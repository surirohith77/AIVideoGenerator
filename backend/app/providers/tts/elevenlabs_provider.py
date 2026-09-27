from typing import Optional
from app.providers.tts.base import TTSProvider

class ElevenLabsProvider(TTSProvider):
    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    async def generate_audio(self, text: str, output_path: str, voice: Optional[str] = None) -> str:
        raise NotImplementedError("ElevenLabs commercial TTS is optional. Enable by providing API keys.")
