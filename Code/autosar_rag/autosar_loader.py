"""PDF loader for AUTOSAR specifications with page-level provenance.

Text extraction is attempted for every page. Pages with no usable text are passed
through optional PyMuPDF + pytesseract OCR when those packages and the Tesseract
binary are installed. OCR failures are recorded in metadata rather than hidden.
"""

from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path
from typing import Iterator, Optional, Union, BinaryIO, Any, Iterable

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document
from pypdf import PdfReader

SourceInput = Union[str, Path, BinaryIO, bytes, bytearray, Any]

_HEADING_RE = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*\s+.{3,120}|[A-Z][A-Z0-9 /_()\-]{5,100})\s*$"
)


def remove_empty_documents(documents: Iterable[Document]) -> list[Document]:
    """Filter out empty or whitespace-only documents to prevent Qdrant 422 errors.

    Qdrant rejects points where dense vectors are empty. Filtering empty text
    before indexing protects vector search pipelines.
    """
    valid_documents: list[Document] = []
    skipped = 0
    for doc in documents:
        text = getattr(doc, "page_content", "")
        if not isinstance(text, str) or not text.strip():
            skipped += 1
            continue
        valid_documents.append(doc)
    return valid_documents


class AutosarLoader(BaseLoader):
    """Extract individual PDF pages without dropping page-edge content.

    ``uploaded_file`` may be a Streamlit UploadedFile, an open binary stream, a
    filesystem path, or bytes. The original stream position is restored where
    possible so callers can reuse the upload object after loading.
    """

    def __init__(
        self,
        uploaded_file: SourceInput,
        *,
        document_version: Optional[str] = None,
        project_id: Optional[str] = None,
        enable_ocr: bool = True,
    ) -> None:
        self.uploaded_file = uploaded_file
        self.document_version = document_version or "unspecified"
        self.project_id = project_id or "local"
        self.enable_ocr = enable_ocr

    def _read_bytes(self) -> tuple[bytes, str]:
        source = self.uploaded_file
        source_name = getattr(source, "name", None) or getattr(source, "filename", None)

        if isinstance(source, (str, Path)):
            path = Path(source)
            return path.read_bytes(), path.name
        if isinstance(source, (bytes, bytearray)):
            return bytes(source), str(source_name or "uploaded.pdf")

        # Streamlit UploadedFile has getvalue() and is seekable. Prefer getvalue
        # because .read() may otherwise depend on the current cursor position.
        getvalue = getattr(source, "getvalue", None)
        if callable(getvalue):
            data = getvalue()
            return bytes(data), str(source_name or "uploaded.pdf")

        old_position = None
        try:
            old_position = source.tell()
        except Exception:
            pass
        try:
            if hasattr(source, "seek"):
                source.seek(0)
            data = source.read()
        finally:
            if old_position is not None and hasattr(source, "seek"):
                try:
                    source.seek(old_position)
                except Exception:
                    pass
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("PDF input must be a binary stream or bytes.")
        return bytes(data), str(source_name or "uploaded.pdf")

    @staticmethod
    def _headings(text: str) -> list[str]:
        headings = []
        for line in text.splitlines():
            candidate = " ".join(line.strip().split())
            if candidate and len(candidate) <= 120 and _HEADING_RE.match(candidate):
                headings.append(candidate)
        # A heading may appear several times in extracted text; keep order but
        # discard duplicate occurrences on the same page.
        return list(dict.fromkeys(headings))

    def _ocr_page(self, pdf_bytes: bytes, page_index: int) -> tuple[str, Optional[str]]:
        """OCR one page if optional runtime dependencies are available."""
        try:
            import fitz  # PyMuPDF, optional
            import pytesseract  # optional Python wrapper for Tesseract
            from PIL import Image

            with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
                page = pdf.load_page(page_index)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                return pytesseract.image_to_string(image), None
        except ImportError as exc:
            return "", (
                "OCR required but unavailable. Install PyMuPDF, Pillow and "
                f"pytesseract, and install the Tesseract binary ({exc})."
            )
        except Exception as exc:  # OCR/parser failures must be visible in report
            return "", f"OCR failed: {type(exc).__name__}: {exc}"

    def lazy_load(self) -> Iterator[Document]:
        pdf_bytes, source_name = self._read_bytes()
        if not pdf_bytes.startswith(b"%PDF-"):
            raise ValueError("Uploaded file does not have a valid PDF signature.")

        source_hash = hashlib.sha256(pdf_bytes).hexdigest()
        document_id = source_hash[:20]
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes), strict=False)
        except Exception as exc:
            raise ValueError(f"Could not parse PDF {source_name!r}: {exc}") from exc

        if reader.is_encrypted:
            try:
                result = reader.decrypt("")
                if not result:
                    raise ValueError("PDF is encrypted and requires a password.")
            except Exception as exc:
                raise ValueError("PDF is encrypted and cannot be opened.") from exc

        table_pdf = None
        table_extraction_available = True
        table_parser_warning: Optional[str] = None
        try:
            import pdfplumber  # optional but installed by the project requirements
            table_pdf = pdfplumber.open(io.BytesIO(pdf_bytes))
        except ImportError as exc:
            table_extraction_available = False
            table_parser_warning = (
                "Table parser unavailable; install pdfplumber to preserve table rows and columns. "
                f"({exc})"
            )
        except Exception as exc:
            # A table parser failure must not prevent basic PDF text extraction,
            # but it must remain visible instead of silently degrading ingestion.
            table_pdf = None
            table_extraction_available = False
            table_parser_warning = f"Table parser failed: {type(exc).__name__}: {exc}"

        try:
            for page_index, page in enumerate(reader.pages):
                page_number = page_index + 1
                extraction_warnings: list[str] = []
                if table_parser_warning:
                    extraction_warnings.append(table_parser_warning)
                try:
                    text = page.extract_text() or ""
                except Exception as exc:
                    text = ""
                    extraction_warnings.append(
                        f"PDF text extraction failed: {type(exc).__name__}: {exc}"
                    )

                extracted_tables = []
                if table_pdf is not None and page_index < len(table_pdf.pages):
                    try:
                        extracted_tables = table_pdf.pages[page_index].extract_tables() or []
                    except Exception as exc:
                        extraction_warnings.append(
                            f"Table extraction failed: {type(exc).__name__}: {exc}"
                        )

                table_blocks = []
                for table_index, table in enumerate(extracted_tables, start=1):
                    rows = []
                    for row in table or []:
                        cells = [" ".join(str(cell or "").split()) for cell in (row or [])]
                        if any(cells):
                            rows.append(cells)
                    if not rows:
                        continue
                    header_cells = rows[0]
                    headers = [cell or f"Column {index + 1}" for index, cell in enumerate(header_cells)]
                    rendered_rows = [f"[TABLE {table_index} HEADER] " + " | ".join(headers)]
                    for row_index, row_cells in enumerate(rows[1:], start=2):
                        pairs = []
                        for column_index, value in enumerate(row_cells):
                            if not value:
                                continue
                            label = headers[column_index] if column_index < len(headers) else f"Column {column_index + 1}"
                            pairs.append(f"{label} = {value}")
                        # Repeat the table headers semantically in every row so
                        # chunk boundaries cannot orphan values from their columns.
                        rendered_rows.append(f"[TABLE {table_index} ROW {row_index}] " + " | ".join(pairs))
                    table_blocks.append("\n".join(rendered_rows))
                table_text = "\n\n".join(table_blocks)
                # Append table extraction as a separate block. This keeps cell order
                # explicit even if the base PDF text extractor flattens the table.
                if table_text:
                    text = (text.rstrip() + "\n\n" + table_text).strip()

                extraction_method = "pdf_text"
                # An almost-empty page often represents a scanned page with only a
                # page number or no text at all. OCR it rather than silently indexing
                # a blank record. This is a heuristic, recorded in the metadata.
                if self.enable_ocr and len(text.strip()) < 20:
                    ocr_text, ocr_warning = self._ocr_page(pdf_bytes, page_index)
                    if ocr_text.strip():
                        text = ocr_text
                        extraction_method = "ocr"
                    elif ocr_warning:
                        extraction_warnings.append(ocr_warning)

                headings = self._headings(text)
                yield Document(
                    page_content=text.strip(),
                    metadata={
                        "source": source_name,
                        "document_id": document_id,
                        "document_version": self.document_version,
                        "source_sha256": source_hash,
                        "project_id": self.project_id,
                        "page_number": page_number,
                        "page_start": page_number,
                        "page_end": page_number,
                        "section_headings": headings,
                        "section_path": headings[-1:] if headings else [],
                        "content_type": "page",
                        "extraction_method": extraction_method,
                        "extraction_warnings": extraction_warnings,
                        "empty_after_extraction": not bool(text.strip()),
                    },
                )
        finally:
            if table_pdf is not None:
                table_pdf.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract page-level text and metadata from an AUTOSAR PDF.")
    parser.add_argument("pdf", help="Path to an input PDF")
    args = parser.parse_args()
    for document in AutosarLoader(args.pdf).lazy_load():
        print(f"Page {document.metadata['page_number']}: {len(document.page_content)} characters")
        for warning in document.metadata.get("extraction_warnings", []):
            print(f"  WARNING: {warning}")
