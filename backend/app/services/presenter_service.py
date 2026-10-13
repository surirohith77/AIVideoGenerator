import asyncio
import os
import uuid
import hashlib
import json
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
    ext = os.path.splitext(safe_filename)[1] or (".mp4" if reference_kind == "FACE" else ".wav")
    upload_id = uuid.uuid4()

    if reference_kind == "VOICE":
        # Voice is submitted from the combined camera/microphone recording.
        # Extract its audio track into a correctly named PCM WAV for XTTS.
        folder = os.path.join(storage_provider.base_dir, "presenters", presenter_id)
        os.makedirs(folder, exist_ok=True)
        source_path = os.path.join(folder, f"voice_source_{upload_id}{ext}")
        wav_filename = f"voice_{upload_id}.wav"
        full_path = os.path.join(folder, wav_filename)
        await storage_provider.save_file(file_obj, os.path.relpath(source_path, storage_provider.base_dir))

        conv_cmd = [
            "ffmpeg", "-y", "-v", "error", "-i", source_path,
            "-map", "0:a:0", "-vn", "-acodec", "pcm_s16le", "-ar", "22050", "-ac", "1",
            full_path,
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *conv_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0 or not os.path.exists(full_path) or os.path.getsize(full_path) <= 1024:
                detail = stderr.decode("utf-8", errors="ignore").strip()
                raise RuntimeError(f"Could not extract voice audio from the presenter recording: {detail}")
        except Exception:
            if os.path.exists(full_path):
                os.remove(full_path)
            raise
        finally:
            if os.path.exists(source_path):
                os.remove(source_path)

        safe_filename = "voice_reference.wav"
        mime_type = "audio/wav"
    else:
        unique_fn = f"face_{upload_id}{ext}"
        relative_path = os.path.join("presenters", presenter_id, unique_fn)
        full_path = await storage_provider.save_file(file_obj, relative_path)
        safe_filename = os.path.basename(safe_filename)
        mime_type = mime_type or "video/mp4"

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

    # A presenter is ready only after both reference modalities are available.
    if presenter.face_reference_asset_id and presenter.voice_reference_asset_id:
        presenter.status = PresenterStatus.READY.value
    else:
        presenter.status = PresenterStatus.PROCESSING.value

    db.commit()
    db.refresh(presenter)
    db.refresh(asset)
    return asset


async def save_presenter_recording_reference(
    db: Session,
    presenter_id: str,
    file_obj: BinaryIO,
    filename: str,
    mime_type: str,
) -> tuple[Asset, Asset]:
    """Store one camera recording and attach its video and extracted audio together."""
    presenter = get_presenter_by_id(db, presenter_id)
    if not presenter:
        raise ValueError("Presenter not found")

    extension = os.path.splitext(os.path.basename(filename or ""))[1].lower()
    if extension not in {".webm", ".mp4", ".mov", ".m4v"}:
        extension = ".mp4" if "mp4" in (mime_type or "") else ".webm"

    recording_id = uuid.uuid4()
    folder = os.path.join(storage_provider.base_dir, "presenters", presenter_id)
    os.makedirs(folder, exist_ok=True)
    video_path = os.path.join(folder, f"recording_{recording_id}{extension}")
    audio_path = os.path.join(folder, f"voice_{recording_id}.wav")
    relative_path = os.path.relpath(video_path, storage_provider.base_dir)
    await storage_provider.save_file(file_obj, relative_path)

    try:
        probe = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
            "-of", "csv=p=0", video_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stream_output, probe_error = await probe.communicate()
        stream_types = set(stream_output.decode("utf-8", errors="ignore").splitlines())
        if probe.returncode != 0 or "video" not in stream_types or "audio" not in stream_types:
            detail = probe_error.decode("utf-8", errors="ignore").strip()
            raise ValueError(
                "The presenter recording must contain both video and audio. "
                + (detail or "Please record again with camera and microphone enabled.")
            )

        extract = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-v", "error", "-i", video_path,
            "-map", "0:a:0", "-vn", "-acodec", "pcm_s16le", "-ar", "22050", "-ac", "1",
            audio_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, extract_error = await extract.communicate()
        if extract.returncode != 0 or not os.path.isfile(audio_path) or os.path.getsize(audio_path) <= 1024:
            detail = extract_error.decode("utf-8", errors="ignore").strip()
            raise ValueError(f"Could not extract the voice reference from the recording: {detail}")

        video_asset = Asset(
            project_id=None,
            type=AssetType.PRESENTER_FACE_REFERENCE.value,
            filename=os.path.basename(video_path),
            path=video_path,
            mime_type=mime_type or "video/webm",
            size=os.path.getsize(video_path),
            tags="presenter, face, recording",
        )
        voice_asset = Asset(
            project_id=None,
            type=AssetType.PRESENTER_VOICE_REFERENCE.value,
            filename="voice_reference.wav",
            path=audio_path,
            mime_type="audio/wav",
            size=os.path.getsize(audio_path),
            tags="presenter, voice, extracted",
        )
        db.add_all([video_asset, voice_asset])
        db.flush()

        presenter.face_reference_asset_id = video_asset.id
        presenter.voice_reference_asset_id = voice_asset.id
        presenter.status = PresenterStatus.READY.value
        db.commit()
    except Exception:
        db.rollback()
        for path in (video_path, audio_path):
            if os.path.exists(path):
                os.remove(path)
        raise

    db.refresh(presenter)
    db.refresh(video_asset)
    db.refresh(voice_asset)
    return video_asset, voice_asset

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
    if not presenter or not presenter.face_reference or not os.path.isfile(presenter.face_reference.path):
        raise ValueError("The selected presenter is missing a usable video reference. Record or upload a camera video first.")

    face_path = presenter.face_reference.path
    audio_hash = compute_file_hash(audio_path)
    effective_settings = settings or {"width": 1280, "height": 720}
    post_processing_enabled = (
        bool(settings["enable_post_processing"])
        if settings and "enable_post_processing" in settings
        else os.getenv("ENABLE_MUSETALK_POST_PROCESSING", "1").lower() in ("1", "true", "yes")
    )
    cache_settings = {
        "generation_version": "musetalk-mouth-detail-v3",
        "settings": effective_settings,
        "parsing_mode": effective_settings.get("parsing_mode", os.getenv("MUSETALK_PARSING_MODE", "inner_mouth")),
        "post_processing_enabled": post_processing_enabled,
    }
    settings_hash = hashlib.sha256(
        json.dumps(cache_settings, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()

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
        "voice_engine": os.getenv("LOCAL_VOICE_ENGINE", "f5_tts"),
        "presenter_engine": os.getenv("LOCAL_PRESENTER_ENGINE", "musetalk"),
        "voice_verification": audio_ver,
        "video_verification": video_ver,
        "status": "COMPLETED"
    }

