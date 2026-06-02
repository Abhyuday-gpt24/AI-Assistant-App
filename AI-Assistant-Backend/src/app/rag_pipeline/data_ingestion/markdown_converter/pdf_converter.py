"""Clean/digital PDF → Markdown via pymupdf4llm.

This module only does fast text extraction (tables/headings included). The
decision of whether a PDF is simple enough for this path — vs. needing the
vision converter — lives in `classify.profile_pdf`.
"""

import os
import tempfile


def extract_markdown(data: bytes) -> str:
    """Extract a PDF to Markdown with pymupdf4llm. May be empty for scanned PDFs."""
    import pymupdf4llm

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        return (pymupdf4llm.to_markdown(tmp_path) or "").strip()
    finally:
        os.unlink(tmp_path)
