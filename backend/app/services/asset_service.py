import os
import uuid
from typing import List, Optional, BinaryIO
from sqlalchemy.orm import Session
from app.models.models import Asset, AssetType
from app.schemas.schemas import AssetUpdate
from app.providers.storage.local_storage import LocalStorageProvider
from app.utils.ffmpeg_utils import extract_media_metadata

storage_provider = LocalStorageProvider()

def determine_asset_type(filename: str, mime_type: str) -> str:
    fn = filename.lower()
    if any(fn.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]):
        return AssetType.IMAGE.value
    elif any(fn.endswith(ext) for ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]):
        return AssetType.VIDEO.value
    elif any(fn.endswith(ext) for ext in [".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"]):
        if "voice" in fn or "narration" in fn:
            return AssetType.VOICE.value
        elif "music" in fn or "bgm" in fn or "background" in fn:
            return AssetType.MUSIC.value
        return AssetType.AUDIO.value
    elif "logo" in fn:
        return AssetType.LOGO.value
    return AssetType.OTHER.value

async def save_uploaded_asset(
    db: Session,
    project_id: str,
    file_obj: BinaryIO,
    filename: str,
    mime_type: str,
    custom_type: Optional[str] = None
) -> Asset:
    ext = os.path.splitext(filename)[1]
    unique_fn = f"{uuid.uuid4()}{ext}"
    relative_path = os.path.join("uploads", project_id, unique_fn)
    
    full_path = await storage_provider.save_file(file_obj, relative_path)
    file_size = os.path.getsize(full_path)

    # Extract FFprobe metadata
    meta = await extract_media_metadata(full_path)
    asset_type = custom_type or determine_asset_type(filename, mime_type)

    asset = Asset(
        project_id=project_id,
        type=asset_type,
        filename=filename,
        path=full_path,
        mime_type=mime_type,
        size=file_size,
        duration=meta.get("duration"),
        width=meta.get("width"),
        height=meta.get("height"),
        tags=f"{asset_type.lower()}, {filename.lower()}",
        metadata_json=meta
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset

def get_project_assets(db: Session, project_id: str, asset_type: Optional[str] = None) -> List[Asset]:
    query = db.query(Asset).filter(Asset.project_id == project_id)
    if asset_type:
        query = query.filter(Asset.type == asset_type)
    return query.order_by(Asset.created_at.desc()).all()

def get_asset_by_id(db: Session, asset_id: str) -> Optional[Asset]:
    return db.query(Asset).filter(Asset.id == asset_id).first()

def update_asset(db: Session, asset_id: str, data: AssetUpdate) -> Optional[Asset]:
    asset = get_asset_by_id(db, asset_id)
    if not asset:
        return None
    if data.filename is not None:
        asset.filename = data.filename
    if data.tags is not None:
        asset.tags = data.tags
    if data.type is not None:
        asset.type = data.type
    db.commit()
    db.refresh(asset)
    return asset

async def delete_asset(db: Session, asset_id: str) -> bool:
    asset = get_asset_by_id(db, asset_id)
    if not asset:
        return False
    if os.path.exists(asset.path):
        try:
            os.remove(asset.path)
        except Exception:
            pass
    db.delete(asset)
    db.commit()
    return True
