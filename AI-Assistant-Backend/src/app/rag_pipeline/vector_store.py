from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from config import settings
from langchain_openai.embeddings import OpenAIEmbeddings


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