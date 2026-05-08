import hashlib
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

import models
import schemas
from database import get_db
from config import DATA_DIR, MAX_FILE_SIZE_MB, SUPPORTED_EXTENSIONS

router = APIRouter(prefix="/api/projects/{project_id}/documents", tags=["documents"])


def _get_project_or_404(db: Session, project_id: str) -> models.Project:
    p = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p


def _get_doc_or_404(db: Session, project_id: str, doc_id: str) -> models.Document:
    d = (
        db.query(models.Document)
        .filter(models.Document.id == doc_id, models.Document.project_id == project_id)
        .first()
    )
    if not d:
        raise HTTPException(status_code=404, detail="Document not found")
    return d


def _log(db: Session, project_id: str, action: str, detail: dict):
    entry = models.AuditLog(project_id=project_id, action=action, detail=detail)
    db.add(entry)
    db.commit()


@router.get("", response_model=List[schemas.DocumentOut])
def list_documents(project_id: str, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    docs = (
        db.query(models.Document)
        .filter(models.Document.project_id == project_id)
        .order_by(models.Document.created_at.desc())
        .all()
    )
    return docs


@router.post("", response_model=schemas.DocumentOut, status_code=201)
async def upload_document(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    _get_project_or_404(db, project_id)

    # Validate extension
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Only PDF files are supported. Got: {suffix}")

    content = await file.read()

    # Size check
    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_FILE_SIZE_MB} MB limit")

    file_hash = hashlib.sha256(content).hexdigest()

    # Duplicate check
    existing = (
        db.query(models.Document)
        .filter(
            models.Document.project_id == project_id,
            models.Document.file_hash == file_hash,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"This file was already uploaded (document id: {existing.id})",
        )

    # Save to disk
    project_dir = DATA_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    doc = models.Document(
        project_id=project_id,
        file_name=file.filename,
        file_hash=file_hash,
        file_size=len(content),
        status="pending",
    )
    db.add(doc)
    db.flush()  # get ID before saving file

    file_path = project_dir / f"{doc.id}{suffix}"
    with open(file_path, "wb") as f:
        f.write(content)

    doc.file_path = str(file_path)
    db.commit()
    db.refresh(doc)

    _log(db, project_id, "document_uploaded", {"file_name": file.filename, "doc_id": doc.id})
    return doc


@router.get("/{doc_id}", response_model=schemas.DocumentOut)
def get_document(project_id: str, doc_id: str, db: Session = Depends(get_db)):
    return _get_doc_or_404(db, project_id, doc_id)


@router.patch("/{doc_id}/metadata", response_model=schemas.DocumentOut)
def update_metadata(
    project_id: str,
    doc_id: str,
    payload: schemas.DocumentMetaUpdate,
    db: Session = Depends(get_db),
):
    doc = _get_doc_or_404(db, project_id, doc_id)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(doc, field, value)
    db.commit()
    db.refresh(doc)
    _log(db, project_id, "metadata_updated", {"doc_id": doc_id, **payload.model_dump(exclude_none=True)})
    return doc


@router.delete("/{doc_id}", response_model=schemas.MessageOut)
def delete_document(project_id: str, doc_id: str, db: Session = Depends(get_db)):
    doc = _get_doc_or_404(db, project_id, doc_id)
    file_path = Path(doc.file_path) if doc.file_path else None
    if file_path and file_path.exists():
        file_path.unlink()
    db.delete(doc)
    db.commit()
    _log(db, project_id, "document_deleted", {"doc_id": doc_id})
    return {"message": f"Document {doc_id} deleted."}
