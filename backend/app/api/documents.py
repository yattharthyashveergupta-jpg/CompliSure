"""
Document Management Endpoints.
Handles PDF upload, validation, page extraction, chunk viewing, and deletion.
"""
from typing import List
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.models.schemas import DocumentSummary, DocumentDetail
from backend.app.models.database import get_db
from backend.app.services.document_service import document_service
from backend.app.services.pdf_service import PDFProcessingError
from backend.app.utils.logging import logger

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/upload",
    response_model=DocumentSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and index a compliance PDF"
)
async def upload_document(
    file: UploadFile = File(..., description="Compliance PDF file to ingest"),
    db: Session = Depends(get_db)
):
    """
    Accepts a PDF document, validates format, extracts text page-by-page preserving
    exact page numbers, performs page-aware chunking, and indexes chunks into the vector store.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF documents (.pdf) are permitted."
        )

    try:
        content = await file.read()
        summary = document_service.ingest_pdf_file(
            file_bytes=content,
            filename=file.filename,
            db=db
        )
        return summary
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except PDFProcessingError as pe:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(pe))
    except Exception as e:
        logger.error(f"Unexpected error during document upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing and indexing the document."
        )


@router.get(
    "",
    response_model=List[DocumentSummary],
    summary="List all indexed compliance documents"
)
def list_documents(db: Session = Depends(get_db)):
    """Retrieves all approved and indexed compliance documents with metadata."""
    return document_service.list_documents(db)


@router.get(
    "/{document_id}",
    response_model=DocumentDetail,
    summary="Get document details and chunk metadata"
)
def get_document(document_id: str, db: Session = Depends(get_db)):
    """Fetches full document details including its individual page-aware chunks."""
    doc = document_service.get_document_detail(document_id, db)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' was not found."
        )
    return doc


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete document and remove indexed chunks"
)
def delete_document(document_id: str, db: Session = Depends(get_db)):
    """Deletes a document from storage, SQLite database, and vector index."""
    success = document_service.delete_document(document_id, db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' was not found."
        )
    return {"message": f"Document '{document_id}' successfully removed from knowledge base."}


@router.post(
    "/init-samples",
    response_model=List[DocumentSummary],
    summary="Initialize or reset sample benchmark policies"
)
def init_sample_documents(db: Session = Depends(get_db)):
    """Generates and indexes the official sample compliance policy documents."""
    document_service.initialize_sample_documents(db)
    return document_service.list_documents(db)
