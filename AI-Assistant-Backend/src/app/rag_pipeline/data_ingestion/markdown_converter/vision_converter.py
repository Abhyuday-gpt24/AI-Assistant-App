"""Scanned/complex PDF → Markdown via a vision LLM (Gemini).

Each page is rendered to a PNG and sent to Gemini, which transcribes it to
Markdown. Embedded raster images are also extracted so the ingestion layer can
upload them to S3 and inject their URLs back into the Markdown (and thus into
the chunk metadata). The image bytes are returned here; uploading is the
service layer's job so this module stays free of any S3/AWS dependency.

Placeholder contract: for each extracted image the Markdown contains a marker
`__IMG__{name}__`; the ingestion service replaces it with the uploaded URL.
"""

import base64

# DPI to rasterize pages at before sending to the vision model. 150 balances
# legibility against payload size / token cost.
RENDER_DPI = 150

OCR_PROMPT = (
    "You are an OCR + document-structuring engine. Transcribe this page into "
    "clean GitHub-flavored Markdown. Preserve headings, lists, tables, and "
    "reading order. Do NOT add commentary, code fences, or text that isn't on "
    "the page. If the page is blank, return an empty string."
)


def _gemini():
    from langchain_google_genai import ChatGoogleGenerativeAI
    from config import settings

    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        api_key=settings.GEMINI_API_KEY,
        temperature=0,
    )


def convert_pdf_with_vision(data: bytes, filename: str) -> tuple[str, list[dict]]:
    """Return (markdown, images).

    images: list of {"name", "data" (bytes), "content_type"} extracted from the
    PDF. The markdown references each via an `__IMG__{name}__` placeholder.
    """
    # PyMuPDF imports as `pymupdf` on recent versions, `fitz` on older ones.
    try:
        import pymupdf
    except ModuleNotFoundError:
        import fitz as pymupdf
    from langchain_core.messages import HumanMessage

    model = _gemini()
    parts: list[str] = []
    images: list[dict] = []

    with pymupdf.open(stream=data, filetype="pdf") as doc:
        for page_index in range(doc.page_count):
            page = doc[page_index]

            # 1) Rasterize the page and ask the vision model to transcribe it.
            pix = page.get_pixmap(dpi=RENDER_DPI)
            page_b64 = base64.b64encode(pix.tobytes("png")).decode("ascii")
            message = HumanMessage(content=[
                {"type": "text", "text": OCR_PROMPT},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/png;base64,{page_b64}"}},
            ])
            page_md = (model.invoke([message]).content or "").strip()

            # 2) Pull out embedded raster images for S3 storage.
            page_markers: list[str] = []
            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                extracted = doc.extract_image(xref)
                ext = extracted.get("ext", "png")
                name = f"p{page_index + 1}_{img_index + 1}.{ext}"
                images.append({
                    "name": name,
                    "data": extracted["image"],
                    "content_type": f"image/{'jpeg' if ext == 'jpg' else ext}",
                })
                page_markers.append(f"![{name}](__IMG__{name}__)")

            section = page_md
            if page_markers:
                section = f"{section}\n\n" + "\n".join(page_markers)
            if section.strip():
                parts.append(section.strip())

    return "\n\n".join(parts).strip(), images
