"""Dispatch a file to the right converter based on its MIME type."""

import logging

logger = logging.getLogger(__name__)

OFFICE_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # docx
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # pptx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx
    "application/epub+zip",  # epub
}
TEXT_TYPES = {"text/plain", "text/html", "text/csv", "text/markdown"}


def convert_to_markdown(data: bytes, filename: str, content_type: str) -> dict:
    """Convert raw file bytes to Markdown.

    Returns {"markdown": str, "images": list[dict], "method": str, "profile": dict|None}.
    `images` (extracted from complex PDFs) is empty for every path except the
    vision one; each entry is {"name", "data", "content_type"}. `profile` is the
    PDF classifier's decision (None for non-PDFs).
    """
    from src.app.rag_pipeline.data_ingestion.markdown_converter import (
        text_converter,
        office_converter,
        pdf_converter,
        vision_converter,
        classify,
    )

    if content_type in TEXT_TYPES:
        md = text_converter.convert_text_like(data, content_type, filename)
        return {"markdown": md, "images": [], "method": "text", "profile": None}

    if content_type in OFFICE_TYPES:
        md = office_converter.convert_office(data, filename)
        # Image-first DOCX/PPTX (sparse text + many images) → render to PDF via
        # LibreOffice and run the vision path. Falls back to the markitdown text
        # if profiling says "simple" or LibreOffice/vision is unavailable.
        profile = classify.profile_office(data, content_type, md)
        if profile["route"] == "complex":
            try:
                pdf_bytes = office_converter.office_to_pdf(data, filename)
                vmd, images = vision_converter.convert_pdf_with_vision(pdf_bytes, filename)
                if vmd.strip():
                    return {"markdown": vmd, "images": images,
                            "method": "vision-office", "profile": profile}
            except Exception:
                logger.warning(
                    "Office vision path failed for %s; falling back to markitdown",
                    filename, exc_info=True,
                )
        return {"markdown": md, "images": [], "method": "markitdown", "profile": profile}

    if content_type == "application/pdf":
        # Profile the PDF's content to choose the conversion strategy.
        profile = classify.profile_pdf(data)
        if profile["route"] == "simple":
            md = pdf_converter.extract_markdown(data)
            if md:  # extraction produced real text → done
                return {"markdown": md, "images": [], "method": "pymupdf4llm", "profile": profile}
            # "simple" but extraction came back empty → fall through to vision.
        # complex (or simple-but-empty) → vision LLM (+ extract images for S3).
        md, images = vision_converter.convert_pdf_with_vision(data, filename)
        return {"markdown": md, "images": images, "method": "vision", "profile": profile}

    raise ValueError(f"No converter for content type: {content_type}")
