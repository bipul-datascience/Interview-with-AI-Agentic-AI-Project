"""Safe, local text extraction for the MVP."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path


def extract_resume_text(filename: str, content: bytes) -> str:
    """Extract plain text from a PDF, DOCX, or TXT upload."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".txt":
        return content.decode("utf-8", errors="replace")
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix == ".docx":
        from docx import Document

        document = Document(BytesIO(content))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    raise ValueError("Please upload a PDF, DOCX, or TXT resume.")
