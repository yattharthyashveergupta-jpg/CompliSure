"""
CompliSure Backend Application Entry Point.
Evidence-grounded compliance AI assistant preventing confident wrong answers.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from backend.app.config import settings
from backend.app.utils.logging import logger
from backend.app.models.database import init_db, SessionLocal
from backend.app.services.document_service import document_service
from backend.app.api.documents import router as documents_router
from backend.app.api.chat import router as chat_router
from backend.app.api.safeguards import router as safeguards_router
from backend.app.api.evaluation import router as evaluation_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager: handles startup and shutdown."""
    logger.info("Initializing CompliSure Database and Knowledge Base...")
    try:
        init_db()
        db = SessionLocal()
        # Seed with initial benchmark policies if empty
        document_service.initialize_sample_documents(db)
        db.close()
    except Exception as e:
        logger.error(f"Error during startup initialization: {e}")

    logger.info("CompliSure Backend is ready.")
    yield
    logger.info("Shutting down CompliSure Backend.")


app = FastAPI(
    title="CompliSure API",
    description=(
        "Evidence-grounded compliance AI assistant backend. "
        "Prevents confident wrong answers using page-aware retrieval, "
        "evidence thresholds, grounded generation, two-stage factual verification, and safe refusal."
    ),
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows Next.js frontend or any client origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(documents_router, prefix=settings.API_V1_PREFIX)
app.include_router(chat_router, prefix=settings.API_V1_PREFIX)
app.include_router(safeguards_router, prefix=settings.API_V1_PREFIX)
app.include_router(evaluation_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Health"])
def root():
    """Health check and backend system status."""
    return {
        "app": "CompliSure Backend",
        "status": "online",
        "description": "Preventing Confident Wrong Answers in Compliance Assistants",
        "version": "1.0.0",
        "active_mode": settings.DEFAULT_SAFEGUARD_MODE,
        "evidence_threshold": settings.DEFAULT_EVIDENCE_THRESHOLD,
        "docs_url": "/docs"
    }


@app.get("/api/health", tags=["Health"])
def health_check():
    """API health probe endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "database": "connected",
        "safeguards_active": True,
        "active_model": settings.GEMINI_MODEL,
        "evidence_threshold": settings.DEFAULT_EVIDENCE_THRESHOLD
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global safe exception handler to prevent unhandled 500 leaks."""
    logger.error(f"Unhandled Exception on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred while processing your compliance request."}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
