from langchain_core.documents import Document


def store_chunks(chunks: list[dict], vector_store):
    """Convert chunk dicts to LangChain Documents and add to Pinecone"""
    documents = []
    ids = []

    for chunk in chunks:
        documents.append(
            Document(
                page_content=chunk["text"],
                metadata={
                    "source": chunk["source"],
                    "heading_trail": chunk["heading_trail"],
                    # Parity with the live path: keep the source doc reference and
                    # any image URLs lifted out of the chunk so retrieval can
                    # surface them.
                    "storage_path": chunk.get("storage_path", ""),
                    "image_urls": chunk.get("image_urls", []),
                },
            )
        )
        ids.append(chunk["chunk_id"])

    vector_store.add_documents(documents, ids=ids)
    return ids