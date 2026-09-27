from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.auth import get_current_user
from app.models.models import User
from app.schemas.schemas import ScriptCreate, ScriptUpdate, ScriptResponse, SceneResponse, SceneUpdate
from app.services import script_service, project_service

router = APIRouter(tags=["Scripts & Scenes"])

@router.post("/projects/{project_id}/scripts", response_model=ScriptResponse)
def create_script(project_id: str, data: ScriptCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = project_service.get_project_by_id(db, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return script_service.create_script(db, project_id, data)

@router.get("/projects/{project_id}/scripts", response_model=List[ScriptResponse])
def get_scripts(project_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = project_service.get_project_by_id(db, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return script_service.get_project_scripts(db, project_id)

@router.get("/scripts/{script_id}", response_model=ScriptResponse)
def get_script(script_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    script = script_service.get_script_by_id(db, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script

@router.put("/scripts/{script_id}", response_model=ScriptResponse)
def update_script(script_id: str, data: ScriptUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    script = script_service.get_script_by_id(db, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script_service.update_script(db, script_id, data)

@router.delete("/scripts/{script_id}")
def delete_script(script_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    script = script_service.get_script_by_id(db, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    script_service.delete_script(db, script_id)
    return {"message": "Script deleted successfully"}

@router.post("/scripts/{script_id}/analyze", response_model=List[SceneResponse])
async def analyze_script(
    script_id: str,
    mode: str = "CONTENT",
    presenter_id: Optional[str] = None,
    presenter_frequency: str = "automatic",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    script = script_service.get_script_by_id(db, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    scenes = await script_service.analyze_script_and_create_scenes(
        db=db,
        script_id=script_id,
        mode=mode,
        presenter_id=presenter_id,
        presenter_frequency=presenter_frequency
    )
    return scenes

@router.get("/scripts/{script_id}/scenes", response_model=List[SceneResponse])
def get_scenes(script_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    script = script_service.get_script_by_id(db, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script.scenes

@router.put("/scenes/{scene_id}", response_model=SceneResponse)
def update_scene(scene_id: str, data: SceneUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    scene = script_service.update_scene(db, scene_id, data)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene
