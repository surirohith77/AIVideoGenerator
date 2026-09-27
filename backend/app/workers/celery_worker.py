import asyncio
from celery import Celery
from app.config import settings
from app.db.session import SessionLocal

celery_app = Celery(
    "aivideo_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

@celery_app.task(name="app.workers.process_video_job")
def process_video_job(job_id: str):
    from app.services.rendering_service import execute_video_generation_job
    asyncio.run(execute_video_generation_job(SessionLocal, job_id))
