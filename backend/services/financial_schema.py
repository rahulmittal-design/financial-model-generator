"""Load and query the standard financial schema."""
import yaml
from pathlib import Path
from typing import Optional, Dict, List, Any

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "data" / "financial_schema.yaml"
_schema: Optional[Dict] = None


def load_schema() -> Dict:
    global _schema
    if _schema is None:
        with open(_SCHEMA_PATH) as f:
            _schema = yaml.safe_load(f)
    return _schema


def get_all_items() -> List[Dict[str, Any]]:
    schema = load_schema()
    items = []
    for stmt_type, entries in schema.items():
        for entry in entries:
            items.append({**entry, "statement_type": stmt_type})
    return items


def find_match(label: str) -> Optional[Dict[str, Any]]:
    """Best-effort dictionary match of a raw label to a standard line item."""
    normalised = _normalise(label)
    best = None
    best_score = 0.0

    for item in get_all_items():
        for alias in item.get("aliases", []):
            score = _similarity(normalised, _normalise(alias))
            if score > best_score:
                best_score = score
                best = item

    if best_score >= 0.75:
        return {
            "standard_id": best["id"],
            "standard_label": best["label"],
            "statement_type": best["statement_type"],
            "sign_convention": "inverted" if best.get("sign") == "negative" else "normal",
            "confidence": round(best_score, 3),
        }
    return None


def _normalise(text: str) -> str:
    import re
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _similarity(a: str, b: str) -> float:
    """Token Jaccard similarity."""
    set_a = set(a.split())
    set_b = set(b.split())
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    # Bonus for exact match
    if a == b:
        return 1.0
    jaccard = len(intersection) / len(union)
    # Bonus if one is a substring of the other
    if a in b or b in a:
        jaccard = min(1.0, jaccard + 0.15)
    return jaccard
