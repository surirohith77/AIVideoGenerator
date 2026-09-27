import re
from typing import List, Optional, Dict, Any
from app.models.models import Asset

def match_asset_for_scene(
    scene_description: str,
    search_terms: List[str],
    visual_type: str,
    available_assets: List[Asset]
) -> Optional[Asset]:
    """
    Asset matching service.
    Ranks assets based on filename, tags, metadata, and search terms relevance score.
    """
    if not available_assets:
        return None

    # Filter assets by visual category (images or videos)
    matching_assets = [
        a for a in available_assets 
        if a.type in [visual_type, "IMAGE", "VIDEO"]
    ]
    if not matching_assets:
        matching_assets = available_assets

    best_asset = None
    highest_score = -1

    terms = set([t.lower() for t in search_terms if t])
    desc_words = set(re.findall(r'\w+', scene_description.lower()))
    query_words = terms.union(desc_words)

    for asset in matching_assets:
        score = 0
        fn = asset.filename.lower()
        tags = (asset.tags or "").lower()
        
        # Check filename match
        for word in query_words:
            if len(word) > 2 and word in fn:
                score += 3
            if len(word) > 2 and word in tags:
                score += 2

        # Prefer exact type match
        if asset.type == visual_type:
            score += 1

        if score > highest_score:
            highest_score = score
            best_asset = asset

    # Default to first available matching visual asset if no explicit score match
    return best_asset or (matching_assets[0] if matching_assets else None)
