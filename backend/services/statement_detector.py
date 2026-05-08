"""
Detect which financial statement a table belongs to,
and extract the reporting periods from column headers.
"""
from __future__ import annotations
import re
from typing import Dict, List, Any, Tuple, Optional

# ── Keywords for each statement type ─────────────────────────────────────────

_IS_KEYWORDS = [
    "revenue", "sales", "turnover", "income statement", "profit and loss",
    "p&l", "statement of income", "statement of operations",
    "consolidated statement of profit", "comprehensive income",
    "gross profit", "ebitda", "operating profit", "net profit", "net income",
    "earnings per share", "eps",
]

_BS_KEYWORDS = [
    "balance sheet", "statement of financial position", "financial position",
    "assets", "liabilities", "equity", "shareholders", "stockholders",
    "total assets", "current assets", "non-current assets",
]

_CF_KEYWORDS = [
    "cash flow", "cash flows", "statement of cash flows",
    "operating activities", "investing activities", "financing activities",
    "net cash", "capex", "capital expenditure",
]

_NOTE_KEYWORDS = [
    "notes to", "note ", "accounting policies", "segment information",
]

# ── Period / year detection ───────────────────────────────────────────────────

_YEAR_RE = re.compile(r"\b(20\d{2}|19\d{2})\b")
_FY_RE   = re.compile(r"(?:FY|F\.Y\.?|fiscal year)\s*(\d{2,4})", re.IGNORECASE)
_QTR_RE  = re.compile(r"Q[1-4]\s*(?:FY)?\s*(\d{2,4})", re.IGNORECASE)


def detect_statement_type(table: Dict[str, Any]) -> Tuple[str, float]:
    """
    Returns (statement_type, confidence) where statement_type is one of:
    income_statement | balance_sheet | cash_flow | note | unknown
    """
    text = _table_text(table)

    scores: Dict[str, float] = {
        "income_statement": _score(text, _IS_KEYWORDS),
        "balance_sheet":    _score(text, _BS_KEYWORDS),
        "cash_flow":        _score(text, _CF_KEYWORDS),
        "note":             _score(text, _NOTE_KEYWORDS),
    }

    best_type = max(scores, key=scores.__getitem__)
    best_score = scores[best_type]

    if best_score < 0.10:
        return "unknown", 0.0

    # Normalise to a 0-1 confidence (cap at 1.0)
    confidence = min(1.0, best_score / 0.5)
    return best_type, round(confidence, 3)


def detect_periods(table: Dict[str, Any]) -> List[str]:
    """Extract fiscal year / period strings from table headers."""
    headers = table.get("headers", [])
    header_text = " ".join(str(h) for h in headers)

    periods: List[str] = []

    # FY2024-style
    for m in _FY_RE.finditer(header_text):
        yr = m.group(1)
        if len(yr) == 2:
            yr = "20" + yr
        periods.append(f"FY{yr}")

    # Plain years from headers
    if not periods:
        for m in _YEAR_RE.finditer(header_text):
            periods.append(f"FY{m.group(1)}")

    # Quarter labels
    for m in _QTR_RE.finditer(header_text):
        periods.append(m.group(0).replace(" ", ""))

    return list(dict.fromkeys(periods))  # deduplicate, preserve order


# ── private helpers ───────────────────────────────────────────────────────────

def _table_text(table: Dict[str, Any]) -> str:
    parts: List[str] = []
    parts.extend(str(h) for h in table.get("headers", []))
    for row in (table.get("rows") or [])[:10]:  # first 10 rows
        if isinstance(row, list):
            parts.extend(str(c) for c in row)
        elif isinstance(row, dict):
            parts.extend(str(v) for v in row.values())
    return " ".join(parts).lower()


def _score(text: str, keywords: List[str]) -> float:
    hits = sum(1 for kw in keywords if kw in text)
    return hits / max(len(keywords), 1)
