"""
SQLAlchemy models — Documents, Pages, Chunks, AuditLogs, Officers.
Uses pgvector for embeddings, tsvector for BM25.
"""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Text, Integer, Float, DateTime, Date,
    Boolean, ForeignKey, Index, func, text
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, TSVECTOR
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


class Document(Base):
    """Top-level document record — one per ingested PDF/TXT."""
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(512), nullable=False, unique=True)
    file_type = Column(String(10), nullable=False)  # pdf | txt
    file_hash = Column(String(64), nullable=False, unique=True)  # SHA-256 for dedup
    total_pages = Column(Integer, default=0)
    policy_date = Column(Date, nullable=True)
    amendment_ids = Column(ARRAY(String), default=[])
    officer_ids = Column(ARRAY(String), default=[])
    metadata_ = Column("metadata", JSONB, default={})
    ingested_at = Column(DateTime, default=datetime.utcnow)

    pages = relationship("Page", back_populates="document", cascade="all, delete-orphan")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Page(Base):
    """Page-level index for BM25 full-text search."""
    __tablename__ = "pages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doc_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_no = Column(Integer, nullable=False)
    raw_text = Column(Text, nullable=False)
    search_vector = Column(
        TSVECTOR,
        # Computed column for tsvector — Alembic migration sets up the trigger
    )

    document = relationship("Document", back_populates="pages")
    chunks = relationship("Chunk", back_populates="page", cascade="all, delete-orphan")

    __table_args__ = (
        Index("pages_fts_idx", "search_vector", postgresql_using="gin"),
        Index("pages_doc_page_idx", "doc_id", "page_no"),
    )


class Chunk(Base):
    """Chunk-level semantic index using pgvector embeddings."""
    __tablename__ = "chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id = Column(UUID(as_uuid=True), ForeignKey("pages.id", ondelete="CASCADE"), nullable=False)
    doc_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)  # order within page
    chunk_text = Column(Text, nullable=False)
    token_count = Column(Integer, default=0)
    embedding = Column(Vector(1536))  # OpenAI text-embedding-3-small = 1536 dims
    metadata_ = Column("metadata", JSONB, default={})

    page = relationship("Page", back_populates="chunks")
    document = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("chunks_vector_idx", "embedding",
              postgresql_using="ivfflat",
              postgresql_ops={"embedding": "vector_cosine_ops"},
              postgresql_with={"lists": 100}),
        Index("chunks_doc_idx", "doc_id"),
    )


class AuditLog(Base):
    """Every query + answer is logged here for auditing and analytics."""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query = Column(Text, nullable=False)
    sanitized_query = Column(Text, nullable=True)
    answer = Column(Text, nullable=True)
    chunks_used = Column(JSONB, default=[])
    llm_used = Column(String(50), nullable=True)
    latency_ms = Column(Integer, nullable=True)
    cost_inr = Column(Float, nullable=True)
    blocked = Column(Boolean, default=False)
    block_reason = Column(Text, nullable=True)
    grounding_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("audit_created_idx", "created_at"),
    )


class Officer(Base):
    """Officer database — Phase 2: link policy documents to named bureaucrats."""
    __tablename__ = "officers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(256), nullable=False)
    designation = Column(String(256), nullable=True)
    ministry = Column(String(256), nullable=True)
    tenure_start = Column(Date, nullable=True)
    tenure_end = Column(Date, nullable=True)
    metadata_ = Column("metadata", JSONB, default={})
