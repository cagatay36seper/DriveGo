import os
import hmac
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.exceptions import HTTPException as StarletteHTTPException

from server.db.database import Base, SessionLocal, engine, seed_initial_data
from server.routes.auth import router as auth_router
from server.routes.cars import router as cars_router
from server.routes.dashboard import router as dashboard_router
from server.routes.reservations import router as reservations_router
from server.routes.reviews import router as reviews_router
from server.routes.modals import UserDB
from server.utils.auth import extract_access_token, verify_access_token
from server.utils.errors import custom_http_exception_handler, custom_rate_limit_handler
from server.utils.limits import limit_static_files
from server.utils.sv import RateLimits


PRODUCTION = os.getenv("PRODUCTION", "false").lower() in {"1", "true", "yes"}
HTML_DIR = Path("client/html")
STATIC_DIR = Path("client/html")
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")
    if origin.strip()
]
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "1" if PRODUCTION else "0") == "1"


limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    docs_url=None if PRODUCTION else "/docs",
    redoc_url=None if PRODUCTION else "/redoc",
    openapi_url=None if PRODUCTION else "/openapi.json",
    title="DriveGo API",
    description="Rent a Car API",
    version="1.0.0",
)

app.state.limiter = limiter

Base.metadata.create_all(bind=engine)
seed_initial_data()


app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)
app.add_exception_handler(HTTPException, custom_http_exception_handler)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return await custom_http_exception_handler(request, exc)


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-ACINT", "X-CSRF-Token"],
)


@app.middleware("http")
async def lsf(request: Request, call_next):
    unsafe_request = request.method in {"POST", "PUT", "PATCH", "DELETE"}
    stateful_path = request.url.path.startswith(("/api/", "/admin/"))
    csrf_exempt_path = request.url.path in {"/api/auth/login", "/api/auth/register"}

    if unsafe_request and stateful_path and not csrf_exempt_path:
        origin = request.headers.get("origin")
        if origin and origin not in ALLOWED_ORIGINS:
            return JSONResponse({"detail": "Request origin is not allowed."}, status_code=403)

        if request.cookies.get("access_token"):
            csrf_cookie = request.cookies.get("csrf_token")
            csrf_header = request.headers.get("X-CSRF-Token")
            if not csrf_cookie or not csrf_header or not hmac.compare_digest(csrf_cookie, csrf_header):
                return JSONResponse({"detail": "CSRF doğrulaması başarısız."}, status_code=403)

    response = await limit_static_files(request, limiter, call_next)
    if not request.cookies.get("csrf_token"):
        response.set_cookie(
            key="csrf_token",
            value=secrets.token_urlsafe(32),
            httponly=False,
            secure=COOKIE_SECURE,
            samesite="lax",
            max_age=60 * 60 * 24 * 7,
            path="/",
        )
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; script-src 'self'; font-src 'self' https://cdnjs.cloudflare.com; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
    )
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.mount("/src", StaticFiles(directory="client/src"), name="src")

if not PRODUCTION:
    app.mount("/html", StaticFiles(directory=str(HTML_DIR)), name="html")


@lru_cache(maxsize=100)
def get_cached_html(filename: str) -> Optional[str]:
    file_path = HTML_DIR / filename
    if not file_path.exists():
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def render_html(filename: str, use_cache: bool = PRODUCTION) -> HTMLResponse:
    if not use_cache:
        try:
            with open(HTML_DIR / filename, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        except FileNotFoundError:
            return HTMLResponse("<h1>404 - Sayfa Bulunamadı</h1>", status_code=404)

    content = get_cached_html(filename)
    if content is None:
        return HTMLResponse("<h1>404 - Sayfa Bulunamadı</h1>", status_code=404)
    return HTMLResponse(content=content)


async def get_current_user(request: Request) -> Optional[dict]:
    token = extract_access_token(request)
    payload = verify_access_token(token) if token else None
    if not payload:
        return None

    db = SessionLocal()
    try:
        try:
            user_id = int(payload.get("sub"))
        except (TypeError, ValueError):
            return None
        user = db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user or not user.is_active or user.is_blocked:
            return None
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
        }
    finally:
        db.close()


async def require_auth(request: Request) -> dict:
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


app.include_router(auth_router, prefix="/api")
app.include_router(cars_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(reservations_router, prefix="/api")
app.include_router(reviews_router, prefix="/api")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": "production" if PRODUCTION else "development",
        "version": "1.0.0",
    }


@app.get("/", response_class=HTMLResponse)
@limiter.limit(RateLimits.ROOT)
async def root(request: Request):
    return render_html("index.html")


@app.get("/login", response_class=HTMLResponse)
@limiter.limit(RateLimits.ROOT)
async def login_page(request: Request):
    user = await get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return render_html("login.html")


@app.get("/register", response_class=HTMLResponse)
@limiter.limit(RateLimits.ROOT)
async def register_page(request: Request):
    user = await get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return render_html("register.html")


@app.get("/dashboard", response_class=HTMLResponse)
@limiter.limit(RateLimits.ROOT)
async def dashboard_page(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return render_html("dashboard.html")


@app.get("/{path:path}")
async def catch_all(path: str):
    html_root = HTML_DIR.resolve()
    html_file = (html_root / f"{path}.html").resolve()
    if html_root in html_file.parents and html_file.exists():
        return render_html(f"{path}.html")

    static_root = STATIC_DIR.resolve()
    static_file = (static_root / path).resolve()
    if static_root in static_file.parents and static_file.exists():
        return FileResponse(static_file)

    return HTMLResponse("<h1>404 - Sayfa Bulunamadı</h1>", status_code=404)


@app.post("/admin/cache/clear")
async def clear_cache(request: Request):
    user = await get_current_user(request)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin yetkisi gerekli.")
    get_cached_html.cache_clear()
    return {"message": "Cache cleared successfully"}


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return HTMLResponse("<h1>404 - Sayfa Bulunamadı</h1>", status_code=404)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    uvicorn.run(
        app,
        host=host,
        port=port,
    )
