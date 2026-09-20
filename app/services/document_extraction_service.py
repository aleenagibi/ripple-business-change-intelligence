from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader


class DocumentExtractionService:
    """Extract textual content from supported document formats."""

    SUPPORTED_EXTENSIONS = {
        ".pdf",
        ".docx",
        ".txt",
    }

    def extract(self, file_path: Path) -> str:
        extension = file_path.suffix.lower()

        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported document type: {extension}"
            )

        if extension == ".pdf":
            return self._extract_pdf(file_path)

        if extension == ".docx":
            return self._extract_docx(file_path)

        return self._extract_txt(file_path)

    @staticmethod
    def _extract_pdf(file_path: Path) -> str:
        reader = PdfReader(str(file_path))

        pages: list[str] = []

        for page in reader.pages:
            text = page.extract_text()

            if text:
                pages.append(text)

        return "\n\n".join(pages).strip()

    @staticmethod
    def _extract_docx(file_path: Path) -> str:
        document = DocxDocument(str(file_path))

        paragraphs = [
            paragraph.text.strip()
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        ]

        return "\n\n".join(paragraphs).strip()

    @staticmethod
    def _extract_txt(file_path: Path) -> str:
        return file_path.read_text(
            encoding="utf-8",
            errors="replace",
        ).strip()