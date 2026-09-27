from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.auth import get_current_user
from app.models.models import User
from app.schemas.schemas import AssetResponse, AssetUpdate
from app.services import asset_service, project_service

router = APIRouter(tags=["Assets"])

@router.post("/projects/{project_id}/assets", response_model=AssetResponse)
async def upload_asset(
    project_id: str,
    file: UploadFile = File(...),
    asset_type: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = project_service.get_project_by_id(db, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    asset = await asset_service.save_uploaded_asset(
        db=db,
        project_id=project_id,
        file_obj=file.file,
        filename=file.filename,
        mime_type=file.content_type,
        custom_type=asset_type
    )
    return asset

@router.get("/projects/{project_id}/assets", response_model=List[AssetResponse])
def get_assets(
    project_id: str,
    type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = project_service.get_project_by_id(db, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return asset_service.get_project_assets(db, project_id, type)

@router.get("/assets/{asset_id}/file")
def download_asset_file(asset_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    asset = asset_service.get_asset_by_id(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(asset.path, media_type=asset.mime_type, filename=asset.filename)

@router.put("/assets/{asset_id}", response_model=AssetResponse)
def update_asset(asset_id: str, data: AssetUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    asset = asset_service.get_asset_by_id(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset_service.update_asset(db, asset_id, data)

@router.delete("/assets/{asset_id}")
async def delete_asset(asset_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    asset = asset_service.get_asset_by_id(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    await asset_service.delete_asset(db, asset_id)
    return {"message": "Asset deleted successfully"}
