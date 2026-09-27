from abc import ABC, abstractmethod
from typing import List, Dict, Any
from app.schemas.schemas import LLMScriptBreakdown

class LLMProvider(ABC):

    @abstractmethod
    async def generate_scene_plan(
        self,
        script_text: str,
        style_profile: Dict[str, Any],
        available_assets: List[Dict[str, Any]]
    ) -> LLMScriptBreakdown:
        """
        Analyzes the user script and generates a structured scene breakdown
        validated against Pydantic schema LLMScriptBreakdown.
        """
        pass
