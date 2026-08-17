"""
Document reader service.

Downloads files sent by users via Telegram and extracts plain text
content from them so the LLM can read and act on the contents
(e.g., turn a todolist.txt into calendar events or tasks).

Supported formats (by file extension / mime type):
- Plain text: .txt, .md, .csv, .json, .log, .xml, .yaml, .yml, .html
- PDF: .pdf (requires pypdf, optional)
- Word: .docx (parsed via built-in ZIP/XML reader, no extra deps)
"""

import html
import io
import re
import zipfile
from typing import Optional

from app.core.logging import logger


# Maximum characters of extracted text kept for the LLM context
MAX_TEXT_LENGTH = 15_000

# Extensions that can be read directly as UTF-8 text
TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".csv", ".tsv", ".json", ".log",
    ".xml", ".yaml", ".yml", ".ini", ".cfg", ".html", ".htm", ".py",
    ".js", ".ts", ".sql", ".bat", ".sh", ".rtf",
}


class DocumentReader:
    """
    Extracts text content from uploaded documents.

    Uses no heavy dependencies: plain text files are decoded directly,
    .docx files are unzipped and their XML text nodes extracted, and
    PDFs are parsed with pypdf when it is installed.
    """

    @staticmethod
    def _extension(file_name: Optional[str], mime_type: Optional[str]) -> str:
        """Determine the file extension, falling back to mime type hints."""
        if file_name and "." in file_name:
            return "." + file_name.rsplit(".", 1)[-1].lower()
        # Fall back to mime type for extension-less Telegram files
        mime_map = {
            "text/plain": ".txt",
            "text/csv": ".csv",
            "application/json": ".json",
            "application/pdf": ".pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        }
        if mime_type:
            return mime_map.get(mime_type, "")
        return ""

    @staticmethod
    def _decode_text(data: bytes) -> str:
        """Decode bytes to text, trying UTF-8 first then falling back."""
        for encoding in ("utf-8", "utf-16", "latin-1", "shift_jis"):
            try:
                return data.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                continue
        # Last resort: ignore undecodable bytes
        return data.decode("utf-8", errors="replace")

    @staticmethod
    def _extract_docx(data: bytes) -> str:
        """Extract text from a .docx file (a ZIP containing word/document.xml)."""
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                xml = zf.read("word/document.xml").decode("utf-8", errors="replace")
        except (zipfile.BadZipFile, KeyError) as e:
            raise ValueError(f"Could not read .docx file: {e}") from e

        # Each <w:p> is a paragraph - join with newlines; strip all other tags
        xml = xml.replace("</w:p>", "\n")
        text = re.sub(r"<[^>]+>", "", xml)
        # Unescape XML/HTML entities (amp, lt, gt, quot, apos, ...)
        return html.unescape(text)

    @staticmethod
    def _extract_pdf(data: bytes) -> str:
        """Extract text from a PDF using pypdf (optional dependency)."""
        try:
            from pypdf import PdfReader
        except ImportError as e:
            raise ValueError(
                "PDF reading requires the 'pypdf' package. Install it with: pip install pypdf"
            ) from e

        reader = PdfReader(io.BytesIO(data))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "\n".join(pages)

    async def extract_text(
        self,
        data: bytes,
        file_name: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> str:
        """
        Extract plain text from raw file bytes.

        Args:
            data: Raw file content downloaded from Telegram.
            file_name: Original file name (used to detect format).
            mime_type: Telegram mime type (fallback for format detection).

        Returns:
            Extracted text, truncated to MAX_TEXT_LENGTH characters.

        Raises:
            ValueError: If the format is unsupported or parsing fails.
        """
        ext = self._extension(file_name, mime_type)
        logger.debug(
            "Extracting text from file %r (ext=%s, %d bytes)", file_name, ext, len(data)
        )

        if ext in TEXT_EXTENSIONS or ext.startswith(".text"):
            text = self._decode_text(data)
        elif ext == ".docx":
            text = self._extract_docx(data)
        elif ext == ".pdf":
            text = self._extract_pdf(data)
        else:
            ext_label = ext if ext else "unknown"
            raise ValueError(
                f"Unsupported file type '{ext_label}'. "
                "Supported: txt, md, csv, json, pdf, docx and other text files."
            )

        text = text.strip()
        if not text:
            raise ValueError("The file appears to be empty or contains no readable text.")

        if len(text) > MAX_TEXT_LENGTH:
            text = text[:MAX_TEXT_LENGTH] + "\n\n[... file truncated ...]"
            logger.info("File '%s' truncated to %d chars", file_name, MAX_TEXT_LENGTH)

        return text


# Singleton instance
document_reader = DocumentReader()