"""Pinecone access — ONE tenant namespace, per-chat isolation via metadata.

Every vector for the whole app lives in a single namespace (`settings.PINECONE_NAMESPACE`,
the tenant/company id). A chat is isolated NOT by having its own namespace but by a
`chat_id` metadata filter applied at retrieval time. Chunk ids are prefixed with
`{chat_id}#` so a chat's vectors can be listed (and deleted) by id-prefix — the
serverless-safe way to delete a subset (serverless Pinecone does not support
delete-by-metadata-filter).
"""

import logging
import re

from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from config import settings
from langchain_openai.embeddings import OpenAIEmbeddings


logger = logging.getLogger(__name__)

_vector_store = None          # the single tenant-namespace store (built once)
retrievers = {}               # chat_id → retriever (filtered store)
index_initialized = False


def _tenant_namespace() -> str:
    return settings.PINECONE_NAMESPACE


def chunk_vector_id(chat_id: str, chunk_id: str) -> str:
    """The Pinecone vector id for a chat-upload chunk: '{chat_id}#{chunk_id}'. The
    prefix is what lets us list/delete exactly one chat's vectors on serverless."""
    return f"{chat_id}#{chunk_id}"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-") or "topic"


def nextjs_docs_vector_id(topic: str, chunk_id: str) -> str:
    """The Pinecone vector id for a Next.js-docs KB chunk:
    'nextjs#{topic}#{chunk_id}'. The 'nextjs#' prefix separates the shared docs
    corpus from per-chat vectors; the topic slug allows future per-topic
    listing/deletion."""
    return f"nextjs#{_slug(topic)}#{chunk_id}"


def get_vector_store():
    """The single tenant-namespace vector store (shared by every chat). Per-chat
    scoping is done with metadata filters on the retriever, not here."""
    global _vector_store, index_initialized
    if _vector_store is not None:
        return _vector_store

    pinecone_index_name = settings.PINECONE_INDEX_NAME

    # Index creation only needs to happen once.
    if not index_initialized:
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        existing = [idx.name for idx in pc.list_indexes()]
        if pinecone_index_name not in existing:
            pc.create_index(
                name=pinecone_index_name,
                dimension=1536,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
        index_initialized = True

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=settings.OPENAI_API_KEY)

    _vector_store = PineconeVectorStore(
        index_name=pinecone_index_name,
        embedding=embeddings,
        namespace=_tenant_namespace(),
        pinecone_api_key=settings.PINECONE_API_KEY,
    )
    return _vector_store


# How many candidates to pull from the vector store BEFORE re-ranking. The
# embedding step casts a wide net (recall); Cohere then re-ranks down to the
# final top-k in the retrieval node (precision). See rag_pipeline/reranker.py.
RERANK_CANDIDATES = 20


def _build_retriever(filter_dict: dict, cache_key: str, k: int):
    """Similarity retriever over the tenant namespace, scoped by a metadata
    `filter_dict` and memoized under `cache_key`. Returns a broad candidate pool
    (`k` = `RERANK_CANDIDATES`) that the retrieval node then re-ranks with Cohere."""
    if cache_key in retrievers:
        return retrievers[cache_key]
    retriever = get_vector_store().as_retriever(
        search_type="similarity",
        search_kwargs={"k": k, "filter": filter_dict},
    )
    retrievers[cache_key] = retriever
    return retriever


def get_user_docs_retriever(chat_id: str, k=RERANK_CANDIDATES):
    """Retriever over ONLY this chat's own uploaded docs (`{"chat_id": chat_id}`).
    The analyzer routes here for questions about the user's own files. Returns the
    pre-rerank candidate pool."""
    if not chat_id:
        raise ValueError("get_user_docs_retriever requires a chat_id")
    return _build_retriever({"chat_id": chat_id}, f"user:{chat_id}", k)


def get_nextjs_docs_retriever(k=RERANK_CANDIDATES):
    """Retriever over the curated Next.js documentation KB
    (`{"source": "company", "topic": "nextjs"}`) — the same docs corpus for every chat. The
    analyzer routes here for questions about Next.js. Returns the pre-rerank
    candidate pool."""
    return _build_retriever({"source": "company", "topic": "nextjs"}, "nextjs", k)


def _chat_vector_ids(index, chat_id: str) -> list[str]:
    """Every Pinecone vector id belonging to a chat, found by id-prefix."""
    ids: list[str] = []
    for page in index.list(prefix=f"{chat_id}#", namespace=_tenant_namespace()):
        ids.extend(page)
    return ids


def collect_chat_storage_paths(chat_id: str) -> set[str]:
    """Best-effort: the distinct source `storage_path`s embedded for a chat, read
    from vector metadata (used as a deletion fallback). Empty set on any failure
    so deletion never blocks on Pinecone."""
    paths: set[str] = set()
    if not chat_id:
        return paths
    try:
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        index = pc.Index(settings.PINECONE_INDEX_NAME)
        ids = _chat_vector_ids(index, chat_id)
        for i in range(0, len(ids), 100):
            fetched = index.fetch(ids=ids[i:i + 100], namespace=_tenant_namespace())
            for vector in fetched.vectors.values():
                meta = vector.metadata or {}
                if meta.get("storage_path"):
                    paths.add(meta["storage_path"])
    except Exception:
        logger.warning("collect_chat_storage_paths failed for %s", chat_id,
                       exc_info=True)
    return paths


def delete_chat_vectors(chat_id: str) -> None:
    """Delete every vector belonging to a chat (by id-prefix '{chat_id}#') from
    the tenant namespace, and evict its cached retriever. Best-effort: a chat that
    never ingested a doc simply has no vectors."""
    if not chat_id:
        return
    try:
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        index = pc.Index(settings.PINECONE_INDEX_NAME)
        ids = _chat_vector_ids(index, chat_id)
        for i in range(0, len(ids), 1000):
            index.delete(ids=ids[i:i + 1000], namespace=_tenant_namespace())
    except Exception:
        logger.info("delete_chat_vectors: nothing to delete for %s", chat_id)
    retrievers.pop(f"user:{chat_id}", None)
