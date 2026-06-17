"""用户管理:列表/创建/删除 + 改密。需登录(get_current_user)。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db import get_session
from app.models import AppUser
from app.security import hash_password, verify_password
from app.utils import gen_id

router = APIRouter(tags=["user"])


class UserIn(BaseModel):
    username: str
    password: str
    role: str = "user"


class PasswordIn(BaseModel):
    old_password: str
    new_password: str


@router.get("/users")
async def list_users(
    _: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> list[dict]:
    rows = (
        await session.execute(select(AppUser).where(AppUser.deleted.is_(False)))
    ).scalars().all()
    return [{"id": u.id, "username": u.username, "role": u.role} for u in rows]


@router.post("/users")
async def create_user(
    body: UserIn, _: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> dict:
    exists = (
        await session.execute(select(AppUser).where(AppUser.username == body.username))
    ).scalars().first()
    if exists:
        raise HTTPException(status_code=409, detail="用户名已存在")
    u = AppUser(id=gen_id(), username=body.username, password=hash_password(body.password), role=body.role)
    session.add(u)
    await session.commit()
    return {"id": u.id, "username": u.username, "role": u.role}


@router.delete("/users/{uid}")
async def delete_user(
    uid: str, _: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> dict:
    u = (await session.execute(select(AppUser).where(AppUser.id == uid))).scalar_one_or_none()
    if u is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    u.deleted = True
    await session.commit()
    return {"deleted": True}


@router.put("/user/password")
async def change_password(
    body: PasswordIn,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    u = (
        await session.execute(select(AppUser).where(AppUser.username == user.get("sub")))
    ).scalars().first()
    if u is None or not verify_password(body.old_password, u.password):
        raise HTTPException(status_code=400, detail="原密码错误")
    u.password = hash_password(body.new_password)
    await session.commit()
    return {"updated": True}
