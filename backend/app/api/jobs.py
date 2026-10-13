import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.session import get_db, SessionLocal
from app.api.auth import get_current_user
from app.models.models import User, JobStatus
from app.schemas.schemas import VideoJobResponse, VideoJobCreate
from app.services import rendering_service, script_service
from app.services import presenter_service

router = APIRouter(tags=["Video Jobs"])

@router.post("/scripts/{script_id}/generate-video", response_model=VideoJobResponse)
def trigger_video_generation(
    script_id: str,
    job_in: Optional[VideoJobCreate] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    script = script_service.get_script_by_id(db, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    gen_mode = job_in.generation_mode if job_in else "CONTENT"
    pres_id = job_in.presenter_id if job_in else None

    if gen_mode.upper() == "PRESENTER":
        if not pres_id:
            raise HTTPException(
                status_code=400,
                detail="Select a presenter with a recorded voice reference before starting Presenter mode.",
            )
        presenter = presenter_service.get_presenter_by_id(db, pres_id)
        if not presenter or presenter.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Presenter not found")
        if not presenter.face_reference or not os.path.isfile(presenter.face_reference.path):
            raise HTTPException(
                status_code=400,
                detail=f"Presenter '{presenter.name}' is missing a usable video reference. Record a camera video before generating.",
            )
        if not presenter.voice_reference or not os.path.isfile(presenter.voice_reference.path):
            raise HTTPException(
                status_code=400,
                detail=f"Presenter '{presenter.name}' is missing a usable voice reference. Record or upload one before generating video.",
            )

    job = rendering_service.create_video_job(
        db=db,
        project_id=script.project_id,
        script_id=script_id,
        generation_mode=gen_mode,
        presenter_id=pres_id
    )
    
    # Try Celery background worker if available, fallback to FastAPI background task
    try:
        from app.workers.celery_worker import process_video_job
        process_video_job.delay(job.id)
    except Exception:
        # Fallback to local background tasks executor
        background_tasks.add_task(rendering_service.execute_video_generation_job, SessionLocal, job.id)

    return job

@router.get("/jobs/{job_id}", response_model=VideoJobResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = rendering_service.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = rendering_service.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = JobStatus.CANCELLED.value
    job.current_stage = "CANCELLED"
    db.commit()
    return {"message": "Job cancelled successfully"}
