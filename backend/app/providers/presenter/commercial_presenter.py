from typing import Dict, Any, Optional
from app.providers.presenter.base import PresenterProvider

class CommercialPresenterProvider(PresenterProvider):
    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    async def create_presenter_profile(self, face_reference_path: str, voice_reference_path: Optional[str] = None, settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        raise NotImplementedError("Commercial cloud presenter API is optional.")

    async def generate_presenter_clip(self, presenter_id: str, face_reference_path: str, audio_path: str, output_clip_path: str, settings: Optional[Dict[str, Any]] = None) -> str:
        raise NotImplementedError("Commercial cloud presenter API is optional.")
