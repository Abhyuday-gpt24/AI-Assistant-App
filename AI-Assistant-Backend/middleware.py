from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from src.api.services.auth import decode_token
from src.api.db.database import SessionLocal
from src.api.db.models import User
from sqlmodel import select
import logging
import time
from collections import defaultdict

logger = logging.getLogger(__name__)


# Public routes that don't need auth
PUBLIC_PATHS = [
    "/api/auth/signup",
    "/api/auth/login",
    "/docs",
    "/redoc",
    "/openapi.json",
]


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        # Skip auth for public routes
        if any(request.url.path.startswith(path) for path in PUBLIC_PATHS):
            return await call_next(request)

        # Read token from httpOnly cookie (set by set_auth_cookie at login)
        token = request.cookies.get("access_token")
        if not token:
            return JSONResponse(
                status_code=401,
                content={"error": "Not authenticated"},
            )

        user_id = decode_token(token)
        if not user_id:
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid or expired token"},
            )

        # Fetch user from DB
        async with SessionLocal() as db:
            result = await db.exec(select(User).where(User.id == user_id))
            user = result.first()

        if not user:
            return JSONResponse(
                status_code=401,
                content={"error": "User not found"},
            )

        # Attach user to request — accessible in any route via request.state.user
        request.state.user = user
        return await call_next(request)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = round(time.time() - start, 3)
        user_email = getattr(request.state, "user", None)
        user_info = user_email.email if user_email else "anonymous"
        logger.info(f"{user_info} | {request.method} {request.url.path} → {response.status_code} ({duration}s)")
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Don't let CORS preflights (or any OPTIONS) consume the rate budget.
        if request.method == "OPTIONS":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if now - t < self.window
        ]

        if len(self.requests[client_ip]) >= self.max_requests:
            return JSONResponse(status_code=429, content={"error": "Too many requests"})

        self.requests[client_ip].append(now)
        return await call_next(request)