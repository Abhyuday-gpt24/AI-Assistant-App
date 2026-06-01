from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError
import logging

logger = logging.getLogger(__name__)


# Custom exceptions
class AppException(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


class DuplicateError(AppException):
    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(status_code=409, detail=detail)


class NotFoundError(AppException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=404, detail=detail)


class AuthError(AppException):
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(status_code=401, detail=detail)


# Handlers
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.warning(f"DB integrity error: {exc}")
    return JSONResponse(
        status_code=409,
        content={"error": "Duplicate or constraint violation"},
    )


async def db_error_handler(request: Request, exc: OperationalError):
    logger.error(f"DB connection error: {exc}")
    return JSONResponse(
        status_code=503,
        content={"error": "Database unavailable, try again later"},
    )


async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},  # never expose details in prod
    )