"""File → Markdown conversion for RAG ingestion.

One module per conversion strategy; `convert.py` is the dispatcher:

    Text/HTML/CSV          → text_converter   (lightweight cleanup)
    DOCX/PPTX/EPUB/XLSX     → office_converter  (markitdown)
    Clean/digital PDF       → pdf_converter     (pymupdf4llm)
    Scanned/complex PDF     → vision_converter  (Gemini vision LLM + image extraction)
    Standalone images       → NOT handled here  (sent to the chat model as base64)

Heavy third-party libs (pymupdf4llm, markitdown, langchain-google-genai) are
imported lazily inside each function so importing this package is cheap and the
always-on API doesn't pull them in. They only need to be installed wherever the
ingestion endpoint actually runs.
"""

from src.app.rag_pipeline.data_ingestion.markdown_converter.convert import (
    convert_to_markdown,
)

__all__ = ["convert_to_markdown"]
