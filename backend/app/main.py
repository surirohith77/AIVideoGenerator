import os
import sys

# Ensure monorepo root is in sys.path so 'renderer' and shared packages resolve cleanly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.db.session import engine, Base
from app.api import auth, projects, styles, assets, scripts, jobs, videos, presenters, system

from sqlalchemy import text

# Create database tables automatically for SQLite/Dev
Base.metadata.create_all(bind=engine)

# Ensure SQLite database columns are updated if missing
if "sqlite" in settings.DATABASE_URL:
    try:
        with engine.connect() as conn:
            # 1. assets.project_id nullable fix
            res_assets = conn.execute(text("PRAGMA table_info(assets);")).fetchall()
            for col in res_assets:
                if col[1] == "project_id" and col[3] == 1:
                    conn.execute(text("PRAGMA foreign_keys=OFF;"))
                    conn.execute(text("""
                        CREATE TABLE assets_new (
                            id VARCHAR NOT NULL, 
                            project_id VARCHAR, 
                            type VARCHAR(50) NOT NULL, 
                            filename VARCHAR(255) NOT NULL, 
                            path VARCHAR(1000) NOT NULL, 
                            mime_type VARCHAR(100), 
                            size INTEGER NOT NULL, 
                            duration FLOAT, 
                            width INTEGER, 
                            height INTEGER, 
                            tags VARCHAR(500), 
                            metadata_json JSON, 
                            created_at DATETIME NOT NULL, 
                            PRIMARY KEY (id), 
                            FOREIGN KEY(project_id) REFERENCES projects (id)
                        );
                    """))
                    conn.execute(text("INSERT INTO assets_new SELECT * FROM assets;"))
                    conn.execute(text("DROP TABLE assets;"))
                    conn.execute(text("ALTER TABLE assets_new RENAME TO assets;"))
                    conn.execute(text("PRAGMA foreign_keys=ON;"))
                    conn.commit()
                    break

            # 2. scenes missing columns fix
            res_scenes = conn.execute(text("PRAGMA table_info(scenes);")).fetchall()
            scene_cols = [col[1] for col in res_scenes]
            if "scene_mode" not in scene_cols:
                conn.execute(text("ALTER TABLE scenes ADD COLUMN scene_mode VARCHAR(50) DEFAULT 'MEDIA';"))
            if "presenter_id" not in scene_cols:
                conn.execute(text("ALTER TABLE scenes ADD COLUMN presenter_id VARCHAR;"))
            if "visual_source" not in scene_cols:
                conn.execute(text("ALTER TABLE scenes ADD COLUMN visual_source VARCHAR(50) DEFAULT 'USER_ASSET';"))
            if "visual_prompt" not in scene_cols:
                conn.execute(text("ALTER TABLE scenes ADD COLUMN visual_prompt TEXT;"))

            # 3. video_jobs missing columns fix
            res_jobs = conn.execute(text("PRAGMA table_info(video_jobs);")).fetchall()
            job_cols = [col[1] for col in res_jobs]
            if "generation_mode" not in job_cols:
                conn.execute(text("ALTER TABLE video_jobs ADD COLUMN generation_mode VARCHAR(50) DEFAULT 'CONTENT';"))
            if "presenter_id" not in job_cols:
                conn.execute(text("ALTER TABLE video_jobs ADD COLUMN presenter_id VARCHAR;"))

            conn.commit()
    except Exception:
        pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Local-First Script-to-Video AI Studio Backend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(system.router, prefix=settings.API_V1_STR)
app.include_router(presenters.router, prefix=settings.API_V1_STR)
app.include_router(projects.router, prefix=settings.API_V1_STR)
app.include_router(styles.router, prefix=settings.API_V1_STR)
app.include_router(assets.router, prefix=settings.API_V1_STR)
app.include_router(scripts.router, prefix=settings.API_V1_STR)
app.include_router(jobs.router, prefix=settings.API_V1_STR)
app.include_router(videos.router, prefix=settings.API_V1_STR)

# Mount local storage folder to serve assets directly in dev
os.makedirs(settings.STORAGE_PATH, exist_ok=True)
app.mount("/static/storage", StaticFiles(directory=settings.STORAGE_PATH), name="storage")

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "storage_mode": settings.STORAGE_MODE,
        "llm_provider": settings.LLM_PROVIDER,
        "tts_provider": settings.TTS_PROVIDER
    }
