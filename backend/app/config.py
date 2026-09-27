import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Video Studio"
    API_V1_STR: str = "/api"
    
    # Database & Redis
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./aivideo.db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Storage
    STORAGE_MODE: str = os.getenv("STORAGE_MODE", "local")
    STORAGE_PATH: str = os.getenv("STORAGE_PATH", os.path.abspath(os.path.join(os.path.dirname(__file__), "../../storage")))
    
    # AI Providers
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "local")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3:latest")
    
    TTS_PROVIDER: str = os.getenv("TTS_PROVIDER", "local")
    IMAGE_PROVIDER: str = os.getenv("IMAGE_PROVIDER", "local")
    VIDEO_PROVIDER: str = os.getenv("VIDEO_PROVIDER", "local")
    
    # Auth
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super-secret-jwt-key-change-in-production-32-chars-min")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "500"))

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
