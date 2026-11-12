from celery import Celery
from app.core.config import get_settings

celery = Celery("deepsight", broker=get_settings().redis_url, backend=get_settings().redis_url)
celery.conf.task_default_queue = "default"


@celery.task
def health_task():
    return {"status": "ok"}
