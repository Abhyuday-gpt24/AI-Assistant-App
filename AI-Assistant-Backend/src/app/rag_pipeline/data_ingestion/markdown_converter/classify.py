"""Document profiler — decides HOW a PDF should be converted.

Sits in front of the PDF converters and inspects the actual content (not just
the MIME type) to route between:

  • "simple"  → a well-structured, text-first PDF: fast text extraction
               (pymupdf4llm) handles it, tables included.
  • "complex" → scanned, image-heavy, multi-column, or table+image-clustered
               PDFs where flat text extraction loses information → vision LLM.

Signals (all via PyMuPDF / fitz, no extra deps):
  - avg characters per page      → near-zero ⇒ scanned/image-only
  - avg embedded images per page → high ⇒ image-heavy
  - table count                  → tables combined with images ⇒ clustered
  - column count per page        → multi-column ⇒ cluttered layout

Returns a profile dict so callers can log WHY a route was chosen.
"""

# Tunable thresholds.
MIN_CHARS_PER_PAGE = 100   # below this ⇒ effectively no extractable text (scanned)
IMAGES_PER_PAGE_HEAVY = 1.0  # >= this avg ⇒ image-heavy
MIXED_IMAGES_PER_PAGE = 0.3  # images this dense alongside tables ⇒ clustered
COLUMN_GAP_RATIO = 0.20      # horizontal gap (fraction of page width) splitting columns

# Office (docx/pptx) thresholds — these formats are structured XML, so they only
# need the vision path when they're image-first with little extractable text.
OFFICE_MIN_CHARS_PER_SLIDE = 60   # pptx: sparse text per slide ⇒ image-first deck
OFFICE_DOCX_MIN_CHARS = 200       # docx: very little text overall ...
OFFICE_DOCX_MIN_IMAGES = 3        # ... combined with several images ⇒ image-first doc

_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
_OFFICE_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp", ".emf", ".wmf")


def profile_pdf(data: bytes) -> dict:
    """Profile a PDF and return {route, reasons, stats}.

    route ∈ {"simple", "complex"}. Defensive: any failure profiling a page is
    swallowed (that page just contributes nothing) so a malformed PDF still
    yields a decision rather than raising.
    """
    # PyMuPDF imports as `pymupdf` on recent versions, `fitz` on older ones.
    try:
        import pymupdf
    except ModuleNotFoundError:
        import fitz as pymupdf

    pages = 0
    total_chars = 0
    total_images = 0
    total_tables = 0
    max_columns = 1

    with pymupdf.open(stream=data, filetype="pdf") as doc:
        pages = max(doc.page_count, 1)
        for page in doc:
            try:
                total_chars += len(page.get_text("text") or "")
                total_images += len(page.get_images(full=True))
                total_tables += _table_count(page)
                max_columns = max(max_columns, _column_count(page))
            except Exception:
                continue

    avg_chars = total_chars / pages
    avg_images = total_images / pages

    reasons = []
    if avg_chars < MIN_CHARS_PER_PAGE:
        reasons.append(f"sparse text ({avg_chars:.0f} chars/page)")
    if avg_images >= IMAGES_PER_PAGE_HEAVY:
        reasons.append(f"image-heavy ({avg_images:.1f} imgs/page)")
    if total_tables >= 1 and avg_images >= MIXED_IMAGES_PER_PAGE:
        reasons.append(f"clustered tables+images ({total_tables} tables)")
    if max_columns >= 2:
        reasons.append(f"multi-column layout ({max_columns} cols)")

    return {
        "route": "complex" if reasons else "simple",
        "reasons": reasons,
        "stats": {
            "pages": pages,
            "avg_chars_per_page": round(avg_chars, 1),
            "avg_images_per_page": round(avg_images, 2),
            "tables": total_tables,
            "max_columns": max_columns,
        },
    }


def profile_office(data: bytes, content_type: str, text: str) -> dict:
    """Decide whether a DOCX/PPTX needs the vision path.

    Office files are zip archives; we count embedded media images (and pptx
    slides) and compare against the text markitdown already extracted. Only
    image-first files (sparse text + images) route to "complex". XLSX/EPUB
    never go to vision — they stay on the markitdown path.
    """
    import io
    import zipfile

    images = 0
    slides = 0
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for name in z.namelist():
                lname = name.lower()
                if "media/" in lname and lname.endswith(_OFFICE_IMAGE_EXTS):
                    images += 1
                if lname.startswith("ppt/slides/slide") and lname.endswith(".xml"):
                    slides += 1
    except Exception:
        return {"route": "simple", "reasons": [], "stats": {"images": 0, "slides": 0}}

    text_len = len((text or "").strip())
    reasons = []

    if content_type == _PPTX:
        units = max(slides, 1)
        chars_per_slide = text_len / units
        if images >= 1 and chars_per_slide < OFFICE_MIN_CHARS_PER_SLIDE:
            reasons.append(
                f"image-first deck ({images} imgs, {chars_per_slide:.0f} chars/slide)"
            )
    elif content_type == _DOCX:
        if text_len < OFFICE_DOCX_MIN_CHARS and images >= OFFICE_DOCX_MIN_IMAGES:
            reasons.append(f"image-first doc ({images} imgs, {text_len} chars text)")

    return {
        "route": "complex" if reasons else "simple",
        "reasons": reasons,
        "stats": {"images": images, "slides": slides, "text_len": text_len},
    }


def _table_count(page) -> int:
    """Number of tables PyMuPDF detects on the page (0 if unsupported)."""
    try:
        return len(page.find_tables().tables)
    except Exception:
        return 0


def _column_count(page) -> int:
    """Estimate text columns by clustering text-block x-midpoints.

    Returns 2 when blocks split into a left/right group separated by a wide
    horizontal gap (each group holding >=2 blocks); otherwise 1.
    """
    blocks = [b for b in page.get_text("blocks") if len(b) >= 5 and str(b[4]).strip()]
    if len(blocks) < 4:
        return 1

    mids = sorted((b[0] + b[2]) / 2 for b in blocks)
    page_width = page.rect.width or 1
    # widest gap between consecutive midpoints
    gap, idx = max((mids[i + 1] - mids[i], i) for i in range(len(mids) - 1))
    if gap > COLUMN_GAP_RATIO * page_width:
        left, right = idx + 1, len(mids) - (idx + 1)
        if left >= 2 and right >= 2:
            return 2
    return 1
