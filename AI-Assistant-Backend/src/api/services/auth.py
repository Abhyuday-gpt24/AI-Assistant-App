from jose import jwt
from datetime import datetime, timedelta
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from src.api.db.models import User
from fastapi import Request, HTTPException
import bcrypt
import hashlib
import base64
from config import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
EXPIRE_HOURS = int(settings.EXPIRE_HOURS)



COOKIE_CONFIG = {
    "httponly": True,
    "secure": settings.COOKIE_SECURE,   # False over plain HTTP, else browser drops it
    "samesite": "lax",
    "max_age": EXPIRE_HOURS * 3600,
    "path": "/"
}

def hash_password(password: str) -> str:
    sha256 = hashlib.sha256(password.encode("utf-8")).digest()
    b64 = base64.b64encode(sha256)
    return bcrypt.hashpw(b64, bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    sha256 = hashlib.sha256(plain_password.encode("utf-8")).digest()
    b64 = base64.b64encode(sha256)
    return bcrypt.checkpw(b64, hashed_password.encode("utf-8"))

def create_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=EXPIRE_HOURS)
    return jwt.encode({"sub": user_id, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> str | None:
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(request: Request, db: AsyncSession) -> User:
    token = request.cookies.get("access_token")
    user_id = decode_token(token)

    result = await db.exec(select(User).where(User.id == user_id))
    user = result.first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


async def create_user(db: AsyncSession, email: str, password: str, name: str) -> User:
    user = User(email=email, hashed_password=hash_password(password), name=name)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    result = await db.exec(select(User).where(User.email == email))
    user = result.first()
    if user and verify_password(password, user.hashed_password):
        return user
    return None