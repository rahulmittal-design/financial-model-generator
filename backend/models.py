import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON
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


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=gen_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_hash = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)
    page_count = Column(Integer, nullable=True)
    detected_year = Column(Integer, nullable=True)
    detected_currency = Column(String, nullable=True)
    detected_scale = Column(String, nullable=True)
    # pending | processing | extracted | failed
    status = Column(String, default="pending")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="documents")
    extracted_tables = relationship("ExtractedTable", back_populates="document", cascade="all, delete-orphan")


class ExtractedTable(Base):
    __tablename__ = "extracted_tables"

    id = Column(String, primary_key=True, default=gen_uuid)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    page_number = Column(Integer, nullable=True)
    # unknown | income_statement | balance_sheet | cash_flow | note
    table_type = Column(String, default="unknown")
    detection_confidence = Column(Float, nullable=True)
    detected_periods = Column(JSON, nullable=True)  # list of period strings e.g. ["FY2023","FY2024"]
    raw_data = Column(JSON, nullable=True)          # list of row dicts
    headers = Column(JSON, nullable=True)           # list of column headers
    extraction_confidence = Column(Float, nullable=True)
    user_confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="extracted_tables")
    line_items = relationship("FinancialLineItem", back_populates="source_table", cascade="all, delete-orphan")


class FinancialLineItem(Base):
    __tablename__ = "financial_line_items"

    id = Column(String, primary_key=True, default=gen_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    table_id = Column(String, ForeignKey("extracted_tables.id"), nullable=True)
    statement_type = Column(String, nullable=False)  # income_statement | balance_sheet | cash_flow
    source_label = Column(String, nullable=False)
    standard_id = Column(String, nullable=True)
    standard_label = Column(String, nullable=True)
    period = Column(String, nullable=True)
    raw_value = Column(String, nullable=True)
    normalized_value = Column(Float, nullable=True)
    currency = Column(String, nullable=True)
    scale = Column(String, nullable=True)
    sign_convention = Column(String, default="normal")  # normal | inverted | unknown
    mapping_confidence = Column(Float, nullable=True)
    # pending | approved | rejected | edited
    review_status = Column(String, default="pending")
    source_page = Column(Integer, nullable=True)
    source_document_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="line_items")
    source_table = relationship("ExtractedTable", back_populates="line_items")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=gen_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    action = Column(String, nullable=False)
    detail = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="audit_logs")
