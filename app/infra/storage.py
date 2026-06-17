"""S3/MinIO 对象存储(boto3 惰性导入,在线程池跑同步调用)。默认关闭则空操作。"""

from __future__ import annotations

import asyncio

from app.config import settings


def _client():
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
    )


async def upload(key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    if not settings.s3_enabled:
        return ""

    def _do() -> str:
        c = _client()
        try:
            c.head_bucket(Bucket=settings.s3_bucket)
        except Exception:
            try:
                c.create_bucket(Bucket=settings.s3_bucket)
            except Exception:
                pass
        c.put_object(Bucket=settings.s3_bucket, Key=key, Body=data, ContentType=content_type)
        return key

    try:
        return await asyncio.to_thread(_do)
    except Exception:
        return ""


async def presigned(key: str, expires: int = 3600) -> str:
    if not settings.s3_enabled or not key:
        return ""

    def _do() -> str:
        return _client().generate_presigned_url(
            "get_object", Params={"Bucket": settings.s3_bucket, "Key": key}, ExpiresIn=expires
        )

    try:
        return await asyncio.to_thread(_do)
    except Exception:
        return ""
