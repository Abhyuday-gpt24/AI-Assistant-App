from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from config import settings
from langchain_openai.embeddings import OpenAIEmbeddings


vector_stores = {}
retrievers = {}
index_initialized = False


def get_vector_store():
    global index_initialized
    collection = settings.NAMESPACE_METADATA
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

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    store = PineconeVectorStore(
        index_name=pinecone_index_name,
        embedding=embeddings,
        namespace=collection,
    )
    vector_stores[collection] = store
    return store


def get_retriever(k=4):
    collection = settings.NAMESPACE_METADATA
    if collection in retrievers:
        return retrievers[collection]

    retriever = get_vector_store().as_retriever(
        search_type="mmr",
        search_kwargs={"k": k, "fetch_k": 25, "lambda_mult": 0.85},
    )
    retrievers[collection] = retriever
    return retriever