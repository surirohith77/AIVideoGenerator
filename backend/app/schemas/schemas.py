from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field

# Auth Schemas
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True

# Presenter Schemas
class PresenterCreate(BaseModel):
    name: str
    description: Optional[str] = None
    consent_confirmed: bool = Field(..., description="Must explicitly confirm consent")
    consent_method: str = "UI_CHECKBOX"

class PresenterUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    face_reference_asset_id: Optional[str] = None
    voice_reference_asset_id: Optional[str] = None
    status: Optional[str] = None

class PresenterResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    face_reference_asset_id: Optional[str] = None
    voice_reference_asset_id: Optional[str] = None
    status: str
    consent_confirmed: bool
    consent_timestamp: Optional[datetime] = None
    consent_method: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# System Capabilities Schema
class SystemCapabilitiesResponse(BaseModel):
    cpu: bool = True
    cpu_count: int = 4
    gpu_available: bool = False
    gpu_name: Optional[str] = None
    gpu_memory_gb: Optional[float] = None
    mps_available: bool = False
    cuda_available: bool = False
    local_llm_available: bool = True
    local_tts_available: bool = True
    local_presenter_available: bool = True
    voice_clone_status: str = "NOT_INSTALLED"
    presenter_model_status: str = "NOT_INSTALLED"
    voice_engine: str = "xtts_v2"
    presenter_engine: str = "musetalk"
    estimated_performance: str = "Good (Local CPU / Engine)"


# StyleProfile Schemas
class StyleProfileBase(BaseModel):
    name: str = "Default Style"
    aspect_ratio: str = "16:9"
    resolution: str = "1080p"
    visual_style: str = "documentary"
    caption_style: str = "bold"
    caption_position: str = "bottom"
    font_family: str = "Inter"
    primary_color: str = "#FFFFFF"
    secondary_color: str = "#FACC15"
    transition: str = "fade"
    default_scene_duration: float = 6.0
    music_volume: float = 0.12
    use_logo: bool = True
    use_intro: bool = False
    use_outro: bool = False
    intro_asset_id: Optional[str] = None
    outro_asset_id: Optional[str] = None
    logo_asset_id: Optional[str] = None
    music_asset_id: Optional[str] = None

class StyleProfileUpdate(BaseModel):
    name: Optional[str] = None
    aspect_ratio: Optional[str] = None
    resolution: Optional[str] = None
    visual_style: Optional[str] = None
    caption_style: Optional[str] = None
    caption_position: Optional[str] = None
    font_family: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    transition: Optional[str] = None
    default_scene_duration: Optional[float] = None
    music_volume: Optional[float] = None
    use_logo: Optional[bool] = None
    use_intro: Optional[bool] = None
    use_outro: Optional[bool] = None
    intro_asset_id: Optional[str] = None
    outro_asset_id: Optional[str] = None
    logo_asset_id: Optional[str] = None
    music_asset_id: Optional[str] = None

class StyleProfileResponse(StyleProfileBase):
    id: str
    project_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Project Schemas
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    style: Optional[StyleProfileBase] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class ProjectResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    style_profile: Optional[StyleProfileResponse] = None

    class Config:
        from_attributes = True

# Asset Schemas
class AssetUpdate(BaseModel):
    filename: Optional[str] = None
    tags: Optional[str] = None
    type: Optional[str] = None

class AssetResponse(BaseModel):
    id: str
    project_id: Optional[str] = None
    type: str
    filename: str
    path: str
    mime_type: Optional[str] = None
    size: int
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    tags: Optional[str] = ""
    metadata_json: Optional[Dict[str, Any]] = {}
    created_at: datetime

    class Config:
        from_attributes = True

# Script & LLM Scene Schemas
class ScriptCreate(BaseModel):
    title: str
    content: str
    mode: Optional[str] = "CONTENT" # PRESENTER or CONTENT
    presenter_id: Optional[str] = None
    presenter_frequency: Optional[str] = "automatic" # automatic, frequent, occasional, intro_outro, never

class ScriptUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

class LLMSceneItem(BaseModel):
    scene_number: int
    scene_mode: str = "MEDIA" # PRESENTER, MEDIA, MIXED, TEXT
    narration: str
    duration: float = 6.0
    visual_type: str = "IMAGE"
    visual_description: str
    search_terms: List[str] = []
    transition: str = "fade"
    caption: str
    presenter_id: Optional[str] = None
    visual_source: str = "USER_ASSET"

class LLMScriptBreakdown(BaseModel):
    title: str
    scenes: List[LLMSceneItem]

class SceneResponse(BaseModel):
    id: str
    script_id: str
    scene_number: int
    scene_mode: str
    presenter_id: Optional[str] = None
    visual_source: str
    visual_prompt: Optional[str] = None
    narration: str
    visual_description: Optional[str] = None
    visual_type: str
    duration: float
    transition: str
    caption: Optional[str] = None
    asset_id: Optional[str] = None
    generated_asset_id: Optional[str] = None
    asset: Optional[AssetResponse] = None
    presenter: Optional[PresenterResponse] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SceneUpdate(BaseModel):
    scene_mode: Optional[str] = None
    presenter_id: Optional[str] = None
    narration: Optional[str] = None
    visual_description: Optional[str] = None
    duration: Optional[float] = None
    transition: Optional[str] = None
    caption: Optional[str] = None
    asset_id: Optional[str] = None

class ScriptResponse(BaseModel):
    id: str
    project_id: str
    title: str
    content: str
    status: str
    scenes: List[SceneResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# VideoJob Schemas
class VideoJobCreate(BaseModel):
    generation_mode: str = "CONTENT" # PRESENTER or CONTENT
    presenter_id: Optional[str] = None

class VideoJobResponse(BaseModel):
    id: str
    project_id: str
    script_id: str
    generation_mode: str
    presenter_id: Optional[str] = None
    status: str
    progress: int
    current_stage: str
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class VideoResponse(BaseModel):
    id: str
    project_id: str
    script_id: Optional[str] = None
    job_id: Optional[str] = None
    title: str
    file_path: str
    duration: float
    width: int
    height: int
    aspect_ratio: str
    created_at: datetime

    class Config:
        from_attributes = True
