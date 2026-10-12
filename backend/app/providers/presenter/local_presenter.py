import os
import asyncio
import logging
import shutil
import hashlib
from typing import Dict, Any, Optional
from app.providers.presenter.base import PresenterProvider
from app.utils.media_verification import verify_output_media_file

logger = logging.getLogger(__name__)

def compute_file_hash(file_path: str) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

class LocalPresenterProvider(PresenterProvider):
    """
    Local AI Presenter Engine Adapter (MuseTalk Apple Silicon Runtime).
    Executes actual neural model lip-sync inference via /Users/rohith/Documents/yt/musetalk-mac/.venv/bin/python.
    Strictly forbids falling back to simple FFmpeg looping of reference videos.
    """
    def __init__(self):
        self.engine_name = os.getenv("LOCAL_PRESENTER_ENGINE", "musetalk").lower()
        self.musetalk_dir = os.getenv("MUSETALK_MAC_DIR", "/Users/rohith/Documents/yt/musetalk-mac")
        self.musetalk_python = os.getenv(
            "MUSETALK_PYTHON_PATH",
            os.path.join(self.musetalk_dir, ".venv", "bin", "python")
        )
        self.model_path = os.getenv("PRESENTER_MODEL_PATH", self.musetalk_dir)

    def get_engine_status(self) -> Dict[str, Any]:
        """
        Inspects whether the local presenter model engine weights/scripts are installed.
        """
        if os.path.exists(self.musetalk_python):
            return {
                "engine": self.engine_name,
                "status": "READY",
                "model_path": self.musetalk_dir,
                "python_path": self.musetalk_python,
                "message": f"Local Apple Silicon MuseTalk engine ready at '{self.musetalk_dir}'."
            }

        if self.model_path and os.path.exists(self.model_path):
            return {
                "engine": self.engine_name,
                "status": "READY",
                "model_path": self.model_path,
                "message": f"Local presenter model ({self.engine_name}) weights found at '{self.model_path}'."
            }
        
        if shutil.which(self.engine_name):
            return {
                "engine": self.engine_name,
                "status": "READY",
                "model_path": shutil.which(self.engine_name),
                "message": f"Local presenter engine executable ({self.engine_name}) found."
            }

        return {
            "engine": self.engine_name,
            "status": "NOT_INSTALLED",
            "model_path": self.musetalk_dir,
            "message": f"Local presenter engine '{self.engine_name}' not found at '{self.musetalk_dir}'. Please verify musetalk-mac environment."
        }

    async def create_presenter_profile(
        self,
        face_reference_path: str,
        voice_reference_path: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        status_info = self.get_engine_status()
        return {
            "engine": self.engine_name,
            "face_path": face_reference_path,
            "voice_path": voice_reference_path,
            "status": status_info["status"],
            "message": status_info["message"]
        }

    async def generate_presenter_clip(
        self,
        presenter_id: str,
        face_reference_path: str,
        audio_path: str,
        output_clip_path: str,
        settings: Optional[Dict[str, Any]] = None
    ) -> str:
        os.makedirs(os.path.dirname(output_clip_path), exist_ok=True)

        if not face_reference_path or not os.path.exists(face_reference_path):
            raise ValueError(f"ERROR: Face reference video missing or file not found at '{face_reference_path}'.")

        if not audio_path or not os.path.exists(audio_path):
            raise ValueError(f"ERROR: Generated narration audio missing or file not found at '{audio_path}'.")

        logger.info(
            f"\n========== AI PRESENTER GENERATION ==========\n"
            f"Presenter ID: {presenter_id}\n"
            f"Presenter engine: {self.engine_name}\n"
            f"MuseTalk directory: {self.musetalk_dir}\n"
            f"MuseTalk python: {self.musetalk_python}\n"
            f"Face reference: {face_reference_path}\n"
            f"Input generated speech audio: {audio_path}\n"
            f"Output clip destination: {output_clip_path}\n"
            f"=============================================="
        )

        print("[MuseTalk] Starting")
        print(f"[MuseTalk] Input video: {face_reference_path}")
        print(f"[MuseTalk] Input audio: {audio_path}")
        print("[MuseTalk] Device: MPS")

        # 1. Primary Execution: Dedicated Apple-Silicon MuseTalk Runtime (.venv)
        inference_script = os.path.join(self.musetalk_dir, "inference.py")
        if os.path.exists(self.musetalk_python) and os.path.exists(inference_script):
            enable_post_proc = os.getenv("ENABLE_MUSETALK_POST_PROCESSING", "1").lower() in ("1", "true", "yes")
            if settings and "enable_post_processing" in settings:
                enable_post_proc = bool(settings["enable_post_processing"])

            parsing_mode = os.getenv("MUSETALK_PARSING_MODE", "inner_mouth")
            if settings and "parsing_mode" in settings:
                parsing_mode = str(settings["parsing_mode"])

            cmd = [
                self.musetalk_python,
                inference_script,
                "--video_path", face_reference_path,
                "--audio_path", audio_path,
                "--output_path", output_clip_path,
                "--device", "mps",
                "--batch_size", "1",
                "--parsing_mode", parsing_mode
            ]
            if enable_post_proc:
                cmd.append("--enable_post_processing")

            logger.info(f"Executing Apple-Silicon MuseTalk inference: {' '.join(cmd)}")
            print("[MuseTalk] Inference started")
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            stdout_str = stdout.decode("utf-8", errors="ignore")
            stderr_str = stderr.decode("utf-8", errors="ignore")

            if proc.returncode == 0 and os.path.exists(output_clip_path) and os.path.getsize(output_clip_path) > 1024:
                print("[MuseTalk] Inference completed")
                print(f"[MuseTalk] Output: {output_clip_path}")
                
                verification = await verify_output_media_file(output_clip_path, require_video=True, require_audio=True)
                print(f"[MuseTalk] ffprobe validation: size={verification['size']}B, duration={verification['duration']}s")
                
                # Enforce hash check: output MP4 must be a newly generated file, not reference copy
                if compute_file_hash(output_clip_path) == compute_file_hash(face_reference_path):
                    raise RuntimeError("Neural model error: Generated presenter output is identical to reference MP4.")
                
                print("[MuseTalk] SUCCESS")
                return output_clip_path
            else:
                err_msg = stderr_str or stdout_str or f"Process exited with code {proc.returncode}"
                logger.error(f"[MuseTalk Error] Inference failed: {err_msg}")
                raise RuntimeError(f"MuseTalk inference failed: {err_msg}")

        # 2. Secondary Execution: Standard model_path inference script
        if self.model_path and os.path.exists(self.model_path):
            script_path = os.path.join(self.model_path, "inference.py")
            if os.path.exists(script_path):
                cmd = [
                    "python3", script_path,
                    "--video_path", face_reference_path,
                    "--audio_path", audio_path,
                    "--output_path", output_clip_path,
                    "--device", "mps"
                ]
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                if proc.returncode == 0 and os.path.exists(output_clip_path) and os.path.getsize(output_clip_path) > 1024:
                    verification = await verify_output_media_file(output_clip_path, require_video=True, require_audio=True)
                    if compute_file_hash(output_clip_path) == compute_file_hash(face_reference_path):
                        raise RuntimeError("Neural model error: Generated presenter output is identical to reference MP4.")
                    return output_clip_path
                else:
                    raise RuntimeError(f"MuseTalk inference failed: {stderr.decode('utf-8', errors='ignore')}")

        # DO NOT fall back to FFmpeg -stream_loop -1 for AI Presenter Mode! Raise explicit error.
        raise RuntimeError(
            f"Local presenter model ({self.engine_name}) runtime not found at '{self.musetalk_dir}'. "
            f"Please ensure musetalk-mac environment and inference script exist."
        )
