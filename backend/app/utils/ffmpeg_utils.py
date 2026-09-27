import json
import asyncio
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

async def extract_media_metadata(file_path: str) -> Dict[str, Any]:
    """
    Executes ffprobe to extract duration, width, height, codec, FPS, and audio parameters.
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0 and stdout:
            data = json.loads(stdout.decode("utf-8"))
            format_info = data.get("format", {})
            streams = data.get("streams", [])
            
            duration = float(format_info.get("duration", 0.0))
            width = None
            height = None
            fps = None
            codec_name = None
            has_audio = False

            for s in streams:
                if s.get("codec_type") == "video":
                    width = s.get("width")
                    height = s.get("height")
                    codec_name = s.get("codec_name")
                    r_frame_rate = s.get("r_frame_rate", "")
                    if "/" in r_frame_rate:
                        num, den = r_frame_rate.split("/")
                        if float(den) > 0:
                            fps = round(float(num) / float(den), 2)
                elif s.get("codec_type") == "audio":
                    has_audio = True

            return {
                "duration": duration,
                "width": width,
                "height": height,
                "fps": fps,
                "codec": codec_name,
                "has_audio": has_audio,
                "format_name": format_info.get("format_name"),
                "bit_rate": format_info.get("bit_rate")
            }
    except Exception as e:
        logger.error(f"FFprobe metadata extraction failed for {file_path}: {e}")

    return {"duration": 0.0, "width": None, "height": None}
