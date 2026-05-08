"""
Map raw annual-report line items to the standard financial schema.
Phase 3: dictionary/rules-based approach with confidence scoring.
LLM assistance is pluggable via the llm_classify() stub.
"""
from __future__ import annotations
import re
from typing import List, Dict, Any, Optional

from services.financial_schema import find_match, load_schema

# Scale multipliers (to normalise raw values)
_SCALE_MULT: Dict[str, float] = {
    "billions": 1_000_000_000,
    "millions": 1_000_000,
    "thousands": 1_000,
    "crores": 10_000_000,
    "lakhs": 100_000,
    "actuals": 1,
}

_NUMERIC_RE = re.compile(r"[-−]?\s*[\d,\.]+")


def map_table_rows(
    table: Dict[str, Any],
    statement_type: str,
    detected_periods: List[str],
    scale: Optional[str] = None,
    currency: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Iterate over table rows and produce line-item mapping candidates.

    Returns a list of dicts matching FinancialLineItem fields.
    """
    rows = table.get("rows", []) or []
    headers = table.get("headers", []) or []

    # Determine which column indices correspond to each period
    period_col_map = _match_period_columns(headers, detected_periods)

    results: List[Dict[str, Any]] = []

    for row in rows:
        cells = _row_to_cells(row, headers)
        label = _extract_label(cells)
        if not label or _is_total_or_junk(label):
            continue

        # Try to map to standard schema
        match = find_match(label)

        for period, col_idx in period_col_map.items():
            raw_val = _get_cell(cells, col_idx)
            norm_val = _parse_number(raw_val, scale)

            results.append({
                "source_label": label,
                "standard_id": match["standard_id"] if match else None,
                "standard_label": match["standard_label"] if match else None,
                "statement_type": match["statement_type"] if match else statement_type,
                "period": period,
                "raw_value": raw_val,
                "normalized_value": norm_val,
                "currency": currency,
                "scale": scale,
                "sign_convention": match.get("sign_convention", "normal") if match else "unknown",
                "mapping_confidence": match["confidence"] if match else 0.0,
                "review_status": "approved" if (match and match["confidence"] >= 0.85) else "pending",
            })

    return results


# ── private helpers ───────────────────────────────────────────────────────────

def _row_to_cells(row: Any, headers: List[str]) -> Dict[str, str]:
    if isinstance(row, dict):
        return {str(k): str(v) for k, v in row.items()}
    if isinstance(row, list):
        return {str(headers[i]) if i < len(headers) else str(i): str(v) for i, v in enumerate(row)}
    return {}


def _extract_label(cells: Dict[str, str]) -> Optional[str]:
    """The label is usually the first non-empty cell."""
    for v in cells.values():
        cleaned = v.strip().strip("*").strip()
        if cleaned and not _looks_numeric(cleaned):
            return cleaned
    return None


def _get_cell(cells: Dict[str, str], col_idx: int) -> str:
    values = list(cells.values())
    if col_idx < len(values):
        return values[col_idx]
    return ""


def _match_period_columns(headers: List[str], periods: List[str]) -> Dict[str, int]:
    """
    Map each detected period to the column index that best represents it.
    Simple heuristic: match year string in header.
    """
    mapping: Dict[str, int] = {}
    for period in periods:
        year = period.replace("FY", "").replace("Q", "")
        for i, h in enumerate(headers):
            if year in str(h):
                mapping[period] = i
                break

    # Fallback: assign columns sequentially if no header match
    if not mapping and periods:
        for j, p in enumerate(periods):
            mapping[p] = j + 1  # col 0 is usually the label

    return mapping


def _is_total_or_junk(label: str) -> bool:
    junk = {"", "-", "—", "–", "nil", "na", "n/a", "notes", "particulars", "description"}
    return label.lower() in junk or len(label) < 2


def _looks_numeric(s: str) -> bool:
    return bool(_NUMERIC_RE.fullmatch(s.replace(",", "").replace(" ", "")))


def _parse_number(raw: str, scale: Optional[str]) -> Optional[float]:
    if not raw:
        return None
    cleaned = raw.replace(",", "").replace(" ", "").replace("−", "-").replace("–", "-")
    cleaned = re.sub(r"[^\d.\-]", "", cleaned)
    try:
        value = float(cleaned)
        if scale and scale in _SCALE_MULT:
            value *= _SCALE_MULT[scale]
        return value
    except ValueError:
        return None


# ── LLM hook (Phase 6) ────────────────────────────────────────────────────────

def llm_classify(label: str, context: str = "") -> Optional[Dict[str, Any]]:
    """
    Placeholder for LLM-assisted classification.
    In Phase 6 this will call the configured local LLM endpoint.
    """
    return None
