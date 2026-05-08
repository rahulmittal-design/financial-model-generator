from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime


# ── Project ──────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    company_name: str
    ticker: Optional[str] = None
    sector: Optional[str] = None
    base_currency: Optional[str] = None
    fiscal_year_end: Optional[str] = None


class ProjectUpdate(BaseModel):
    company_name: Optional[str] = None
    ticker: Optional[str] = None
    sector: Optional[str] = None
    base_currency: Optional[str] = None
    fiscal_year_end: Optional[str] = None


class ProjectOut(BaseModel):
    id: str
    company_name: str
    ticker: Optional[str]
    sector: Optional[str]
    base_currency: Optional[str]
    fiscal_year_end: Optional[str]
    created_at: datetime
    updated_at: datetime
    document_count: int = 0

    class Config:
        from_attributes = True


# ── Document ──────────────────────────────────────────────────────────────────

class DocumentOut(BaseModel):
    id: str
    project_id: str
    file_name: str
    file_size: Optional[int]
    page_count: Optional[int]
    detected_year: Optional[int]
    detected_currency: Optional[str]
    detected_scale: Optional[str]
    status: str
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentMetaUpdate(BaseModel):
    detected_year: Optional[int] = None
    detected_currency: Optional[str] = None
    detected_scale: Optional[str] = None


# ── Extracted Table ───────────────────────────────────────────────────────────

class ExtractedTableOut(BaseModel):
    id: str
    document_id: str
    page_number: Optional[int]
    table_type: str
    detection_confidence: Optional[float]
    detected_periods: Optional[List[str]]
    headers: Optional[List[str]]
    raw_data: Optional[List[Dict[str, Any]]]
    extraction_confidence: Optional[float]
    user_confirmed: bool

    class Config:
        from_attributes = True


class TableTypeUpdate(BaseModel):
    table_type: str  # income_statement | balance_sheet | cash_flow | note | unknown
    user_confirmed: bool = True


# ── Line Item ─────────────────────────────────────────────────────────────────

class LineItemOut(BaseModel):
    id: str
    project_id: str
    table_id: Optional[str]
    statement_type: str
    source_label: str
    standard_id: Optional[str]
    standard_label: Optional[str]
    period: Optional[str]
    raw_value: Optional[str]
    normalized_value: Optional[float]
    currency: Optional[str]
    scale: Optional[str]
    sign_convention: str
    mapping_confidence: Optional[float]
    review_status: str
    source_page: Optional[int]
    source_document_id: Optional[str]

    class Config:
        from_attributes = True


class LineItemUpdate(BaseModel):
    standard_id: Optional[str] = None
    standard_label: Optional[str] = None
    normalized_value: Optional[float] = None
    sign_convention: Optional[str] = None
    review_status: Optional[str] = None


# ── Audit Log ─────────────────────────────────────────────────────────────────

class AuditLogOut(BaseModel):
    id: str
    project_id: str
    action: str
    detail: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Generic ───────────────────────────────────────────────────────────────────

class MessageOut(BaseModel):
    message: str
