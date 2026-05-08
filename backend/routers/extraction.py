"""
Phase 2: PDF extraction endpoints.
Triggers async extraction and returns results.
"""
import asyncio
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

import models
import schemas
from database import get_db
from config import DATA_DIR
from services.pdf_extractor import extract_pdf, detect_metadata, save_extraction_artifacts
from services.statement_detector import detect_statement_type, detect_periods

router = APIRouter(prefix="/api/projects/{project_id}/documents", tags=["extraction"])


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


# ── Trigger extraction ────────────────────────────────────────────────────────

@router.post("/{doc_id}/extract", response_model=schemas.DocumentOut)
def trigger_extraction(
    project_id: str,
    doc_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    doc = _get_doc_or_404(db, project_id, doc_id)
    if doc.status == "processing":
        raise HTTPException(status_code=409, detail="Extraction already in progress")
    doc.status = "processing"
    db.commit()
    background_tasks.add_task(_run_extraction, project_id, doc_id)
    db.refresh(doc)
    return doc


def _run_extraction(project_id: str, doc_id: str):
    """Background task: runs PDF extraction and saves results."""
    from database import SessionLocal
    db = SessionLocal()
    try:
        doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
        if not doc:
            return

        pdf_path = Path(doc.file_path)
        result = extract_pdf(pdf_path)

        if not result["success"]:
            doc.status = "failed"
            doc.error_message = result.get("error", "Unknown extraction error")
            db.commit()
            return

        # Save artifact
        project_dir = DATA_DIR / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        save_extraction_artifacts(project_dir, doc_id, result)

        # Update document metadata
        meta = detect_metadata(result.get("pages", []))
        doc.page_count = result.get("page_count", 0)
        if not doc.detected_currency:
            doc.detected_currency = meta.get("currency")
        if not doc.detected_scale:
            doc.detected_scale = meta.get("scale")
        if not doc.detected_year:
            doc.detected_year = meta.get("detected_year")

        # Persist extracted tables
        for tbl_data in result.get("tables", []):
            stmt_type, conf = detect_statement_type(tbl_data)
            periods = detect_periods(tbl_data)
            tbl = models.ExtractedTable(
                document_id=doc_id,
                page_number=tbl_data.get("page_number"),
                table_type=stmt_type,
                detection_confidence=conf,
                detected_periods=periods,
                headers=tbl_data.get("headers"),
                raw_data=[
                    {str(h): str(row[i]) if i < len(row) else ""
                     for i, h in enumerate(tbl_data.get("headers", []))}
                    for row in (tbl_data.get("rows") or [])
                ],
                extraction_confidence=tbl_data.get("confidence", 0.7),
            )
            db.add(tbl)

        doc.status = "extracted"
        db.commit()
        _log(db, project_id, "extraction_complete", {
            "doc_id": doc_id,
            "method": result.get("method"),
            "table_count": len(result.get("tables", [])),
        })

    except Exception as e:
        db = SessionLocal()
        doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
        if doc:
            doc.status = "failed"
            doc.error_message = str(e)
            db.commit()
    finally:
        db.close()


# ── Get extracted tables ──────────────────────────────────────────────────────

@router.get("/{doc_id}/tables", response_model=List[schemas.ExtractedTableOut])
def get_tables(project_id: str, doc_id: str, db: Session = Depends(get_db)):
    _get_doc_or_404(db, project_id, doc_id)
    tables = (
        db.query(models.ExtractedTable)
        .filter(models.ExtractedTable.document_id == doc_id)
        .order_by(models.ExtractedTable.page_number)
        .all()
    )
    return tables


@router.patch("/{doc_id}/tables/{table_id}", response_model=schemas.ExtractedTableOut)
def update_table_type(
    project_id: str,
    doc_id: str,
    table_id: str,
    payload: schemas.TableTypeUpdate,
    db: Session = Depends(get_db),
):
    _get_doc_or_404(db, project_id, doc_id)
    tbl = db.query(models.ExtractedTable).filter(models.ExtractedTable.id == table_id).first()
    if not tbl:
        raise HTTPException(status_code=404, detail="Table not found")
    tbl.table_type = payload.table_type
    tbl.user_confirmed = payload.user_confirmed
    db.commit()
    db.refresh(tbl)
    _log(db, project_id, "table_type_updated", {"table_id": table_id, "type": payload.table_type})
    return tbl
