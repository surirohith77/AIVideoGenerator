from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.models import Script, Scene, Project, Asset, Presenter
from app.schemas.schemas import ScriptCreate, ScriptUpdate, SceneUpdate
from app.providers.llm.local_llm import LocalLLMProvider
from app.services.asset_matching_service import match_asset_for_scene

llm_provider = LocalLLMProvider()

def create_script(db: Session, project_id: str, data: ScriptCreate) -> Script:
    script = Script(
        project_id=project_id,
        title=data.title,
        content=data.content,
        status="DRAFT"
    )
    db.add(script)
    db.commit()
    db.refresh(script)
    return script

def get_project_scripts(db: Session, project_id: str) -> List[Script]:
    return db.query(Script).filter(Script.project_id == project_id).order_by(Script.created_at.desc()).all()

def get_script_by_id(db: Session, script_id: str) -> Optional[Script]:
    return db.query(Script).filter(Script.id == script_id).first()

def update_script(db: Session, script_id: str, data: ScriptUpdate) -> Optional[Script]:
    script = get_script_by_id(db, script_id)
    if not script:
        return None
    if data.title is not None:
        script.title = data.title
    if data.content is not None:
        script.content = data.content
    db.commit()
    db.refresh(script)
    return script

def delete_script(db: Session, script_id: str) -> bool:
    script = get_script_by_id(db, script_id)
    if not script:
        return False
    db.delete(script)
    db.commit()
    return True

def determine_scene_mode(
    scene_idx: int,
    total_scenes: int,
    mode: str, # "PRESENTER" or "CONTENT"
    frequency: str = "automatic",
    has_presenter: bool = False
) -> str:
    if not has_presenter:
        return "MEDIA"
    if mode == "PRESENTER":
        return "PRESENTER"

    if frequency == "never":
        return "MEDIA"
    elif frequency == "intro_outro":
        return "PRESENTER" if (scene_idx == 1 or scene_idx == total_scenes) else "MEDIA"
    elif frequency == "frequent":
        return "PRESENTER" if (scene_idx % 2 != 0) else "MEDIA"
    elif frequency == "occasional":
        return "PRESENTER" if (scene_idx == 1 or scene_idx == total_scenes or scene_idx % 4 == 0) else "MEDIA"

    # Default "automatic" hybrid balance: presenter for intro, middle transition (if >5 scenes), and outro
    if scene_idx == 1 or scene_idx == total_scenes or (total_scenes > 5 and scene_idx == (total_scenes // 2) + 1):
        return "PRESENTER"
    return "MEDIA"

async def analyze_script_and_create_scenes(
    db: Session,
    script_id: str,
    mode: str = "CONTENT",
    presenter_id: Optional[str] = None,
    presenter_frequency: str = "automatic"
) -> List[Scene]:
    script = get_script_by_id(db, script_id)
    if not script:
        raise ValueError("Script not found")

    project = db.query(Project).filter(Project.id == script.project_id).first()
    style_dict = {}
    if project and project.style_profile:
        sp = project.style_profile
        style_dict = {
            "name": sp.name,
            "aspect_ratio": sp.aspect_ratio,
            "resolution": sp.resolution,
            "visual_style": sp.visual_style,
            "caption_style": sp.caption_style,
            "caption_position": sp.caption_position,
            "font_family": sp.font_family,
            "primary_color": sp.primary_color,
            "secondary_color": sp.secondary_color,
            "transition": sp.transition,
            "default_scene_duration": sp.default_scene_duration,
            "music_volume": sp.music_volume,
            "use_logo": sp.use_logo
        }
    available_assets = db.query(Asset).filter(Asset.project_id == script.project_id).all()
    assets_data = [{"filename": a.filename, "tags": a.tags, "type": a.type} for a in available_assets]

    # Delete existing scenes if re-analyzing
    db.query(Scene).filter(Scene.script_id == script_id).delete()

    # Call LLM Provider / Fallback rule analyzer
    breakdown = await llm_provider.generate_scene_plan(
        script_text=script.content,
        style_profile=style_dict,
        available_assets=assets_data
    )

    has_presenter = bool(presenter_id)
    total_scenes = len(breakdown.scenes)
    created_scenes = []

    for idx, item in enumerate(breakdown.scenes, 1):
        scene_mode = item.scene_mode if (hasattr(item, 'scene_mode') and item.scene_mode != "MEDIA") else determine_scene_mode(
            scene_idx=idx,
            total_scenes=total_scenes,
            mode=mode,
            frequency=presenter_frequency,
            has_presenter=has_presenter
        )

        matched_asset = None
        if scene_mode == "MEDIA":
            matched_asset = match_asset_for_scene(
                scene_description=item.visual_description,
                search_terms=item.search_terms,
                visual_type=item.visual_type,
                available_assets=available_assets
            )
        
        scene = Scene(
            script_id=script_id,
            scene_number=item.scene_number,
            scene_mode=scene_mode,
            presenter_id=presenter_id if scene_mode == "PRESENTER" else None,
            visual_source="USER_ASSET" if matched_asset else "NONE",
            visual_prompt=item.visual_description,
            narration=item.narration,
            visual_description=item.visual_description,
            visual_type=item.visual_type,
            duration=item.duration,
            transition=item.transition,
            caption=item.caption,
            asset_id=matched_asset.id if matched_asset else None,
            status="PLANNED"
        )
        db.add(scene)
        created_scenes.append(scene)

    script.status = "ANALYZED"
    db.commit()
    
    for sc in created_scenes:
        db.refresh(sc)
    return created_scenes

def update_scene(db: Session, scene_id: str, data: SceneUpdate) -> Optional[Scene]:
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if not scene:
        return None
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(scene, field, val)
    db.commit()
    db.refresh(scene)
    return scene
