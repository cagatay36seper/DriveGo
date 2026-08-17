from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """
    rt limit message
    """
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "status": "error",
            "message": "Too many requests. Please try again later."
        }
    )
    
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 404:
        return JSONResponse(
            status_code=404,
            content={
                "status": "not_found",
                "message": "The requested resource was not found.",
                "details": exc.detail
            }
        )
    if exc.status_code == 401:
        return JSONResponse(
            status_code=401,
            content={
                "status": "unauthorized",
                "message": "Unauthorized access. Please login again."
            }
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": str(exc.detail) if getattr(exc, "detail", None) else "An error occured please try again later.",
        },
    )
