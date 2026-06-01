from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.db.database import get_db
from src.api.schemas.schemas import SignupRequest, LoginRequest
from src.api.services.auth import create_user, authenticate_user, create_token
from src.api.services.auth import COOKIE_CONFIG

router = APIRouter()


def set_auth_cookie(response: Response, token: str):
    response.set_cookie(key="access_token", value=token, **COOKIE_CONFIG)


@router.post("/signup")
async def signup(req: SignupRequest, response: Response, db: AsyncSession = Depends(get_db)):
    user = await create_user(db, req.email, req.password, req.name)
    set_auth_cookie(response, create_token(user.id))
    return {"message": "signed up", "user": {"id": user.id, "name": user.name}}


@router.post("/login")
async def login(req: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    set_auth_cookie(response, create_token(user.id))
    return {"message": "logged in", "user": {"id": user.id, "name": user.name}}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token", **COOKIE_CONFIG)
    return {"message": "logged out"}