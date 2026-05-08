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
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Extracted Table ───────────────────────────────────────────────────────────

class ExtractedTableOut(BaseModel):
    id: str
    document_id: str
    page_number: Optional[int]
    table_type: Optional[str]
    raw_data: Optional[Any]
    confidence_score: Optional[float]
    user_confirmed: bool

    class Config:
        from_attributes = True


class ExtractedTableUpdate(BaseModel):
    table_type: Optional[str] = None
    user_confirmed: Optional[bool] = None


# ── Line Item ─────────────────────────────────────────────────────────────────

class LineItemOut(BaseModel):
    id: str
    project_id: str
    document_id: Optional[str]
    table_id: Optional[str]
    raw_label: Optional[str]
    standard_id: Optional[str]
    standard_label: Optional[str]
    statement_type: Optional[str]
    period: Optional[str]
    value: Optional[float]
    currency: Optional[str]
    scale: Optional[str]
    confidence_score: Optional[float]
    review_status: str
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LineItemUpdate(BaseModel):
    standard_id: Optional[str] = None
    standard_label: Optional[str] = None
    statement_type: Optional[str] = None
    period: Optional[str] = None
    value: Optional[float] = None
    review_status: Optional[str] = None
    notes: Optional[str] = None


# ── Audit Log ─────────────────────────────────────────────────────────────────

class AuditLogOut(BaseModel):
    id: str
    project_id: str
    action: str
    entity_type: Optional[str]
    entity_id: Optional[str]
    details: Optional[Any]
    created_at: datetime

    class Config:
        from_attributes = True


# ── FinancialModelEntry ───────────────────────────────────────────────────────

class FinancialModelEntryOut(BaseModel):
    id: str
    project_id: str
    period: str
    statement_type: str
    standard_id: str
    standard_label: str
    value: Optional[float]
    is_derived: bool
    source: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── ForecastEntry ─────────────────────────────────────────────────────────────

class ForecastEntryOut(BaseModel):
    id: str
    project_id: str
    period: str
    standard_id: str
    standard_label: str
    value: Optional[float]
    assumption: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── ChatMessage ───────────────────────────────────────────────────────────────

class ChatMessageIn(BaseModel):
    content: str

class ChatMessageOut(BaseModel):
    id: str
    project_id: str
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── LLM Status ────────────────────────────────────────────────────────────────

class LLMStatusOut(BaseModel):
    loaded: bool
    model_name: Optional[str]
    device: Optional[str]
    quantized: bool
    error: Optional[str]


# ── Model Build ───────────────────────────────────────────────────────────────

class ModelBuildRequest(BaseModel):
    project_id: str
    use_llm: bool = True

class ForecastRequest(BaseModel):
    project_id: str
    forecast_years: int = 3
    use_llm: bool = True

class ExcelExportRequest(BaseModel):
    project_id: str
    include_forecast: bool = True


# ── Statement table ───────────────────────────────────────────────────────────

class StatementRow(BaseModel):
    standard_id: str
    standard_label: str
    values: Dict[str, Optional[float]]
    is_derived: bool = False
    source: str = "extracted"

class StatementTable(BaseModel):
    statement_type: str
    periods: List[str]
    rows: List[StatementRow]

class FinancialModelOut(BaseModel):
    project_id: str
    income_statement: StatementTable
    balance_sheet: StatementTable
    cash_flow: StatementTable
    key_ratios: Dict[str, Dict[str, Optional[float]]]
