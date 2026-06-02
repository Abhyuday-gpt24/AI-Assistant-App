from contextlib import asynccontextmanager
from sqlmodel import SQLModel
from src.api.db.database import engine
from src.api.routes.chat import router as chat_router
from src.api.routes.auth import router as auth_router
from fastapi import FastAPI
from sqlalchemy.exc import IntegrityError, OperationalError
from src.api.routes.file_upload import router as files_router
from src.api.routes.ingestion import router as ingestion_router
from src.api.exceptions import (
    AppException,
    app_exception_handler,
    integrity_error_handler,
    db_error_handler,
    global_exception_handler,
)
from middleware import AuthMiddleware, LoggingMiddleware, RateLimitMiddleware
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs on startup — creates DB tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan)


# Add in the order you want them to RUN, but REVERSED.
# Last added = outermost = runs FIRST on the request.
# Effective request flow: CORS -> Logging -> Auth -> RateLimit -> router
app.add_middleware(RateLimitMiddleware, max_requests=60, window_seconds=60)
app.add_middleware(AuthMiddleware)       # checks JWT, attaches user
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # exact origin, not "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register handlers — order matters, most specific first
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(OperationalError, db_error_handler)
app.add_exception_handler(Exception, global_exception_handler)

app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(chat_router, prefix="/api", tags=["Chat"])
app.include_router(files_router, prefix="/api/storage", tags=["Files"])
app.include_router(ingestion_router, prefix="/api/ingestion", tags=["Ingestion"])

