from src.app.rag_pipeline.data_ingestion.utils.chunk_metadata import build_nextjs_docs_chunk_documents
from src.app.rag_pipeline.vector_store import nextjs_docs_vector_id


def store_nextjs_docs_chunks(chunks: list[dict], vector_store, topic: str):
    """Embed Next.js-docs KB chunk dicts into the tenant namespace, tagged with
    `source="company"` + `topic` and id-prefixed `nextjs#{topic}#…`. Shared by
    every chat at retrieval time (no chat_id scoping)."""
    documents = build_nextjs_docs_chunk_documents(chunks, topic=topic)
    ids = [nextjs_docs_vector_id(topic, c["chunk_id"]) for c in chunks]
    vector_store.add_documents(documents, ids=ids)
    return ids
