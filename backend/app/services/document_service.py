"""
Document Management Service.
Coordinates PDF validation, page-aware text extraction, chunking, database persistence, and vector indexing.
Includes automatic generation of benchmark sample compliance policy PDFs.
"""
from typing import List, Optional
import uuid
import os
import shutil
from pathlib import Path
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from backend.app.models.database import DocumentModel, ChunkModel, SessionLocal
from backend.app.models.schemas import DocumentSummary, DocumentDetail, ChunkMetadata, DocStatus, DocumentChunk
from backend.app.services.pdf_service import pdf_service, PDFProcessingError
from backend.app.services.chunking_service import chunking_service
from backend.app.services.retrieval_service import vector_store
from backend.app.config import settings
from backend.app.utils.logging import logger


class DocumentService:
    """Manages compliance document lifecycle and sample policy generation."""

    def __init__(self):
        self.storage_dir = settings.DOCUMENT_STORAGE_DIR

    def ingest_pdf_file(self, file_bytes: bytes, filename: str, db: Session) -> DocumentSummary:
        """Processes an uploaded PDF and indexes all page chunks."""
        # 1. Validation
        if not filename.lower().endswith(".pdf"):
            raise ValueError("Only PDF documents (.pdf) are supported.")
        if len(file_bytes) > 50 * 1024 * 1024:
            raise ValueError("File exceeds maximum allowed size of 50 MB.")

        doc_id = str(uuid.uuid4())[:8]
        safe_filename = f"{doc_id}_{filename}"
        saved_path = self.storage_dir / safe_filename

        with open(saved_path, "wb") as f:
            f.write(file_bytes)

        # 2. Extract pages
        try:
            extracted_pages = pdf_service.extract_pages_from_bytes(file_bytes, filename)
        except Exception as e:
            if saved_path.exists():
                saved_path.unlink()
            raise PDFProcessingError(f"Failed to extract text from PDF: {str(e)}")

        # 3. Page-aware chunking
        chunks = chunking_service.chunk_document_pages(
            document_id=doc_id,
            document_name=filename,
            pages=extracted_pages
        )

        # 4. Index chunks into vector store
        vector_store.add_chunks(chunks)

        # 5. Persist to Database
        doc_record = DocumentModel(
            id=doc_id,
            filename=filename,
            title=filename.replace(".pdf", "").replace("_", " "),
            pages=len(extracted_pages),
            chunk_count=len(chunks),
            status=DocStatus.INDEXED.value,
            file_path=str(saved_path),
            file_size_bytes=len(file_bytes)
        )
        db.add(doc_record)

        for c in chunks:
            chunk_record = ChunkModel(
                id=c.chunk_id,
                document_id=doc_id,
                document_name=filename,
                page_number=c.page_number,
                section=c.section,
                chunk_index=c.chunk_index,
                text=c.text,
                char_count=len(c.text)
            )
            db.add(chunk_record)

        db.commit()
        db.refresh(doc_record)

        logger.info(f"Successfully ingested and indexed document '{filename}' (ID: {doc_id})")

        return DocumentSummary(
            id=doc_record.id,
            filename=doc_record.filename,
            title=doc_record.title,
            pages=doc_record.pages,
            chunk_count=doc_record.chunk_count,
            status=DocStatus.INDEXED,
            created_at=doc_record.created_at.strftime("%b %d, %H:%M"),
            file_size_bytes=doc_record.file_size_bytes
        )

    def list_documents(self, db: Session) -> List[DocumentSummary]:
        """Retrieves all indexed compliance documents."""
        docs = db.query(DocumentModel).all()
        return [
            DocumentSummary(
                id=d.id,
                filename=d.filename,
                title=d.title,
                pages=d.pages,
                chunk_count=d.chunk_count,
                status=DocStatus(d.status) if d.status in DocStatus._value2member_map_ else DocStatus.INDEXED,
                created_at=d.created_at.strftime("%b %d, %H:%M"),
                file_size_bytes=d.file_size_bytes
            )
            for d in docs
        ]

    def get_document_detail(self, document_id: str, db: Session) -> Optional[DocumentDetail]:
        """Retrieves single document detail with chunk list."""
        doc = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
        if not doc:
            return None

        chunks = db.query(ChunkModel).filter(ChunkModel.document_id == document_id).order_by(ChunkModel.chunk_index).all()
        chunk_metas = [
            ChunkMetadata(
                chunk_id=c.id,
                document_id=c.document_id,
                document_name=c.document_name,
                page_number=c.page_number,
                section=c.section,
                chunk_index=c.chunk_index,
                char_count=c.char_count
            )
            for c in chunks
        ]

        return DocumentDetail(
            id=doc.id,
            filename=doc.filename,
            title=doc.title,
            pages=doc.pages,
            chunk_count=doc.chunk_count,
            status=DocStatus(doc.status) if doc.status in DocStatus._value2member_map_ else DocStatus.INDEXED,
            created_at=doc.created_at.strftime("%b %d, %H:%M"),
            file_size_bytes=doc.file_size_bytes,
            chunks=chunk_metas
        )

    def delete_document(self, document_id: str, db: Session) -> bool:
        """Deletes a document, its database chunks, vector index, and stored file."""
        doc = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
        if not doc:
            return False

        # Remove file from disk
        file_path = Path(doc.file_path)
        if file_path.exists():
            file_path.unlink()

        # Remove vector chunks
        vector_store.delete_document(document_id)

        # Delete database records
        db.query(ChunkModel).filter(ChunkModel.document_id == document_id).delete()
        db.delete(doc)
        db.commit()

        logger.info(f"Deleted document ID: {document_id}")
        return True

    def sync_vector_store_from_db(self, db: Session):
        """Loads chunks from database into in-memory vector store if not already present."""
        if len(vector_store.chunks) > 0:
            return
        
        chunk_records = db.query(ChunkModel).all()
        if not chunk_records:
            return
        
        chunks = [
            DocumentChunk(
                chunk_id=c.id,
                document_id=c.document_id,
                document_name=c.document_name,
                page_number=c.page_number,
                section=c.section,
                chunk_index=c.chunk_index,
                text=c.text
            )
            for c in chunk_records
        ]
        vector_store.add_chunks(chunks)
        logger.info(f"Loaded {len(chunks)} chunks from database into vector store.")

    def initialize_sample_documents(self, db: Session):
        """Generates realistic compliance policy PDFs and ingests them on first run."""
        existing = db.query(DocumentModel).count()
        if existing > 0:
            self.sync_vector_store_from_db(db)
            return

        logger.info("Generating and indexing sample compliance policies...")

        samples = [
            {
                "filename": "Employee Travel Policy.pdf",
                "pages": [
                    (
                        "Section 1. Purpose & Scope\n\n"
                        "This policy establishes the rules and reimbursement limits for university personnel traveling on approved academic or official business. All travel must receive departmental pre-approval at least 14 days prior to departure."
                    ),
                    (
                        "Section 2. Domestic Travel & Lodging\n\n"
                        "Employees traveling domestically may book standard single room accommodations not exceeding ₹3,500 per night in Tier 1 cities, or ₹2,200 per night in Tier 2/3 cities. Itemized receipts are mandatory for all hotel claims."
                    ),
                    (
                        "Section 3. Daily Meal Allowance (Per Diem)\n\n"
                        "A daily subsistence per diem of ₹1,200 is permitted during active travel days. Alcoholic beverages and personal entertainment expenses are strictly non-reimbursable under all circumstances."
                    ),
                    (
                        "Section 4. Travel Reimbursement Limits\n\n"
                        "Employees may claim travel reimbursement up to ₹5,000 per trip for domestic travel without special provost authorization. Claims must be submitted within 30 days of the travel completion date. Any domestic trip exceeding ₹5,000 requires prior written approval from the Dean of Finance."
                    )
                ]
            },
            {
                "filename": "Expense Reimbursement Policy.pdf",
                "pages": [
                    (
                        "Section 1. General Principles\n\n"
                        "All business expenses incurred on behalf of the institution must be ordinary, reasonable, and necessary for institutional operations. Personal expenditures cannot be commingled with official claims."
                    ),
                    (
                        "Section 2. Documentation & Receipt Thresholds\n\n"
                        "All individual expense claims above ₹500 require an original tax invoice or valid digital receipt. Small miscellaneous expenses under ₹500 may be claimed with a self-declaration voucher, subject to a monthly cap of ₹2,000."
                    ),
                    (
                        "Section 3. Equipment and Hardware Purchases\n\n"
                        "All IT equipment, laptops, tablets, and software subscriptions require pre-approval from the IT Procurement Committee regardless of cost. Reimbursing unauthorized hardware purchases is prohibited."
                    )
                ]
            },
            {
                "filename": "Information Security Policy.pdf",
                "pages": [
                    (
                        "Section 1. Access Control & Passwords\n\n"
                        "All system accounts must use multi-factor authentication (MFA). Passwords must contain a minimum of 12 characters including uppercase, lowercase, numbers, and special symbols. Passwords expire every 90 days."
                    ),
                    (
                        "Section 2. Credential Sharing Prohibitions\n\n"
                        "Employees are strictly prohibited from sharing user accounts or system passwords with contractors, vendors, or colleagues. Each individual must possess an attributed, audited account."
                    ),
                    (
                        "Section 3. Incident Reporting Timeline\n\n"
                        "Any suspected data breach, malware infection, or unauthorized access attempt must be reported to the Security Operations Center (SOC) within 2 hours of discovery. Incident logs are retained for 365 days."
                    )
                ]
            },
            {
                "filename": "Data Protection Policy.pdf",
                "pages": [
                    (
                        "Section 1. Personal Identifiable Information (PII)\n\n"
                        "Student and faculty personal data must be encrypted in transit using TLS 1.3 and at rest using AES-256 encryption. Access to sensitive PII is restricted on a strict need-to-know basis."
                    ),
                    (
                        "Section 2. Data Retention & Erasure\n\n"
                        "Student academic transcripts are permanently retained. General administrative correspondence and visitor logs must be securely purged after 3 years. Research project data must be archived for 5 years post-publication."
                    )
                ]
            }
        ]

        for sample in samples:
            pdf_bytes = self._create_sample_pdf_bytes(sample["filename"], sample["pages"])
            self.ingest_pdf_file(pdf_bytes, sample["filename"], db)

        logger.info(f"Initialized {len(samples)} sample compliance policies.")

    def _create_sample_pdf_bytes(self, title: str, pages_text: List[str]) -> bytes:
        """Generates a valid PDF with ReportLab."""
        from io import BytesIO
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)

        for page_idx, page_text in enumerate(pages_text):
            # Header
            p.setFont("Helvetica-Bold", 14)
            p.drawString(50, 750, title.replace(".pdf", "").upper())
            p.setFont("Helvetica", 9)
            p.drawString(500, 750, f"Page {page_idx + 1}")
            p.setLineWidth(0.5)
            p.line(50, 740, 560, 740)

            # Body text
            p.setFont("Helvetica", 11)
            y = 700
            for para in page_text.split("\n\n"):
                lines = para.split("\n")
                for line in lines:
                    # Simple text wrapping
                    words = line.split(" ")
                    current_line = []
                    for word in words:
                        current_line.append(word)
                        if len(" ".join(current_line)) > 70:
                            p.drawString(50, y, " ".join(current_line[:-1]))
                            y -= 16
                            current_line = [word]
                    if current_line:
                        p.drawString(50, y, " ".join(current_line))
                        y -= 16
                y -= 10
                if y < 80:
                    break

            # Footer
            p.setFont("Helvetica-Oblique", 8)
            p.drawString(50, 40, "CompliSure Institutional Safety & Compliance Policy Document")
            p.showPage()

        p.save()
        return buffer.getvalue()


document_service = DocumentService()
