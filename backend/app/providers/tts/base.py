from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class TTSProvider(ABC):

    @abstractmethod
    async def generate_audio(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        voice_reference_path: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generates audio file from text and saves to output_path.
        Supports voice cloning reference audio path when available.
        """
        pass

