import os
import shutil
import asyncio
import logging
from typing import Optional, Dict, Any
from app.providers.tts.base import TTSProvider

logger = logging.getLogger(__name__)

class LocalSystemTTSProvider(TTSProvider):
    """
    Local System TTS provider using native macOS `say` or Linux `espeak`.
    Used as generic system fallback when voice cloning is not requested or unavailable.
    """
    async def generate_audio(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        voice_reference_path: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> str:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Check macOS `say`
        say_cmd = shutil.which("say")
        if say_cmd:
            aiff_tmp = output_path + ".aiff"
            proc = await asyncio.create_subprocess_exec(
                say_cmd, text, "-o", aiff_tmp,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            if os.path.exists(aiff_tmp):
                conv = await asyncio.create_subprocess_exec(
                    "ffmpeg", "-y", "-i", aiff_tmp, "-ac", "2", "-ar", "44100", output_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await conv.communicate()
                if os.path.exists(aiff_tmp):
                    os.remove(aiff_tmp)
                if os.path.exists(output_path):
                    return output_path

        # Check Linux `espeak`
        espeak_cmd = shutil.which("espeak")
        if espeak_cmd:
            proc = await asyncio.create_subprocess_exec(
                espeak_cmd, "-w", output_path, text,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            if os.path.exists(output_path):
                return output_path

        # Fallback silent audio matching speech duration
        duration = max(3.0, round(len(text.split()) / 2.3, 1))
        conv = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", str(duration), output_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await conv.communicate()
        return output_path

# Alias for backward compatibility
LocalTTSProvider = LocalSystemTTSProvider

