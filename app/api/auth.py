"""鉴权:登录发 JWT、当前用户、可复用依赖 get_current_user。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import AppUser
from app.security import create_token, decode_token, verify_password

router = APIRouter(tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/auth/login")
async def login(body: LoginIn, session: AsyncSession = Depends(get_session)) -> dict:
    user = (
        await session.execute(
            select(AppUser).where(AppUser.username == body.username, AppUser.deleted.is_(False))
        )
    ).scalars().first()
    if not user or not verify_password(body.password, user.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return {"token": create_token(user.username, user.role), "username": user.username, "role": user.role}


async def get_current_user(authorization: str = Header(default="")) -> dict:
    """Bearer token 校验,供需要鉴权的路由 Depends 使用。"""
    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="未登录或令牌无效")
    return payload


@router.get("/user/me")
async def me(user: dict = Depends(get_current_user)) -> dict:
    return {"username": user.get("sub"), "role": user.get("role")}
