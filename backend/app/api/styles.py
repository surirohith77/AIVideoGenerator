from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.auth import get_current_user
from app.models.models import User, StyleProfile
from app.schemas.schemas import StyleProfileUpdate, StyleProfileResponse
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["Styles"])

@router.get("/{project_id}/style", response_model=StyleProfileResponse)
def get_style(project_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = project_service.get_project_by_id(db, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.style_profile:
        raise HTTPException(status_code=404, detail="Style profile not found")
    return project.style_profile

@router.put("/{project_id}/style", response_model=StyleProfileResponse)
def update_style(project_id: str, data: StyleProfileUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = project_service.get_project_by_id(db, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    style = project_service.update_style_profile(db, project_id, data)
    return style
