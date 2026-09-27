import asyncio
import os
from app.providers.image.base import ImageProvider

class LocalImageProvider(ImageProvider):
    """
    Local image provider interface.
    Generates dynamic solid/gradient background images using FFmpeg when offline.
    """
    async def generate_image(self, prompt: str, output_path: str, width: int = 1920, height: int = 1080) -> str:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        # Use FFmpeg to draw color background with label text
        cmd = [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c=0x1e293b:s={width}x{height}:d=1",
            "-frames:v", "1", output_path
        ]
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await proc.communicate()
        return output_path
