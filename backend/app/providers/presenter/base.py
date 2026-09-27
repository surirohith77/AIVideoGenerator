from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class PresenterProvider(ABC):

    @abstractmethod
    async def create_presenter_profile(
        self,
        face_reference_path: str,
        voice_reference_path: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Processes reference face video/image & voice audio to prepare reusable Presenter metadata.
        """
        pass

    @abstractmethod
    async def generate_presenter_clip(
        self,
        presenter_id: str,
        face_reference_path: str,
        audio_path: str,
        output_clip_path: str,
        settings: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generates lip-synced / talking-head presenter video clip for specified narration audio track.
        """
        pass
