"""
SQLAlchemy Database Models and Session setup for CompliSure.
Uses SQLite for simple, lightweight persistence.
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Float, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.config import settings

Base = declarative_base()


class DocumentModel(Base):
    """Uploaded compliance document metadata."""
    __tablename__ = "documents"

    id = Column(String(64), primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    pages = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    status = Column(String(50), default="Indexed")
    file_path = Column(String(512), nullable=False)
    file_size_bytes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class ChunkModel(Base):
    """Page-aware text chunk stored in database."""
    __tablename__ = "chunks"

    id = Column(String(128), primary_key=True, index=True)
    document_id = Column(String(64), index=True, nullable=False)
    document_name = Column(String(255), nullable=False)
    page_number = Column(Integer, nullable=False)
    section = Column(String(255), nullable=True)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    char_count = Column(Integer, default=0)


class ChatLogModel(Base):
    """Audit log of user questions, retrieved evidence, and safeguard decisions."""
    __tablename__ = "chat_logs"

    id = Column(String(64), primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    question = Column(Text, nullable=False)
    mode = Column(String(50), nullable=False)
    decision = Column(String(20), nullable=False)  # ANSWER or REFUSE
    answer = Column(Text, nullable=False)
    evidence_status = Column(String(20), nullable=False)
    verification = Column(String(30), nullable=False)
    refusal_reason = Column(Text, nullable=True)
    sources_json = Column(Text, default="[]")
    confidence_score = Column(Float, default=0.0)
    latency_ms = Column(Float, default=0.0)


class EvaluationRunModel(Base):
    """Historical evaluation runs and benchmark results."""
    __tablename__ = "evaluation_runs"

    id = Column(String(64), primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    test_set_size = Column(Integer, nullable=False)
    results_json = Column(Text, nullable=False)
    logs_json = Column(Text, nullable=False)


# Initialize SQLite Engine and Session
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for obtaining database sessions in FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
