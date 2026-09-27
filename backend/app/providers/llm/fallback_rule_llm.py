import re
from typing import List, Dict, Any
from app.providers.llm.base import LLMProvider
from app.schemas.schemas import LLMScriptBreakdown, LLMSceneItem

class FallbackRuleLLMProvider(LLMProvider):
    """
    Local, deterministic rule-based script analyzer.
    Splits scripts by paragraphs or sentences, calculates durations based on average speech rate (~140 wpm),
    extracts search terms, visual descriptions, and visual transitions cleanly offline.
    """
    async def generate_scene_plan(
        self,
        script_text: str,
        style_profile: Dict[str, Any],
        available_assets: List[Dict[str, Any]]
    ) -> LLMScriptBreakdown:
        title_line = "Video Script"
        lines = [line.strip() for line in script_text.strip().split("\n") if line.strip()]
        
        content_lines = lines
        if lines and len(lines[0]) < 60 and not lines[0].endswith("."):
            title_line = lines[0]
            content_lines = lines[1:]

        body_text = " ".join(content_lines) if content_lines else script_text
        
        # Split into sentences or thought clauses
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', body_text) if s.strip()]
        if not sentences:
            sentences = [script_text]

        # Group short sentences into scenes of ~10-25 words
        grouped_scenes = []
        current_narration = []
        current_word_count = 0

        for sentence in sentences:
            words = sentence.split()
            current_narration.append(sentence)
            current_word_count += len(words)

            if current_word_count >= 15 or sentence.endswith((".", "!", "?")):
                grouped_scenes.append(" ".join(current_narration))
                current_narration = []
                current_word_count = 0

        if current_narration:
            grouped_scenes.append(" ".join(current_narration))

        transitions = ["fade", "crossfade", "slide_left", "slide_right", "zoom"]
        default_dur = style_profile.get("default_scene_duration", 6.0)
        
        scenes: List[LLMSceneItem] = []
        for idx, text in enumerate(grouped_scenes, 1):
            words = text.split()
            # Average reading rate: 2.3 words per second (min 4 sec)
            calc_duration = max(4.0, round(len(words) / 2.3, 1))
            
            # Extract key nouns/words for search terms
            keywords = [w.strip(".,!?;:\"'()").capitalize() for w in words if len(w) > 4 and w.isalpha()]
            search_terms = keywords[:4] if keywords else ["Documentary", "Scene"]
            
            visual_desc = f"Visual footage representing: {text[:60]}..."
            caption_text = text if len(text) <= 50 else text[:47] + "..."
            trans = transitions[(idx - 1) % len(transitions)]

            scenes.append(
                LLMSceneItem(
                    scene_number=idx,
                    narration=text,
                    duration=calc_duration,
                    visual_type="IMAGE",
                    visual_description=visual_desc,
                    search_terms=search_terms,
                    transition=trans,
                    caption=caption_text
                )
            )

        return LLMScriptBreakdown(title=title_line, scenes=scenes)
