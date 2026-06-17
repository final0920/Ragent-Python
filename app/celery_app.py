"""Celery 应用(MQ 异步)。仅在 celery_enabled 时被 app.tasks 触发导入。

启动 worker(Windows 用 solo 池):
  uv sync --group infra
  uv run celery -A app.celery_app worker -P solo -l info
"""

from __future__ import annotations

from celery import Celery

from app.config import settings

celery = Celery("ragent", broker=settings.celery_broker, backend=settings.celery_broker)
celery.conf.update(task_serializer="json", accept_content=["json"], result_expires=3600)

import app.tasks  # noqa: E402,F401  注册任务
