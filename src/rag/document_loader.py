import io
from pathlib import Path

import docx2txt
import pdfplumber
from langchain_core.documents import Document
from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def load_document(filename: str, data: bytes) -> list[Document]:
    """Turn an uploaded file (name + raw bytes) into LangChain Documents.

    For PDFs, this returns both regular text passages AND, separately, any
    detected tables as clean Markdown (tagged chunk_type="table" so the
    splitter never breaks them apart). The same table content may also
    appear, less legibly, inside the flat page text — see note in
    _extract_pdf_tables.
    """
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        docs = _load_pdf(filename, data)
    elif ext == ".docx":
        docs = _load_docx(filename, data)
    elif ext == ".txt":
        docs = _load_txt(filename, data)
    else:
        raise ValueError(
            f"Unsupported file type '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    if not docs:
        raise ValueError(f"No extractable text found in '{filename}' (scanned or image-only file?)")
    return docs


def _load_pdf(filename: str, data: bytes) -> list[Document]:
    docs = _extract_pdf_text(filename, data)
    docs += _extract_pdf_tables(filename, data)
    return docs


def _extract_pdf_text(filename: str, data: bytes) -> list[Document]:
    reader = PdfReader(io.BytesIO(data))
    docs = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            docs.append(
                Document(
                    page_content=text,
                    metadata={"filename": filename, "page": page_number, "chunk_type": "text"},
                )
            )
    return docs


def _extract_pdf_tables(filename: str, data: bytes) -> list[Document]:
    """Detect tables with pdfplumber and emit each as one clean Markdown chunk,
    prefixed with a snippet of the text just above it on the page (often the
    table's title or column-year context, which pdfplumber's table detector
    sometimes misses as a proper header row)."""
    docs = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            found_tables = page.find_tables()
            for found in found_tables:
                markdown = _table_to_markdown(found.extract())
                if not markdown:
                    continue

                context = _text_above_table(page, found.bbox)
                content = f"{context}\n\n{markdown}" if context else markdown

                docs.append(
                    Document(
                        page_content=content,
                        metadata={"filename": filename, "page": page_number, "chunk_type": "table"},
                    )
                )
    return docs


def _text_above_table(page, table_bbox, lookback_px: float = 60) -> str:
    """Grab a short strip of text just above a table's bounding box on the page,
    as a best-effort source of the table's title/header context."""
    x0, top, x1, bottom = table_bbox
    region = page.within_bbox((0, max(0, top - lookback_px), page.width, top))
    text = (region.extract_text() or "").strip()
    return text

def _table_to_markdown(table: list[list[str | None]]) -> str:
    rows = [[(cell or "").strip() for cell in row] for row in table if any(cell for cell in row)]
    if not rows:
        return ""

    header, *body = rows
    width = len(header)
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * width) + " |",
    ]
    for row in body:
        row = (row + [""] * width)[:width]  # pad/truncate to header width
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _load_docx(filename: str, data: bytes) -> list[Document]:
    text = (docx2txt.process(io.BytesIO(data)) or "").strip()
    if not text:
        return []
    return [Document(page_content=text, metadata={"filename": filename, "page": None, "chunk_type": "text"})]


def _load_txt(filename: str, data: bytes) -> list[Document]:
    text = data.decode("utf-8-sig", errors="replace").strip()
    if not text:
        return []
    return [Document(page_content=text, metadata={"filename": filename, "page": None, "chunk_type": "text"})]