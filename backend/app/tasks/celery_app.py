from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "sentrascan",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.scan_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Eager modda .delay() cagrisi broker'a hic gitmez, gorev ayni surecte
    # calisir; boylece Redis olmadan da tarama akisi denenebilir.
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=False,
)
