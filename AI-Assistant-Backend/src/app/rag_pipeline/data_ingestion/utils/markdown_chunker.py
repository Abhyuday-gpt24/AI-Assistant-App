"""Chunk an in-memory Markdown string (for the live, per-user ingestion path).

Mirrors the offline `chunker.chunk_file` splitting strategy (header-aware then
recursive char split) but takes a string instead of a file path, and lifts any
image URLs found in a chunk into its metadata so retrieval can surface them.
"""

import hashlib
import re

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

# Markdown image syntax: ![alt](url)
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def chunk_markdown(text: str, source: str, storage_path: str = "") -> list[dict]:
    """Split Markdown into chunk dicts.

    Each dict: {chunk_id, text, source, heading_trail, image_urls, storage_path}.
    """
    if not text or not text.strip():
        return []

    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")],
        strip_headers=False,
    )
    md_sections = md_splitter.split_text(text)

    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=200,
        separators=["\n```\n", "\n\n", "\n", " "],
    )
    final_chunks = char_splitter.split_documents(md_sections)

    results = []
    for i, chunk in enumerate(final_chunks):
        body = chunk.page_content.strip()
        if not body:
            continue

        headers = chunk.metadata
        heading_trail = " > ".join(
            headers[k] for k in ("h1", "h2", "h3") if k in headers
        )
        chunk_text = f"{heading_trail}\n\n{body}" if heading_trail else body

        image_urls = _IMAGE_RE.findall(body)

        raw_id = f"{source}::{i}::{chunk_text[:100]}"
        results.append({
            "chunk_id": hashlib.md5(raw_id.encode()).hexdigest(),
            "text": chunk_text,
            "source": source,
            "heading_trail": heading_trail,
            "image_urls": image_urls,
            "storage_path": storage_path,
        })

    return results
