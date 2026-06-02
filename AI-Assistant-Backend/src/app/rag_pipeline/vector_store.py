import logging

from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from config import settings
from langchain_openai.embeddings import OpenAIEmbeddings


logger = logging.getLogger(__name__)

vector_stores = {}
retrievers = {}
index_initialized = False


def get_vector_store(namespace: str):
    """Vector store scoped to a namespace (the chat_id). RAG is fully per-chat —
    there is no shared/global knowledge base, so a namespace is required."""
    if not namespace:
        raise ValueError("get_vector_store requires a namespace (chat_id)")
    global index_initialized
    collection = namespace
    if collection in vector_stores:
        return vector_stores[collection]

    pinecone_index_name = settings.PINECONE_INDEX_NAME

    # Index creation only needs to happen once
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

    store = PineconeVectorStore(
        index_name=pinecone_index_name,
        embedding=embeddings,
        namespace=collection,
        pinecone_api_key=settings.PINECONE_API_KEY,
    )
    vector_stores[collection] = store
    return store


def get_retriever(namespace: str, k=4):
    """Retriever scoped to a namespace (the chat_id). Per-chat only."""
    if not namespace:
        raise ValueError("get_retriever requires a namespace (chat_id)")
    collection = namespace
    if collection in retrievers:
        return retrievers[collection]

    retriever = get_vector_store(namespace).as_retriever(
        search_type="mmr",
        search_kwargs={"k": k, "fetch_k": 25, "lambda_mult": 0.85},
    )
    retrievers[collection] = retriever
    return retriever


def collect_namespace_storage_paths(namespace: str) -> set[str]:
    """Best-effort: the distinct source `storage_path`s embedded in a namespace,
    read from vector metadata. Used as a fallback to clean up S3 docs for chats
    that pre-date per-chat attachment tracking. Returns an empty set on any
    failure (so deletion never blocks on Pinecone)."""
    paths: set[str] = set()
    if not namespace:
        return paths
    try:
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        index = pc.Index(settings.PINECONE_INDEX_NAME)
        ids: list[str] = []
        for page in index.list(namespace=namespace):
            ids.extend(page)
        for i in range(0, len(ids), 100):
            fetched = index.fetch(ids=ids[i:i + 100], namespace=namespace)
            for vector in fetched.vectors.values():
                meta = vector.metadata or {}
                if meta.get("storage_path"):
                    paths.add(meta["storage_path"])
    except Exception:
        logger.warning("collect_namespace_storage_paths failed for %s", namespace,
                       exc_info=True)
    return paths


def delete_namespace(namespace: str) -> None:
    """Delete every vector in a namespace (= chat_id) and drop its cached store.
    Best-effort: a namespace that never had docs ingested simply isn't there."""
    if not namespace:
        return
    try:
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        index = pc.Index(settings.PINECONE_INDEX_NAME)
        index.delete(delete_all=True, namespace=namespace)
    except Exception:
        # Namespace may not exist (no docs ingested into this chat) — that's fine.
        logger.info("delete_namespace: nothing to delete for %s", namespace)
    vector_stores.pop(namespace, None)
    retrievers.pop(namespace, None)