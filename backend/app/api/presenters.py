from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.auth import get_current_user
from app.models.models import User
from app.schemas.schemas import PresenterCreate, PresenterUpdate, PresenterResponse, AssetResponse
from app.services import presenter_service

router = APIRouter(prefix="/presenters", tags=["Presenters"])

@router.post("", response_model=PresenterResponse)
def create_presenter(
    data: PresenterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        return presenter_service.create_presenter(db, user_id=current_user.id, data=data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=List[PresenterResponse])
def get_presenters(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return presenter_service.get_user_presenters(db, user_id=current_user.id)

@router.get("/{presenter_id}", response_model=PresenterResponse)
def get_presenter(
    presenter_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    presenter = presenter_service.get_presenter_by_id(db, presenter_id)
    if not presenter or presenter.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Presenter not found")
    return presenter

@router.post("/{presenter_id}/record-reference", response_model=PresenterResponse)
async def record_reference_asset(
    presenter_id: str,
    kind: str = Form(..., description="FACE or VOICE"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    presenter = presenter_service.get_presenter_by_id(db, presenter_id)
    if not presenter or presenter.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Presenter not found")

    await presenter_service.save_presenter_reference_asset(
        db=db,
        presenter_id=presenter_id,
        file_obj=file.file,
        filename=file.filename,
        mime_type=file.content_type,
        reference_kind=kind.upper()
    )
    db.refresh(presenter)
    return presenter


@router.post("/{presenter_id}/recording-reference", response_model=PresenterResponse)
async def record_combined_reference(
    presenter_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    presenter = presenter_service.get_presenter_by_id(db, presenter_id)
    if not presenter or presenter.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Presenter not found")

    try:
        await presenter_service.save_presenter_recording_reference(
            db=db,
            presenter_id=presenter_id,
            file_obj=file.file,
            filename=file.filename or "presenter_recording.webm",
            mime_type=file.content_type or "video/webm",
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    db.refresh(presenter)
    return presenter

@router.post("/{presenter_id}/test-generation")
async def test_presenter_generation(
    presenter_id: str,
    text: str = Form("Hello, this is a test of my AI presenter and voice model."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    presenter = presenter_service.get_presenter_by_id(db, presenter_id)
    if not presenter or presenter.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Presenter not found")
    
    try:
        res = await presenter_service.test_presenter_generation(db, presenter_id=presenter_id, text=text)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{presenter_id}")
def delete_presenter(
    presenter_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    presenter = presenter_service.get_presenter_by_id(db, presenter_id)
    if not presenter or presenter.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Presenter not found")
    presenter_service.delete_presenter(db, presenter_id)
    return {"message": "Presenter deleted successfully"}

