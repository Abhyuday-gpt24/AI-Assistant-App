"""DOCX / PPTX / EPUB / XLSX → Markdown via Microsoft markitdown.

markitdown can also read PDFs, but we deliberately route PDFs to pdf_converter
(pymupdf4llm) instead — it produces far better Markdown (headings, tables) and
lets us detect scanned files for the vision path. Office/eBook formats are
structured XML/zip, so markitdown extracts their text directly (no OCR needed).
"""

import os
import shutil
import subprocess
import tempfile


def convert_office(data: bytes, filename: str) -> str:
    from markitdown import MarkItDown

    suffix = os.path.splitext(filename)[1] or ""
    # markitdown picks its converter from the file extension, so we round-trip
    # through a temp file with the original suffix (most robust across versions).
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        result = MarkItDown().convert(tmp_path)
        return (result.text_content or "").strip()
    finally:
        os.unlink(tmp_path)


def office_to_pdf(data: bytes, filename: str) -> bytes:
    """Render a DOCX/PPTX to PDF via headless LibreOffice.

    Used only for image-first Office files that need the vision path (the
    rendered PDF is then fed to `vision_converter`). Requires a `soffice` binary
    on PATH (or `SOFFICE_PATH` env override) — a system dependency on whatever
    host runs ingestion. Raises if LibreOffice is unavailable or conversion
    fails, so callers can fall back to the markitdown text.
    """
    soffice = (
        os.environ.get("SOFFICE_PATH")
        or shutil.which("soffice")
        or shutil.which("soffice.exe")
    )
    if not soffice:
        raise RuntimeError("LibreOffice (soffice) not found — cannot render Office doc")

    suffix = os.path.splitext(filename)[1] or ".docx"
    workdir = tempfile.mkdtemp()
    try:
        in_path = os.path.join(workdir, f"in{suffix}")
        with open(in_path, "wb") as f:
            f.write(data)
        subprocess.run(
            [soffice, "--headless", "--convert-to", "pdf", "--outdir", workdir, in_path],
            check=True,
            capture_output=True,
            timeout=120,
        )
        pdf_path = os.path.splitext(in_path)[0] + ".pdf"
        with open(pdf_path, "rb") as f:
            return f.read()
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
