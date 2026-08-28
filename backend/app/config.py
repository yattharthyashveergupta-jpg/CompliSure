"""
Configuration management for CompliSure.
Loads settings from environment variables and .env file.
"""
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings for CompliSure."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # API and Server
    APP_NAME: str = "CompliSure Backend"
    API_V1_PREFIX: str = "/api"
    HOST: str = "127.0.0.1"
    PORT: int = 8001
    DEBUG: bool = False
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "*"
    ]

    # AI & Model Configuration
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Google Gemini API Key")
    GEMINI_MODEL: str = "gemini-2.5-flash"
    EMBEDDING_MODEL: str = "text-embedding-004"
    
    # Safeguard & Retrieval Defaults
    DEFAULT_SAFEGUARD_MODE: str = "rag_threshold_verification"
    DEFAULT_EVIDENCE_THRESHOLD: float = 0.75
    DEFAULT_TOP_K: int = 5
    MIN_SUPPORTING_CHUNKS: int = 1
    
    # Document Chunking
    CHUNK_SIZE: int = 400
    CHUNK_OVERLAP: int = 50
    
    # Safety Policies
    REQUIRE_SOURCE_CITATION: bool = True
    ENABLE_ANSWER_VERIFICATION: bool = True
    ALLOW_UNSUPPORTED_ANSWERS: bool = False
    
    # Storage and Persistence
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = Path(__file__).resolve().parent.parent / "data"
    DOCUMENT_STORAGE_DIR: Path = Path(__file__).resolve().parent.parent / "data" / "documents"
    VECTOR_STORAGE_DIR: Path = Path(__file__).resolve().parent.parent / "data" / "chroma"
    DATABASE_URL: str = f"sqlite:///{Path(__file__).resolve().parent.parent}/data/complisure.db"


# Singleton instance
settings = Settings()

# Ensure directories exist
os.makedirs(settings.DOCUMENT_STORAGE_DIR, exist_ok=True)
os.makedirs(settings.VECTOR_STORAGE_DIR, exist_ok=True)
os.makedirs(settings.DATA_DIR, exist_ok=True)
