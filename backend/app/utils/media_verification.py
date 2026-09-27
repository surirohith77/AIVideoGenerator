import os
import json
import shutil
import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def verify_output_media_file(
    file_path: str,
    min_size_bytes: int = 1024,
    require_video: bool = False,
    require_audio: bool = False
) -> Dict[str, Any]:
    """
    Validates output media file using ffprobe.
    Ensures file exists, size > min_size_bytes, duration > 0, and valid streams exist.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Media verification failed: file does not exist at {file_path}")

    file_size = os.path.getsize(file_path)
    if file_size < min_size_bytes:
        raise ValueError(f"Media verification failed: file size ({file_size} bytes) below minimum threshold ({min_size_bytes} bytes).")

    ffprobe_cmd = shutil.which("ffprobe")
    if not ffprobe_cmd:
        # If ffprobe is missing from system PATH, return basic file check
        return {
            "path": file_path,
            "size": file_size,
            "verified_by": "file_size_only"
        }

    cmd = [
        ffprobe_cmd,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise ValueError(f"ffprobe failed to parse file {file_path}: {stderr.decode('utf-8', errors='ignore')}")

    probe_data = json.loads(stdout.decode("utf-8", errors="ignore"))
    format_info = probe_data.get("format", {})
    streams = probe_data.get("streams", [])

    duration = float(format_info.get("duration", 0.0))
    if duration <= 0:
        raise ValueError(f"Media verification failed: file duration is 0 seconds for {file_path}")

    has_video = any(s.get("codec_type") == "video" for s in streams)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)

    if require_video and not has_video:
        raise ValueError(f"Media verification failed: missing required video stream in {file_path}")

    if require_audio and not has_audio:
        raise ValueError(f"Media verification failed: missing required audio stream in {file_path}")

    return {
        "path": file_path,
        "size": file_size,
        "duration": duration,
        "has_video": has_video,
        "has_audio": has_audio,
        "video_streams": [s for s in streams if s.get("codec_type") == "video"],
        "audio_streams": [s for s in streams if s.get("codec_type") == "audio"],
        "verified_by": "ffprobe"
    }
