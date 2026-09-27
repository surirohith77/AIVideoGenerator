from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.models import Project, StyleProfile
from app.schemas.schemas import ProjectCreate, ProjectUpdate, StyleProfileUpdate

def create_project(db: Session, user_id: str, data: ProjectCreate) -> Project:
    project = Project(
        user_id=user_id,
        name=data.name,
        description=data.description
    )
    db.add(project)
    db.flush()

    # Create default style profile
    style_data = data.style.model_dump() if data.style else {}
    style_profile = StyleProfile(
        project_id=project.id,
        **style_data
    )
    db.add(style_profile)
    db.commit()
    db.refresh(project)
    return project

def get_user_projects(db: Session, user_id: str) -> List[Project]:
    return db.query(Project).filter(Project.user_id == user_id).order_by(Project.created_at.desc()).all()

def get_project_by_id(db: Session, project_id: str) -> Optional[Project]:
    return db.query(Project).filter(Project.id == project_id).first()

def update_project(db: Session, project_id: str, data: ProjectUpdate) -> Optional[Project]:
    project = get_project_by_id(db, project_id)
    if not project:
        return None
    if data.name is not None:
        project.name = data.name
    if data.description is not None:
        project.description = data.description
    db.commit()
    db.refresh(project)
    return project

def delete_project(db: Session, project_id: str) -> bool:
    project = get_project_by_id(db, project_id)
    if not project:
        return False
    db.delete(project)
    db.commit()
    return True

def update_style_profile(db: Session, project_id: str, data: StyleProfileUpdate) -> Optional[StyleProfile]:
    style = db.query(StyleProfile).filter(StyleProfile.project_id == project_id).first()
    if not style:
        return None
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(style, field, val)
    db.commit()
    db.refresh(style)
    return style
