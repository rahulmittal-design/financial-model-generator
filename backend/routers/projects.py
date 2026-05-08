from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

import models
import schemas
from database import get_db

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=List[schemas.ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(models.Project).order_by(models.Project.updated_at.desc()).all()
    result = []
    for p in projects:
        out = schemas.ProjectOut.model_validate(p)
        out.document_count = len(p.documents)
        result.append(out)
    return result


@router.post("", response_model=schemas.ProjectOut, status_code=201)
def create_project(payload: schemas.ProjectCreate, db: Session = Depends(get_db)):
    project = models.Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    _log(db, project.id, "project_created", {"company_name": project.company_name})
    out = schemas.ProjectOut.model_validate(project)
    out.document_count = 0
    return out


@router.get("/{project_id}", response_model=schemas.ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = _get_or_404(db, project_id)
    out = schemas.ProjectOut.model_validate(project)
    out.document_count = len(project.documents)
    return out


@router.patch("/{project_id}", response_model=schemas.ProjectOut)
def update_project(project_id: str, payload: schemas.ProjectUpdate, db: Session = Depends(get_db)):
    project = _get_or_404(db, project_id)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    _log(db, project.id, "project_updated", payload.model_dump(exclude_none=True))
    out = schemas.ProjectOut.model_validate(project)
    out.document_count = len(project.documents)
    return out


@router.delete("/{project_id}", response_model=schemas.MessageOut)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    import shutil
    from config import DATA_DIR
    project = _get_or_404(db, project_id)
    project_dir = DATA_DIR / project_id
    if project_dir.exists():
        shutil.rmtree(project_dir)
    db.delete(project)
    db.commit()
    return {"message": f"Project {project_id} deleted."}


@router.get("/{project_id}/audit-log", response_model=List[schemas.AuditLogOut])
def get_audit_log(project_id: str, db: Session = Depends(get_db)):
    _get_or_404(db, project_id)
    logs = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.project_id == project_id)
        .order_by(models.AuditLog.created_at.desc())
        .limit(200)
        .all()
    )
    return logs


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_or_404(db: Session, project_id: str) -> models.Project:
    p = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p


def _log(db: Session, project_id: str, action: str, detail: dict):
    entry = models.AuditLog(project_id=project_id, action=action, detail=detail)
    db.add(entry)
    db.commit()
