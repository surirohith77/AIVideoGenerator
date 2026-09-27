from typing import List, Dict, Any
from app.providers.llm.base import LLMProvider
from app.schemas.schemas import LLMScriptBreakdown

class OpenAIProvider(LLMProvider):
    """
    Placeholder commercial OpenAI provider interface.
    Allows easy plug-in of paid OpenAI GPT-4o keys in production if desired.
    """
    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    async def generate_scene_plan(
        self,
        script_text: str,
        style_profile: Dict[str, Any],
        available_assets: List[Dict[str, Any]]
    ) -> LLMScriptBreakdown:
        raise NotImplementedError("OpenAI commercial API provider is optional. Enable by supplying API keys.")
