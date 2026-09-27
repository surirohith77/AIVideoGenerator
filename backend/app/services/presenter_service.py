import os
import uuid
import hashlib
import shutil
from datetime import datetime
from typing import List, Optional, BinaryIO
from sqlalchemy.orm import Session
from app.models.models import Presenter, PresenterStatus, PresenterGenerationCache, Asset, AssetType
from app.schemas.schemas import PresenterCreate, PresenterUpdate
from app.providers.presenter.local_presenter import LocalPresenterProvider
from app.providers.storage.local_storage import LocalStorageProvider

storage_provider = LocalStorageProvider()
presenter_provider = LocalPresenterProvider()

def compute_file_hash(file_path: str) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def create_presenter(db: Session, user_id: str, data: PresenterCreate) -> Presenter:
    if not data.consent_confirmed:
        raise ValueError("Consent must be explicitly confirmed before creating a Presenter.")

    presenter = Presenter(
        user_id=user_id,
        name=data.name,
        description=data.description,
        status=PresenterStatus.CREATED.value,
        consent_confirmed=True,
        consent_timestamp=datetime.utcnow(),
        consent_method=data.consent_method
    )
    db.add(presenter)
    db.commit()
    db.refresh(presenter)
    return presenter

def get_user_presenters(db: Session, user_id: str) -> List[Presenter]:
    return db.query(Presenter).filter(Presenter.user_id == user_id).order_by(Presenter.created_at.desc()).all()

def get_presenter_by_id(db: Session, presenter_id: str) -> Optional[Presenter]:
    return db.query(Presenter).filter(Presenter.id == presenter_id).first()

def update_presenter(db: Session, presenter_id: str, data: PresenterUpdate) -> Optional[Presenter]:
    presenter = get_presenter_by_id(db, presenter_id)
    if not presenter:
        return None
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(presenter, field, val)
    db.commit()
    db.refresh(presenter)
    return presenter

async def save_presenter_reference_asset(
    db: Session,
    presenter_id: str,
    file_obj: BinaryIO,
    filename: str,
    mime_type: str,
    reference_kind: str # "FACE" or "VOICE"
) -> Asset:
    presenter = get_presenter_by_id(db, presenter_id)
    if not presenter:
        raise ValueError("Presenter not found")

    safe_filename = filename or f"{reference_kind.lower()}_reference.mp4"
    ext = os.path.splitext(safe_filename)[1] if (safe_filename and os.path.splitext(safe_filename)[1]) else (".mp4" if reference_kind == "FACE" else ".wav")
    unique_fn = f"{reference_kind.lower()}_{uuid.uuid4()}{ext}"
    relative_path = os.path.join("presenters", presenter_id, unique_fn)
    full_path = await storage_provider.save_file(file_obj, relative_path)

    # Convert voice reference audio to clean 22050Hz 16-bit PCM mono WAV for XTTS compatibility
    if reference_kind == "VOICE":
        clean_wav_path = os.path.join(os.path.dirname(full_path), f"clean_{unique_fn}.wav")
        conv_cmd = [
            "ffmpeg", "-y", "-i", full_path,
            "-vn", "-acodec", "pcm_s16le", "-ar", "22050", "-ac", "1",
            clean_wav_path
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *conv_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            if os.path.exists(clean_wav_path) and os.path.getsize(clean_wav_path) > 1024:
                shutil.move(clean_wav_path, full_path)
        except Exception as e:
            pass

    file_size = os.path.getsize(full_path)

    asset_type = (
        AssetType.PRESENTER_FACE_REFERENCE.value
        if reference_kind == "FACE"
        else AssetType.PRESENTER_VOICE_REFERENCE.value
    )

    asset = Asset(
        project_id=None,
        type=asset_type,
        filename=safe_filename,
        path=full_path,
        mime_type=mime_type or ("video/mp4" if reference_kind == "FACE" else "audio/wav"),
        size=file_size,
        tags=f"presenter, {reference_kind.lower()}"
    )

    db.add(asset)
    db.flush()

    if reference_kind == "FACE":
        presenter.face_reference_asset_id = asset.id
    else:
        presenter.voice_reference_asset_id = asset.id

    # Mark Presenter READY if face reference exists
    if presenter.face_reference_asset_id:
        presenter.status = PresenterStatus.READY.value

    db.commit()
    db.refresh(presenter)
    db.refresh(asset)
    return asset

def delete_presenter(db: Session, presenter_id: str) -> bool:
    presenter = get_presenter_by_id(db, presenter_id)
    if not presenter:
        return False

    # Delete presenter folder on disk
    presenter_folder = os.path.join(storage_provider.base_dir, "presenters", presenter_id)
    if os.path.exists(presenter_folder):
        try:
            shutil.rmtree(presenter_folder)
        except Exception:
            pass

    # Delete cached clips
    db.query(PresenterGenerationCache).filter(PresenterGenerationCache.presenter_id == presenter_id).delete()
    db.delete(presenter)
    db.commit()
    return True

async def get_or_generate_presenter_clip(
    db: Session,
    presenter_id: str,
    audio_path: str,
    output_dir: str,
    settings: Optional[dict] = None
) -> str:
    presenter = get_presenter_by_id(db, presenter_id)
    if not presenter or not presenter.face_reference:
        raise ValueError("Valid presenter with face reference required.")

    face_path = presenter.face_reference.path
    audio_hash = compute_file_hash(audio_path)
    settings_str = f"{settings.get('width', 1280)}x{settings.get('height', 720)}" if settings else "1280x720"
    settings_hash = hashlib.sha256(settings_str.encode("utf-8")).hexdigest()

    # Check cache
    cached = db.query(PresenterGenerationCache).filter(
        PresenterGenerationCache.presenter_id == presenter_id,
        PresenterGenerationCache.audio_hash == audio_hash,
        PresenterGenerationCache.settings_hash == settings_hash
    ).first()

    if cached and os.path.exists(cached.output_path):
        return cached.output_path

    out_file = os.path.join(output_dir, f"presenter_{uuid.uuid4()}.mp4")
    generated_path = await presenter_provider.generate_presenter_clip(
        presenter_id=presenter_id,
        face_reference_path=face_path,
        audio_path=audio_path,
        output_clip_path=out_file,
        settings=settings
    )

    # Save to cache
    cache_item = PresenterGenerationCache(
        presenter_id=presenter_id,
        audio_hash=audio_hash,
        settings_hash=settings_hash,
        output_path=generated_path
    )
    db.add(cache_item)
    db.commit()
    return generated_path

async def test_presenter_generation(db: Session, presenter_id: str, text: str) -> dict:
    from app.providers.tts.voice_clone import LocalVoiceCloneProvider
    from app.utils.media_verification import verify_output_media_file

    presenter = get_presenter_by_id(db, presenter_id)
    if not presenter:
        raise ValueError("Presenter not found")

    output_dir = os.path.join(storage_provider.base_dir, "test_generations", presenter_id)
    os.makedirs(output_dir, exist_ok=True)

    if not presenter.voice_reference or not os.path.exists(presenter.voice_reference.path):
        raise ValueError(f"ERROR: Presenter '{presenter.name}' requires a voice reference. Please record or upload a voice reference audio file.")

    if not presenter.face_reference or not os.path.exists(presenter.face_reference.path):
        raise ValueError(f"ERROR: Presenter '{presenter.name}' requires a face reference. Please record or upload a face reference video file.")

    voice_ref_path = presenter.voice_reference.path
    face_ref_path = presenter.face_reference.path

    # 1. Synthesize speech via voice cloning / tts provider
    audio_out = os.path.join(output_dir, f"test_voice_{uuid.uuid4()}.wav")
    tts_provider = LocalVoiceCloneProvider()
    generated_audio_path = await tts_provider.generate_audio(
        text=text,
        output_path=audio_out,
        voice_reference_path=voice_ref_path
    )

    # Verify generated audio output via ffprobe
    audio_ver = await verify_output_media_file(generated_audio_path, require_audio=True)

    # 2. Render talking presenter video clip
    clip_out = os.path.join(output_dir, f"test_presenter_{uuid.uuid4()}.mp4")
    generated_video_path = await presenter_provider.generate_presenter_clip(
        presenter_id=presenter_id,
        face_reference_path=face_ref_path,
        audio_path=generated_audio_path,
        output_clip_path=clip_out
    )

    # Verify generated presenter video output via ffprobe
    video_ver = await verify_output_media_file(generated_video_path, require_video=True, require_audio=True)

    return {
        "presenter_id": presenter_id,
        "presenter_name": presenter.name,
        "text": text,
        "voice_reference_path": voice_ref_path,
        "face_reference_path": face_ref_path,
        "generated_audio_path": generated_audio_path,
        "generated_video_path": generated_video_path,
        "voice_engine": os.getenv("LOCAL_VOICE_ENGINE", "xtts_v2"),
        "presenter_engine": os.getenv("LOCAL_PRESENTER_ENGINE", "musetalk"),
        "voice_verification": audio_ver,
        "video_verification": video_ver,
        "status": "COMPLETED"
    }

