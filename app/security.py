"""JWT 鉴权与密码校验。兼容明文种子口令与 bcrypt 哈希。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGO = "HS256"


def verify_password(plain: str, stored: str) -> bool:
    if stored.startswith("$2"):
        try:
            return _pwd.verify(plain, stored)
        except Exception:
            return False
    return plain == stored  # 种子明文(仅开发)


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def create_token(username: str, role: str) -> str:
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(days=settings.jwt_expire_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGO)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGO])
    except JWTError:
        return None
