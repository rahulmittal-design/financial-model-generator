import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    ForeignKey, Text, JSON,
)
from sqlalchemy.orm import relationship
from database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=gen_uuid)
    company_name = Column(String, nullable=False)
    ticker = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    base_currency = Column(String, nullable=True)
    fiscal_year_end = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    line_items = relationship("FinancialLineItem", back_populates="project", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="project", cascade="all, delete-orphan")
    model_entries = relationship("FinancialModelEntry", back_populates="project", cascade="all, delete-orphan")
    forecast_entries = relationship("ForecastEntry", back_populates="project", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="project", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=gen_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=True)
    page_count = Column(Integer, nullable=True)
    detected_year = Column(Integer, nullable=True)
    detected_currency = Column(String, nullable=True)
    detected_scale = Column(String, nullable=True)
    status = Column(String, default="pending")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="documents")
    tables = relationship("ExtractedTable", back_populates="document", cascade="all, delete-orphan")
    line_items = relationship("FinancialLineItem", back_populates="document", cascade="all, delete-orphan")


class ExtractedTable(Base):
    __tablename__ = "extracted_tables"

    id = Column(String, primary_key=True, default=gen_uuid)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    page_number = Column(Integer, nullable=True)
    table_type = Column(String, nullable=True)
    raw_data = Column(JSON, nullable=True)
    confidence_score = Column(Float, nullable=True)
    user_confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="tables")
    line_items = relationship("FinancialLineItem", back_populates="table", cascade="all, delete-orphan")


class FinancialLineItem(Base):
    __tablename__ = "financial_line_items"

    id = Column(String, primary_key=True, default=gen_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    table_id = Column(String, ForeignKey("extracted_tables.id"), nullable=True)
    raw_label = Column(String, nullable=True)
    standard_id = Column(String, nullable=True)
    standard_label = Column(String, nullable=True)
    statement_type = Column(String, nullable=True)
    period = Column(String, nullable=True)
    value = Column(Float, nullable=True)
    currency = Column(String, nullable=True)
    scale = Column(String, nullable=True)
    confidence_score = Column(Float, nullable=True)
    review_status = Column(String, default="pending")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="line_items")
    document = relationship("Document", back_populates="line_items")
    table = relationship("ExtractedTable", back_populates="line_items")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=gen_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=True)
    entity_id = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="audit_logs")


# ── Phase 4-6 tables ──────────────────────────────────────────────────────────

class FinancialModelEntry(Base):
    __tablename__ = "financial_model_entries"

    id = Column(String, primary_key=True, default=gen_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    period = Column(String, nullable=False)
    statement_type = Column(String, nullable=False)
    standard_id = Column(String, nullable=False)
    standard_label = Column(String, nullable=False)
    value = Column(Float, nullable=True)
    is_derived = Column(Boolean, default=False)
    source = Column(String, default="extracted")  # "extracted" | "calculated" | "llm"
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="model_entries")


class ForecastEntry(Base):
    __tablename__ = "forecast_entries"

    id = Column(String, primary_key=True, default=gen_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    period = Column(String, nullable=False)
    standard_id = Column(String, nullable=False)
    standard_label = Column(String, nullable=False)
    value = Column(Float, nullable=True)
    assumption = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="forecast_entries")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=gen_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="chat_messages")
