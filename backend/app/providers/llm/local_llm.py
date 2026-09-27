import json
import logging
import httpx
from typing import List, Dict, Any
from app.providers.llm.base import LLMProvider
from app.providers.llm.fallback_rule_llm import FallbackRuleLLMProvider
from app.schemas.schemas import LLMScriptBreakdown
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert video producer AI.
Analyze the user script and breakdown the script into scenes for a video.
Respond ONLY with a valid JSON object matching this strict schema:
{
  "title": "Title of script",
  "scenes": [
    {
      "scene_number": 1,
      "narration": "Exact text to be spoken in scene",
      "duration": 6.5,
      "visual_type": "IMAGE",
      "visual_description": "Detailed description of scene image or video asset needed",
      "search_terms": ["term1", "term2"],
      "transition": "fade",
      "caption": "Short text for caption overlay"
    }
  ]
}
Do not include any explanation or markdown backticks outside of the JSON.
"""

class LocalLLMProvider(LLMProvider):
    def __init__(self):
        self.base_url = settings.LLM_BASE_URL.rstrip("/")
        self.model = settings.LLM_MODEL
        self.fallback = FallbackRuleLLMProvider()

    async def generate_scene_plan(
        self,
        script_text: str,
        style_profile: Dict[str, Any],
        available_assets: List[Dict[str, Any]]
    ) -> LLMScriptBreakdown:
        asset_names = [a.get("filename", "") for a in available_assets]
        prompt = f"""Style Profile: {json.dumps(style_profile, default=str)}
Available Asset Names: {json.dumps(asset_names, default=str)}

SCRIPT:
{script_text}
"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(
                    f"{self.base_url}/chat/completions",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.2
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    # Clean markdown codeblocks if present
                    if content.startswith("```"):
                        content = content.split("```", 2)[1]
                        if content.startswith("json"):
                            content = content[4:]
                    content = content.strip()
                    parsed = json.loads(content)
                    return LLMScriptBreakdown(**parsed)
                else:
                    logger.warning(f"Local LLM API returned status {res.status_code}. Using rule-based fallback.")
        except Exception as e:
            logger.info(f"Local LLM endpoint unreachable ({e}). Falling back to rule-based script analyzer.")

        return await self.fallback.generate_scene_plan(script_text, style_profile, available_assets)
