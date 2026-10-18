import os
import sys
import uuid
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

# Ensure monorepo root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.models import VideoJob, Video, Script, Project, Scene, StyleProfile, Asset, Presenter, JobStatus
from app.providers.tts.local_tts import LocalTTSProvider
from app.services.presenter_service import get_or_generate_presenter_clip
from app.config import settings
from renderer.ffmpeg_builder import FFmpegRenderer
from app.utils.ffmpeg_utils import extract_media_metadata
from app.utils.audio_timeline import split_continuous_audio_by_scenes

logger = logging.getLogger(__name__)
tts_provider = LocalTTSProvider()
renderer = FFmpegRenderer(storage_path=settings.STORAGE_PATH)

def create_video_job(
    db: Session,
    project_id: str,
    script_id: str,
    generation_mode: str = "CONTENT",
    presenter_id: Optional[str] = None
) -> VideoJob:
    job = VideoJob(
        project_id=project_id,
        script_id=script_id,
        generation_mode=generation_mode,
        presenter_id=presenter_id,
        status=JobStatus.QUEUED.value,
        progress=0,
        current_stage="QUEUED"
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job

def get_job_by_id(db: Session, job_id: str) -> Optional[VideoJob]:
    return db.query(VideoJob).filter(VideoJob.id == job_id).first()

async def execute_video_generation_job(db_session_factory, job_id: str):
    """
    Main background worker processing pipeline for video generation.
    Supports Mode A (PRESENTER Video) & Mode B (CONTENT Video).
    """
    db = db_session_factory()
    job = get_job_by_id(db, job_id)
    if not job:
        db.close()
        return

    try:
        # Stage 1: Preparation
        job.status = JobStatus.ANALYZING.value
        job.progress = 10
        job.current_stage = "PREPARING"
        job.started_at = datetime.utcnow()
        db.commit()

        project = db.query(Project).filter(Project.id == job.project_id).first()
        script = db.query(Script).filter(Script.id == job.script_id).first()
        style = db.query(StyleProfile).filter(StyleProfile.project_id == job.project_id).first()
        scenes = db.query(Scene).filter(Scene.script_id == job.script_id).order_by(Scene.scene_number.asc()).all()

        if not scenes:
            raise ValueError("No scenes found for this script. Run script analysis first.")

        # Stage 2: Audio Generation via Local Voice Cloning (XTTS-v2)
        job.status = JobStatus.GENERATING_AUDIO.value
        job.progress = 25
        job.current_stage = "LOADING_XTTS"
        db.commit()

        scene_dicts = []
        gen_dir = os.path.join(settings.STORAGE_PATH, "generated", job.project_id, job.id)
        os.makedirs(gen_dir, exist_ok=True)

        from app.providers.tts.voice_clone import LocalVoiceCloneProvider
        voice_clone_provider = LocalVoiceCloneProvider()

        scene_contexts = []
        for sc in scenes:
            presenter_target_id = sc.presenter_id or job.presenter_id
            
            # Determine whether this scene uses AI Presenter or Media Asset
            scene_is_presenter = (
                job.generation_mode == "PRESENTER" or 
                sc.scene_mode == "PRESENTER" or 
                bool(sc.presenter_id)
            )

            if scene_is_presenter and not presenter_target_id:
                raise ValueError(
                    f"Scene {sc.scene_number} uses Presenter mode, but no presenter was selected. "
                    "Select a presenter with a recorded voice reference and try again."
                )

            # Fetch voice reference audio path if available
            voice_ref_path = None
            if presenter_target_id:
                pres_obj = db.query(Presenter).filter(Presenter.id == presenter_target_id).first()
                if not pres_obj:
                    raise ValueError(f"Selected presenter '{presenter_target_id}' was not found.")
                if pres_obj.voice_reference and os.path.isfile(pres_obj.voice_reference.path):
                    voice_ref_path = pres_obj.voice_reference.path
                elif scene_is_presenter or presenter_target_id:
                    raise ValueError(
                        f"Presenter '{pres_obj.name}' is missing a usable voice reference. "
                        "Please record or upload a voice reference before generating this video."
                    )

            scene_contexts.append({
                "scene": sc,
                "presenter_target_id": presenter_target_id,
                "scene_is_presenter": scene_is_presenter,
                "voice_ref_path": voice_ref_path,
            })

        narration_texts = [(context["scene"].narration or "").strip() for context in scene_contexts]
        voice_references = {context["voice_ref_path"] for context in scene_contexts}
        # One shared voice reference lets F5 keep its cadence/prosody across
        # visual scene changes. For mixed voices or empty scenes, preserve the
        # existing per-scene synthesis behavior.
        continuous_audio_mode = (
            all(narration_texts)
            and len(voice_references) == 1
        )
        continuous_audio_path = None
        audio_segments = {}
        if continuous_audio_mode:
            voice_ref_path = next(iter(voice_references))
            audio_provider = voice_clone_provider if voice_ref_path else tts_provider
            continuous_audio_path = os.path.join(gen_dir, "narration_continuous.wav")
            job.progress = 35
            job.current_stage = "GENERATING_CONTINUOUS_NARRATION"
            db.commit()
            await audio_provider.generate_audio(
                text=" ".join(narration_texts),
                output_path=continuous_audio_path,
                voice_reference_path=voice_ref_path,
            )
            audio_metadata = await extract_media_metadata(continuous_audio_path)
            narration_duration = float(audio_metadata.get("duration") or 0.0)
            if not audio_metadata.get("has_audio") or narration_duration <= 0:
                raise RuntimeError("Continuous narration generation did not produce valid audio.")

            segments, segment_paths = split_continuous_audio_by_scenes(
                continuous_audio_path,
                scenes,
                narration_duration,
                gen_dir,
            )
            audio_segments = {
                context["scene"].scene_number: (segment, path)
                for context, segment, path in zip(scene_contexts, segments, segment_paths)
            }
            job.progress = 45
            job.current_stage = "CONTINUOUS_VOICE_GENERATED"
            db.commit()

        for context in scene_contexts:
            sc = context["scene"]
            presenter_target_id = context["presenter_target_id"]
            scene_is_presenter = context["scene_is_presenter"]
            voice_ref_path = context["voice_ref_path"]
            sc_audio_path = os.path.join(gen_dir, f"audio_scene_{sc.scene_number:03d}.wav")

            if continuous_audio_mode:
                segment, segmented_path = audio_segments[sc.scene_number]
                sc_audio_path = segmented_path
                scene_duration = segment["duration"]
            else:
                scene_duration = float(sc.duration or 6.0)
                if sc.narration:
                    job.progress = 35
                    job.current_stage = f"GENERATING_VOICE_SCENE_{sc.scene_number}"
                    db.commit()

                    audio_provider = voice_clone_provider if voice_ref_path else tts_provider
                    await audio_provider.generate_audio(
                        text=sc.narration,
                        output_path=sc_audio_path,
                        voice_reference_path=voice_ref_path
                    )

                    job.progress = 45
                    job.current_stage = "VOICE_GENERATED"
                    db.commit()

            asset_path = None
            visual_type = sc.visual_type

            if scene_is_presenter:
                if not presenter_target_id:
                    raise ValueError(f"ERROR: Scene {sc.scene_number} is in PRESENTER mode but no presenter_id was assigned.")

                job.progress = 50
                job.current_stage = "STARTING_MUSE_TALK"
                db.commit()

                job.progress = 70
                job.current_stage = f"LIP_SYNC_SCENE_{sc.scene_number}"
                db.commit()
                
                presenter_clip = await get_or_generate_presenter_clip(
                    db=db,
                    presenter_id=presenter_target_id,
                    audio_path=sc_audio_path,
                    output_dir=gen_dir,
                    settings={"width": 1920, "height": 1080}
                )
                asset_path = presenter_clip
                visual_type = "VIDEO"
            else:
                if sc.asset_id:
                    asset = db.query(Asset).filter(Asset.id == sc.asset_id).first()
                    if asset and os.path.exists(asset.path):
                        asset_path = asset.path

            if not continuous_audio_mode and os.path.exists(sc_audio_path):
                audio_metadata = await extract_media_metadata(sc_audio_path)
                audio_duration = float(audio_metadata.get("duration") or 0.0)
                if audio_metadata.get("has_audio") and audio_duration > 0:
                    if abs(scene_duration - audio_duration) > 0.05:
                        logger.info(
                            "Using narration duration %.3fs instead of configured scene duration %.3fs for scene %s",
                            audio_duration,
                            scene_duration,
                            sc.scene_number,
                        )
                    scene_duration = audio_duration

            scene_dicts.append({
                "scene_number": sc.scene_number,
                "narration": sc.narration,
                "duration": scene_duration,
                "visual_type": visual_type,
                "transition": sc.transition,
                "caption": sc.caption or sc.narration,
                "asset_path": asset_path,
                "audio_path": (
                    sc_audio_path
                    if scene_is_presenter and os.path.exists(sc_audio_path)
                    else (sc_audio_path if not continuous_audio_mode and os.path.exists(sc_audio_path) else None)
                )
            })

        # Stage 3: Resolve Style Assets (Music, Logo)
        style_dict = {
            "aspect_ratio": style.aspect_ratio if style else "16:9",
            "resolution": style.resolution if style else "1080p",
            "music_volume": style.music_volume if style else 0.12,
            "use_logo": style.use_logo if style else True,
            "music_path": None,
            "logo_path": None
        }

        if style and style.music_asset_id:
            m_asset = db.query(Asset).filter(Asset.id == style.music_asset_id).first()
            if m_asset and os.path.exists(m_asset.path):
                style_dict["music_path"] = m_asset.path

        if style and style.logo_asset_id:
            l_asset = db.query(Asset).filter(Asset.id == style.logo_asset_id).first()
            if l_asset and os.path.exists(l_asset.path):
                style_dict["logo_path"] = l_asset.path

        # Stage 4: FFmpeg Render
        job.status = JobStatus.RENDERING.value
        job.progress = 50
        job.current_stage = "RENDERING_FINAL_MP4"
        db.commit()

        output_mp4 = os.path.join(settings.STORAGE_PATH, "projects", job.project_id, f"video_{job.id}.mp4")

        async def update_render_progress(stage: str, progress: int):
            job.current_stage = stage
            job.progress = progress
            db.commit()

        await renderer.render_full_project_video(
            project_name=project.name if project else "Video",
            style_profile=style_dict,
            scenes=scene_dicts,
            output_mp4_path=output_mp4,
            progress_callback=update_render_progress,
            narration_path=continuous_audio_path,
        )

        # Stage 5: Finalize & Create Video record
        total_duration = sum(s["duration"] for s in scene_dicts)
        video_rec = Video(
            project_id=job.project_id,
            script_id=job.script_id,
            job_id=job.id,
            title=script.title if script else "Generated Video",
            file_path=output_mp4,
            duration=total_duration,
            width=1920 if style_dict["aspect_ratio"] != "9:16" else 1080,
            height=1080 if style_dict["aspect_ratio"] != "9:16" else 1920,
            aspect_ratio=style_dict["aspect_ratio"]
        )
        db.add(video_rec)

        job.status = JobStatus.COMPLETED.value
        job.progress = 100
        job.current_stage = "COMPLETED"
        job.output_path = output_mp4
        job.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        logger.error(f"Video job {job_id} failed: {e}", exc_info=True)
        job.status = JobStatus.FAILED.value
        job.error_message = str(e)
        job.current_stage = "FAILED"
        db.commit()
    finally:
        db.close()
