"""
Model Router — Phase 4 / 5 / 6 endpoints

POST /model/{project_id}/build          → build historical model
GET  /model/{project_id}                → retrieve historical model
POST /model/{project_id}/forecast       → run forecast
GET  /model/{project_id}/forecast       → retrieve forecast
GET  /model/{project_id}/export         → download Excel
GET  /model/llm/status                  → LLM status
POST /model/llm/load                    → trigger LLM download/load
POST /model/{project_id}/chat           → chat message
GET  /model/{project_id}/chat           → chat history
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database import get_db
from models import Project, FinancialModelEntry, ForecastEntry, ChatMessage
from schemas import (
    ModelBuildRequest, ForecastRequest, ExcelExportRequest,
    FinancialModelOut, LLMStatusOut, ChatMessageIn, ChatMessageOut,
    ForecastEntryOut, FinancialModelEntryOut,
)
from services import llm_service
from services.model_builder import build_financial_model
from services.forecast_engine import build_forecast
from services.excel_exporter import export_to_excel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/model", tags=["model"])


# ─── LLM management ──────────────────────────────────────────────────────────

@router.get("/llm/status", response_model=LLMStatusOut)
def llm_status():
    return llm_service.get_status()


@router.post("/llm/load")
def llm_load(background_tasks: BackgroundTasks, model_name: Optional[str] = None):
    """Trigger model download/load in background."""
    if llm_service.is_loaded():
        return {"message": "LLM already loaded", "status": llm_service.get_status()}
    background_tasks.add_task(llm_service.load_model, model_name)
    return {"message": "LLM loading started in background. Poll /model/llm/status for updates."}


# ─── Historical model ────────────────────────────────────────────────────────

@router.post("/{project_id}/build")
def build_model(
    project_id: str,
    req: Optional[ModelBuildRequest] = None,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    use_llm = req.use_llm if req else True
    result = build_financial_model(project_id, db, use_llm=use_llm)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{project_id}")
def get_model(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    entries = (
        db.query(FinancialModelEntry)
        .filter(FinancialModelEntry.project_id == project_id)
        .all()
    )
    if not entries:
        raise HTTPException(status_code=404, detail="No model built yet. POST /model/{id}/build first.")

    # Re-assemble from DB (cheap read, no re-computation)
    from collections import defaultdict
    from services.model_builder import IS_ITEMS, BS_ITEMS, CF_ITEMS, _compute_ratios

    data: dict = defaultdict(dict)
    derived_flags: dict = {}
    stmt_map: dict = {}
    for e in entries:
        data[e.standard_id][e.period] = e.value
        if e.is_derived:
            derived_flags[e.standard_id] = True
        stmt_map[e.standard_id] = e.statement_type

    all_periods = sorted({p for vals in data.values() for p in vals})

    def _table(stmt_type, item_ids):
        rows = []
        for sid in item_ids:
            if sid not in data:
                continue
            rows.append({
                "standard_id": sid,
                "standard_label": sid.replace("_", " ").title(),
                "values": {p: data[sid].get(p) for p in all_periods},
                "is_derived": derived_flags.get(sid, False),
                "source": "calculated" if derived_flags.get(sid) else "extracted",
            })
        return {"statement_type": stmt_type, "periods": all_periods, "rows": rows}

    ratios = _compute_ratios(data)
    return {
        "project_id": project_id,
        "income_statement": _table("income_statement", IS_ITEMS),
        "balance_sheet": _table("balance_sheet", BS_ITEMS),
        "cash_flow": _table("cash_flow", CF_ITEMS),
        "key_ratios": ratios,
    }


# ─── Forecast ────────────────────────────────────────────────────────────────

@router.post("/{project_id}/forecast")
def run_forecast(
    project_id: str,
    req: Optional[ForecastRequest] = None,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    forecast_years = req.forecast_years if req else 3
    use_llm = req.use_llm if req else True
    result = build_forecast(project_id, db, forecast_years=forecast_years, use_llm=use_llm)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{project_id}/forecast")
def get_forecast(project_id: str, db: Session = Depends(get_db)):
    entries = (
        db.query(ForecastEntry)
        .filter(ForecastEntry.project_id == project_id)
        .all()
    )
    if not entries:
        raise HTTPException(status_code=404, detail="No forecast found.")
    from collections import defaultdict
    data: dict = defaultdict(dict)
    assumptions: dict = {}
    for e in entries:
        data[e.standard_id][e.period] = e.value
        if e.assumption:
            assumptions[e.standard_id] = e.assumption
    periods = sorted({p for vals in data.values() for p in vals})
    return {
        "project_id": project_id,
        "forecast_periods": periods,
        "forecast": {sid: dict(pvals) for sid, pvals in data.items()},
        "assumptions": assumptions,
    }


# ─── Excel export ────────────────────────────────────────────────────────────

@router.get("/{project_id}/export")
def export_excel(
    project_id: str,
    include_forecast: bool = True,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        data = export_to_excel(project_id, db, include_forecast=include_forecast)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    filename = f"{project.company_name.replace(' ', '_')}_FinancialModel.xlsx"
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── Chat ────────────────────────────────────────────────────────────────────

@router.post("/{project_id}/chat", response_model=ChatMessageOut)
def post_chat(
    project_id: str,
    msg: ChatMessageIn,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Save user message
    user_msg = ChatMessage(project_id=project_id, role="user", content=msg.content)
    db.add(user_msg)
    db.commit()

    # Load recent history
    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.project_id == project_id)
        .order_by(ChatMessage.created_at)
        .limit(20)
        .all()
    )
    history_dicts = [{"role": h.role, "content": h.content} for h in history[:-1]]  # exclude current

    # Build project summary
    entries = (
        db.query(FinancialModelEntry)
        .filter(FinancialModelEntry.project_id == project_id)
        .limit(50)
        .all()
    )
    summary_lines = [f"{project.company_name} ({project.ticker or 'N/A'})"]
    for e in entries[:30]:
        summary_lines.append(f"{e.standard_id} [{e.period}]: {e.value}")
    project_summary = "\n".join(summary_lines)

    # Generate response
    reply = llm_service.chat_about_financials(
        project_summary=project_summary,
        conversation_history=history_dicts,
        user_message=msg.content,
    )

    # Save assistant message
    asst_msg = ChatMessage(project_id=project_id, role="assistant", content=reply)
    db.add(asst_msg)
    db.commit()
    db.refresh(asst_msg)

    return asst_msg


@router.get("/{project_id}/chat", response_model=List[ChatMessageOut])
def get_chat(project_id: str, limit: int = 50, db: Session = Depends(get_db)):
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.project_id == project_id)
        .order_by(ChatMessage.created_at)
        .limit(limit)
        .all()
    )
