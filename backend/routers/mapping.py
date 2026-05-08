"""
Phase 3: Line-item mapping endpoints.
Run mapping on extracted tables, view, and review mappings.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

import models
import schemas
from database import get_db
from services.line_item_mapper import map_table_rows
from services.financial_schema import get_all_items

router = APIRouter(prefix="/api/projects/{project_id}", tags=["mapping"])


def _get_project_or_404(db: Session, project_id: str) -> models.Project:
    p = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p


def _log(db: Session, project_id: str, action: str, detail: dict):
    entry = models.AuditLog(project_id=project_id, action=action, detail=detail)
    db.add(entry)
    db.commit()


# ── Run mapping for all extracted tables in a project ────────────────────────

@router.post("/run-mapping", response_model=schemas.MessageOut)
def run_mapping(project_id: str, db: Session = Depends(get_db)):
    project = _get_project_or_404(db, project_id)

    # Delete previous line items
    db.query(models.FinancialLineItem).filter(
        models.FinancialLineItem.project_id == project_id
    ).delete()
    db.commit()

    tables = (
        db.query(models.ExtractedTable)
        .join(models.Document)
        .filter(
            models.Document.project_id == project_id,
            models.ExtractedTable.table_type != "unknown",
        )
        .all()
    )

    if not tables:
        raise HTTPException(status_code=400, detail="No classified tables found. Run extraction first.")

    total = 0
    for tbl in tables:
        doc = db.query(models.Document).filter(models.Document.id == tbl.document_id).first()
        scale = doc.detected_scale if doc else None
        currency = doc.detected_currency if doc else None

        rows = map_table_rows(
            table={
                "headers": tbl.headers or [],
                "rows": [
                    [row.get(str(h), "") for h in (tbl.headers or [])]
                    for row in (tbl.raw_data or [])
                ],
            },
            statement_type=tbl.table_type,
            detected_periods=tbl.detected_periods or [],
            scale=scale,
            currency=currency,
        )

        for row in rows:
            item = models.FinancialLineItem(
                project_id=project_id,
                table_id=tbl.id,
                source_document_id=tbl.document_id,
                source_page=tbl.page_number,
                **row,
            )
            db.add(item)
            total += 1

    db.commit()
    _log(db, project_id, "mapping_run", {"items_created": total})
    return {"message": f"Mapping complete. {total} line items created."}


# ── List line items ───────────────────────────────────────────────────────────

@router.get("/line-items", response_model=List[schemas.LineItemOut])
def list_line_items(
    project_id: str,
    statement_type: str = None,
    review_status: str = None,
    db: Session = Depends(get_db),
):
    _get_project_or_404(db, project_id)
    q = db.query(models.FinancialLineItem).filter(
        models.FinancialLineItem.project_id == project_id
    )
    if statement_type:
        q = q.filter(models.FinancialLineItem.statement_type == statement_type)
    if review_status:
        q = q.filter(models.FinancialLineItem.review_status == review_status)
    return q.order_by(
        models.FinancialLineItem.statement_type,
        models.FinancialLineItem.period,
        models.FinancialLineItem.source_label,
    ).all()


# ── Update a single line item mapping ────────────────────────────────────────

@router.patch("/line-items/{item_id}", response_model=schemas.LineItemOut)
def update_line_item(
    project_id: str,
    item_id: str,
    payload: schemas.LineItemUpdate,
    db: Session = Depends(get_db),
):
    item = (
        db.query(models.FinancialLineItem)
        .filter(
            models.FinancialLineItem.id == item_id,
            models.FinancialLineItem.project_id == project_id,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Line item not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    _log(db, project_id, "line_item_updated", {"item_id": item_id, **payload.model_dump(exclude_none=True)})
    return item


# ── Bulk approve/reject ────────────────────────────────────────────────────────

@router.post("/line-items/bulk-approve", response_model=schemas.MessageOut)
def bulk_approve(project_id: str, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    updated = (
        db.query(models.FinancialLineItem)
        .filter(
            models.FinancialLineItem.project_id == project_id,
            models.FinancialLineItem.review_status == "pending",
            models.FinancialLineItem.mapping_confidence >= 0.75,
        )
        .update({"review_status": "approved"})
    )
    db.commit()
    _log(db, project_id, "bulk_approve", {"count": updated})
    return {"message": f"{updated} items approved."}


# ── Get standard schema reference ─────────────────────────────────────────────

@router.get("/schema", tags=["mapping"])
def get_schema():
    return get_all_items()
