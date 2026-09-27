from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.auth import get_current_user
from app.models.models import User, Video, Project
from app.schemas.schemas import VideoResponse

router = APIRouter(tags=["Videos"])

@router.get("/projects/{project_id}/videos", response_model=List[VideoResponse])
def get_project_videos(project_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Video).filter(Video.project_id == project_id).order_by(Video.created_at.desc()).all()

@router.get("/videos", response_model=List[VideoResponse])
def get_all_user_videos(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Video).join(Project).filter(Project.user_id == current_user.id).order_by(Video.created_at.desc()).all()

@router.get("/videos/{video_id}", response_model=VideoResponse)
def get_video(video_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video

@router.get("/videos/{video_id}/stream")
def stream_video(video_id: str, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video or not video.file_path:
        raise HTTPException(status_code=404, detail="Video file not found")
    return FileResponse(video.file_path, media_type="video/mp4", filename=f"{video.title}.mp4")

@router.delete("/videos/{video_id}")
def delete_video(video_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    db.delete(video)
    db.commit()
    return {"message": "Video record deleted successfully"}
