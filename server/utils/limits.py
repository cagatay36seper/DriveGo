import time
from fastapi import Request, status
from fastapi.responses import JSONResponse
from .sv import RateLimits

static_requests_db = {}
WINDOW_SIZE = 60  

async def limit_static_files(request: Request, limiter, call_next):
    if request.url.path.startswith(("/static", "/src", "/html")):
        client_ip = request.headers.get("x-forwarded-for") or request.headers.get("x-real-ip") or request.client.host
        if client_ip and "," in client_ip:
            client_ip = client_ip.split(",")[0].strip()
            
        current_time = time.time()
        
        if client_ip not in static_requests_db:
            static_requests_db[client_ip] = []
            
        static_requests_db[client_ip] = [
            t for t in static_requests_db[client_ip] if current_time - t < WINDOW_SIZE
        ]
        
        try:
            if isinstance(RateLimits.STATIC_FILES, str):
                max_allowed = int(RateLimits.STATIC_FILES.split("/")[0])
            else:
                max_allowed = int(RateLimits.STATIC_FILES)
        except Exception:
            max_allowed = 3
            
        if len(static_requests_db[client_ip]) >= max_allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "status": "error",
                    "message": f"Too many requests. Please try again later."
                }
            )
            
        static_requests_db[client_ip].append(current_time)
                
    return await call_next(request)
