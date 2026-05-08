"""
Phase 5 – Forecast Engine

Uses LLM-generated growth assumptions (or simple CAGR fallbacks) to
project financial line items N years forward, then persists ForecastEntry rows.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from models import FinancialModelEntry, ForecastEntry, Project
from services import llm_service

logger = logging.getLogger(__name__)


def _last_actual_values(
    db: Session, project_id: str
) -> Dict[str, Dict[str, Optional[float]]]:
    """Return {standard_id: {period: value}} for all historical model entries."""
    entries = (
        db.query(FinancialModelEntry)
        .filter(FinancialModelEntry.project_id == project_id)
        .all()
    )
    data: Dict[str, Dict[str, Optional[float]]] = defaultdict(dict)
    for e in entries:
        data[e.standard_id][e.period] = e.value
    return data


def _simple_cagr(values: Dict[str, Optional[float]]) -> float:
    """Compute CAGR from a period->value dict. Falls back to 0.05."""
    sorted_vals = [v for _, v in sorted(values.items()) if v is not None]
    if len(sorted_vals) < 2 or sorted_vals[0] == 0:
        return 0.05
    n = len(sorted_vals) - 1
    try:
        cagr = (sorted_vals[-1] / sorted_vals[0]) ** (1 / n) - 1
        # Clamp to reasonable range
        return max(-0.3, min(0.5, cagr))
    except Exception:
        return 0.05


def _next_periods(historical_periods: List[str], n: int) -> List[str]:
    """Given historical periods like ['FY2021','FY2022','FY2023'], return next N."""
    if not historical_periods:
        return [f"FY{2024 + i}" for i in range(n)]
    last = sorted(historical_periods)[-1]
    # Handle formats: FY2023, 2023, 2023A, FY2023A, etc.
    import re
    match = re.search(r"(\d{4})", last)
    if match:
        year = int(match.group(1))
        prefix = last[: match.start()]
        suffix = re.sub(r"\d{4}", "", last[match.start():])
        return [f"{prefix}{year + i + 1}E" for i in range(n)]
    return [f"FY{2024 + i}E" for i in range(n)]


def build_forecast(
    project_id: str,
    db: Session,
    forecast_years: int = 3,
    use_llm: bool = True,
) -> Dict[str, Any]:
    """
    1. Load historical model entries
    2. Get LLM growth assumptions (or compute CAGR)
    3. Project forward
    4. Persist ForecastEntry rows
    5. Return forecast data
    """
    # 1. Historical data
    historical = _last_actual_values(db, project_id)
    if not historical:
        return {"error": "No historical model data found. Build the financial model first."}

    all_hist_periods = sorted({p for vals in historical.values() for p in vals})
    forecast_periods = _next_periods(all_hist_periods, forecast_years)

    # 2. Assumptions
    assumptions: Dict[str, Dict[str, Any]] = {}

    if use_llm and llm_service.is_loaded():
        project = db.query(Project).filter(Project.id == project_id).first()
        context = f"{project.company_name} ({project.ticker or 'N/A'})" if project else ""
        try:
            result = llm_service.generate_forecast_assumptions(
                historical=historical,
                periods_to_forecast=forecast_periods,
                company_context=context,
            )
            assumptions = result.get("assumptions", {})
        except Exception as e:
            logger.warning(f"LLM forecast assumptions failed: {e}")

    # Fill missing assumptions with CAGR
    for sid, periods_dict in historical.items():
        if sid not in assumptions:
            gr = _simple_cagr(periods_dict)
            assumptions[sid] = {
                "growth_rate": gr,
                "rationale": f"CAGR over {len(periods_dict)} historical periods",
            }

    # 3. Project forward
    forecast_data: Dict[str, Dict[str, float]] = {}
    for sid, periods_dict in historical.items():
        sorted_hist = [v for _, v in sorted(periods_dict.items()) if v is not None]
        if not sorted_hist:
            continue
        base = sorted_hist[-1]
        gr = float(assumptions.get(sid, {}).get("growth_rate", 0.05))
        forecast_data[sid] = {}
        for i, fp in enumerate(forecast_periods):
            forecast_data[sid][fp] = base * ((1 + gr) ** (i + 1))

    # 4. Persist
    db.query(ForecastEntry).filter(ForecastEntry.project_id == project_id).delete()
    for sid, fp_vals in forecast_data.items():
        label = sid.replace("_", " ").title()
        assumption_text = assumptions.get(sid, {}).get("rationale", "")
        for fp, val in fp_vals.items():
            entry = ForecastEntry(
                project_id=project_id,
                period=fp,
                standard_id=sid,
                standard_label=label,
                value=val,
                assumption=assumption_text,
            )
            db.add(entry)
    db.commit()

    # 5. Return
    return {
        "project_id": project_id,
        "forecast_periods": forecast_periods,
        "historical_periods": all_hist_periods,
        "assumptions": assumptions,
        "forecast": forecast_data,
    }
