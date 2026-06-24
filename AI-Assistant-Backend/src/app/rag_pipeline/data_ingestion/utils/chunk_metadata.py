"""The single definition of a chunk's Pinecone metadata schema.

Both ingestion paths (live `ingestion_service`, offline `store_chunks_in_vs`) build
their `Document`s here so the metadata can never drift. Every chunk in the one
tenant namespace carries enough to (a) isolate it to a chat via a `chat_id`
filter, (b) attribute it in retrieval, and (c) clean it up on delete.
"""

from langchain_core.documents import Document

from src.api.db.models import now_utc
from src.api.services.s3_bucket_service import file_id_for


def _document_type(filename: str) -> str:
    """The file extension (lowercased, no dot), e.g. 'kubernetes-guide.pdf' → 'pdf'."""
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def build_company_chunk_documents(chunks, *, topic, source="company"):
    """Company-KB chunks: tagged by `topic` + `source="company"`, and DELIBERATELY
    NOT by user_id/chat_id. Retrieval surfaces them to every chat via a
    `{"source": "company"}` filter (see vector_store.get_company_retriever), so the
    company corpus is shared background knowledge, while `topic` (e.g. "terms and
    conditions", "policies") attributes each doc. No storage_path (vectors only).
    """
    created_at = now_utc().date().isoformat()

    documents = []
    for c in chunks:
        filename = c.get("source", "")
        documents.append(
            Document(
                page_content=c["text"],
                metadata={
                    "source": source,
                    "topic": topic,
                    "filename": filename,
                    "chunk_index": c.get("chunk_index", 0),
                    "document_type": _document_type(filename),
                    "created_at": created_at,
                    "heading_trail": c.get("heading_trail", ""),
                },
            )
        )
    return documents


def build_chunk_documents(chunks, *, user_id, chat_id, source="user_upload"):
    """Turn chunk dicts (from `chunk_markdown`) into metadata-tagged Documents.

    `filename`, `storage_path`, `file_id` and `document_type` are derived PER
    chunk from the chunk's own `source`/`storage_path`, so a single call can span
    several files (the offline batch path flattens many files into one list).

    Metadata schema (per the storage architecture):
      user_id, chat_id, file_id, source, filename, chunk_index, document_type,
      created_at  — plus storage_path / heading_trail / image_urls kept for
      retrieval formatting and best-effort cleanup.
    """
    created_at = now_utc().date().isoformat()

    documents = []
    for c in chunks:
        filename = c.get("source", "")
        storage_path = c.get("storage_path", "")
        documents.append(
            Document(
                page_content=c["text"],
                metadata={
                    "user_id": user_id,
                    "chat_id": chat_id,
                    "file_id": file_id_for(storage_path) if storage_path else "",
                    "source": source,
                    "filename": filename,
                    "chunk_index": c.get("chunk_index", 0),
                    "document_type": _document_type(filename),
                    "created_at": created_at,
                    # Retained for retrieval formatting + cleanup (not in the
                    # canonical schema list, but cheap and useful):
                    "storage_path": storage_path,
                    "heading_trail": c.get("heading_trail", ""),
                    "image_urls": c.get("image_urls", []),
                },
            )
        )
    return documents
