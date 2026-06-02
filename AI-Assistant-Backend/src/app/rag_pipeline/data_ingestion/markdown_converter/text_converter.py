"""Text / HTML / CSV → Markdown via lightweight cleanup (no heavy deps)."""

import csv
import io


def convert_text_like(data: bytes, content_type: str, filename: str) -> str:
    name = filename.lower()
    text = data.decode("utf-8", errors="replace")

    if content_type == "text/csv" or name.endswith(".csv"):
        return _csv_to_markdown(text)
    if content_type == "text/html" or name.endswith((".html", ".htm")):
        return _html_to_markdown(text)
    # text/plain & text/markdown are already (close enough to) Markdown.
    return text.strip()


def _csv_to_markdown(text: str) -> str:
    """Render a CSV as a GitHub-flavored Markdown table."""
    rows = [r for r in csv.reader(io.StringIO(text)) if any(cell.strip() for cell in r)]
    if not rows:
        return ""
    from tabulate import tabulate  # already a project dependency

    header, *body = rows
    return tabulate(body, headers=header, tablefmt="github")


def _html_to_markdown(text: str) -> str:
    """HTML → Markdown. markitdown gives proper structure (headings/lists/tables)."""
    from markitdown import MarkItDown

    md = MarkItDown()
    result = md.convert_stream(
        io.BytesIO(text.encode("utf-8")), file_extension=".html"
    )
    return (result.text_content or "").strip()
