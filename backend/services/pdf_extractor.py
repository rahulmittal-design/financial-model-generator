"""
PDF extraction service.
Primary: Docling  |  Fallback: pdfplumber
"""
from __future__ import annotations
import re
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional


# ── helpers ───────────────────────────────────────────────────────────────────

def file_checksum(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ── Docling extraction ────────────────────────────────────────────────────────

def extract_with_docling(pdf_path: Path) -> Dict[str, Any]:
    """
    Use Docling to extract text and tables from a PDF.
    Returns a dict with keys: page_count, pages (list of page dicts), tables.
    """
    try:
        from docling.document_converter import DocumentConverter  # type: ignore
        converter = DocumentConverter()
        result = converter.convert(str(pdf_path))
        doc = result.document

        pages: List[Dict] = []
        tables: List[Dict] = []

        # Extract page text
        full_text = doc.export_to_markdown()
        # Split roughly by page if page info available
        page_texts = _split_by_pages(full_text)
        for idx, text in enumerate(page_texts):
            pages.append({"page_number": idx + 1, "text": text})

        # Extract tables via Docling table objects
        for table in getattr(doc, "tables", []):
            try:
                rows = table.export_to_dataframe().values.tolist()
                headers = list(table.export_to_dataframe().columns)
                page_no = getattr(table, "page_no", None)
                tables.append({
                    "page_number": page_no,
                    "headers": [str(h) for h in headers],
                    "rows": [[str(c) for c in row] for row in rows],
                    "confidence": 0.85,
                })
            except Exception:
                pass

        return {
            "success": True,
            "method": "docling",
            "page_count": len(pages),
            "pages": pages,
            "tables": tables,
        }

    except ImportError:
        return {"success": False, "method": "docling", "error": "Docling not installed"}
    except Exception as e:
        return {"success": False, "method": "docling", "error": str(e)}


# ── pdfplumber fallback ───────────────────────────────────────────────────────

def extract_with_pdfplumber(pdf_path: Path) -> Dict[str, Any]:
    """Fallback extractor using pdfplumber."""
    try:
        import pdfplumber  # type: ignore
        pages: List[Dict] = []
        tables: List[Dict] = []

        with pdfplumber.open(str(pdf_path)) as pdf:
            page_count = len(pdf.pages)
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                pages.append({"page_number": i + 1, "text": text})

                for tbl in page.extract_tables() or []:
                    if not tbl:
                        continue
                    headers = [str(c) if c else "" for c in (tbl[0] or [])]
                    rows = [[str(c) if c else "" for c in row] for row in tbl[1:]]
                    tables.append({
                        "page_number": i + 1,
                        "headers": headers,
                        "rows": rows,
                        "confidence": 0.70,
                    })

        return {
            "success": True,
            "method": "pdfplumber",
            "page_count": page_count,
            "pages": pages,
            "tables": tables,
        }

    except ImportError:
        return {"success": False, "method": "pdfplumber", "error": "pdfplumber not installed"}
    except Exception as e:
        return {"success": False, "method": "pdfplumber", "error": str(e)}


# ── primary entry point ───────────────────────────────────────────────────────

def extract_pdf(pdf_path: Path) -> Dict[str, Any]:
    """
    Try Docling first; fall back to pdfplumber.
    Always returns a standard dict regardless of which method succeeded.
    """
    result = extract_with_docling(pdf_path)
    if not result["success"]:
        result = extract_with_pdfplumber(pdf_path)
    return result


# ── metadata detection ────────────────────────────────────────────────────────

_CURRENCY_PATTERNS = {
    "USD": [r"\bUSD\b", r"US\s*Dollar", r"\$"],
    "GBP": [r"\bGBP\b", r"British Pound", r"Sterling", r"£"],
    "EUR": [r"\bEUR\b", r"Euro", r"€"],
    "INR": [r"\bINR\b", r"Indian Rupee", r"₹", r"\bRs\.?\b"],
    "JPY": [r"\bJPY\b", r"Japanese Yen", r"¥"],
}

_SCALE_PATTERNS = {
    "millions": [r"\bmillions?\b", r"\bMn\b", r"\bM\b(?!\w)"],
    "thousands": [r"\bthousands?\b", r"\bKn?\b(?!\w)"],
    "billions": [r"\bbillions?\b", r"\bBn\b"],
    "crores": [r"\bcrores?\b", r"\bCr\.?\b"],
    "lakhs": [r"\blakhs?\b", r"\bLk\.?\b"],
    "actuals": [r"\bactual\b", r"\bin full\b"],
}

_YEAR_PATTERN = re.compile(r"\b(20\d{2}|19\d{2})\b")


def detect_metadata(pages: List[Dict]) -> Dict[str, Any]:
    """Detect currency, scale, and fiscal year from page text."""
    full_text = " ".join(p.get("text", "") for p in pages[:10])  # first 10 pages

    currency = None
    for cur, patterns in _CURRENCY_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, full_text, re.IGNORECASE):
                currency = cur
                break
        if currency:
            break

    scale = None
    for sc, patterns in _SCALE_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, full_text, re.IGNORECASE):
                scale = sc
                break
        if scale:
            break

    years = [int(y) for y in _YEAR_PATTERN.findall(full_text)]
    detected_year = max(years) if years else None

    return {
        "currency": currency,
        "scale": scale,
        "detected_year": detected_year,
    }


# ── private helpers ───────────────────────────────────────────────────────────

def _split_by_pages(text: str) -> List[str]:
    """Naive split: treat each 3000-char block as a page."""
    chunk_size = 3000
    if len(text) <= chunk_size:
        return [text]
    return [text[i: i + chunk_size] for i in range(0, len(text), chunk_size)]


def save_extraction_artifacts(project_dir: Path, doc_id: str, result: Dict) -> Path:
    artifact_path = project_dir / f"{doc_id}_extraction.json"
    with open(artifact_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    return artifact_path
