import re
import uuid
from pathlib import Path
from uuid import UUID

from app.core.config import settings
from app.models.document import Document
from app.repositories.document_repository import DocumentRepository
from app.repositories.organization_repository import OrganizationRepository
from app.services.chunk_service import ChunkService
from app.services.document_extraction_service import (
    DocumentExtractionService,
)
from fastapi import UploadFile
from sqlalchemy.orm import Session


class DocumentService:
    """Business logic for document ingestion."""

    MAX_FILE_SIZE = 25 * 1024 * 1024

    MIME_TYPES = {
        ".pdf": "application/pdf",
        ".docx": (
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        ".txt": "text/plain",
    }

    def __init__(self, db: Session) -> None:
        self.db = db

        self.document_repository = DocumentRepository(db)
        self.organization_repository = OrganizationRepository(db)

        self.extraction_service = DocumentExtractionService()
        self.chunk_service = ChunkService(db)

    async def upload(
        self,
        organization_id: UUID,
        upload: UploadFile,
    ) -> Document:

        organization = self.organization_repository.get_by_id(
            organization_id
        )

        if organization is None:
            raise ValueError("Organization not found.")

        original_filename = upload.filename or ""
        extension = Path(original_filename).suffix.lower()

        if extension not in self.MIME_TYPES:
            raise ValueError(
                "Unsupported file type. "
                "Supported types are PDF, DOCX, and TXT."
            )

        expected_mime_type = self.MIME_TYPES[extension]

        if upload.content_type not in {
            expected_mime_type,
            "application/octet-stream",
        }:
            raise ValueError(
                f"Invalid MIME type for {extension} file."
            )

        safe_filename = self._sanitize_filename(
            original_filename
        )

        document_id = uuid.uuid4()

        organization_directory = (
            Path(settings.STORAGE_ROOT)
            / str(organization_id)
        )

        organization_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        stored_filename = f"{document_id}{extension}"

        storage_path = (
            organization_directory / stored_filename
        )

        bytes_written = 0

        try:
            

            with storage_path.open("wb") as output:
                while chunk := await upload.read(1024 * 1024):
                    bytes_written += len(chunk)

                    if bytes_written > self.MAX_FILE_SIZE:
                        raise ValueError(
                            "File exceeds the maximum allowed size of 25 MB."
                        )

                    output.write(chunk)

            extracted_text = self.extraction_service.extract(
                storage_path
            )

            if not extracted_text:
                raise ValueError(
                    "No text could be extracted from the document."
                )

            document = Document(
                id=document_id,
                organization_id=organization_id,
                filename=safe_filename,
                document_type=extension.lstrip("."),
                mime_type=expected_mime_type,
                storage_path=str(storage_path),
                extracted_text=extracted_text,
                processing_status="processing",
                document_metadata={
                    "size_bytes": bytes_written,
                },
            )

            self.document_repository.add(document)

            self.db.flush()

            self.chunk_service.process_document(
                document
            )

            document.processing_status = "completed"

            self.db.commit()
            self.db.refresh(document)

            return document

        except Exception:
            self.db.rollback()

            if storage_path.exists():
                storage_path.unlink()

            raise

        finally:
            await upload.close()

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        filename = Path(filename).name

        filename = re.sub(
            r"[^A-Za-z0-9._ -]",
            "_",
            filename,
        )

        filename = filename.strip(" .")

        if not filename:
            return "document"

        return filename