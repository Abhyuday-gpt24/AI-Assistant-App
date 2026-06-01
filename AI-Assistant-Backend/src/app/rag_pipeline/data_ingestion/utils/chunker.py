from app.rag_pipeline.data_ingestion.utils.parser import parse_file
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
import hashlib
from concurrent.futures import ProcessPoolExecutor
# Chunking
def chunk_file(filepath: str) -> list[dict]:
    """Parse + Chunk a single Markdown File"""

    # Parsing 
    doc = parse_file(filepath)

    if not doc["content"].strip():
        return []
    
    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
        ],
        strip_headers=False,
        
    )
    md_sections = md_splitter.split_text(doc["content"])

    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size = 1500,
        chunk_overlap = 200,
        separators=[
            "\n```\n",
            "\n\n",
            "\n",
            " ",
        ],
    )

    final_chunks = char_splitter.split_documents(md_sections)


    # Build Output
    results = []
    for i, chunk in enumerate(final_chunks):
        body = chunk.page_content.strip()
        if not body:
            continue

        headers = chunk.metadata
        heading_trail = " > ".join(
            headers[k] for k in ("h1", "h2", "h3") if k in headers
        )

        text = f"{heading_trail}\n\n{body}" if heading_trail else body

        raw_id = f"{doc['source']}::{i}::{text[:100]}"
        chunk_id = hashlib.md5(raw_id.encode()).hexdigest()
        results.append({
            "chunk_id": chunk_id,
            "text": text,
            "source": doc["source"],
            "heading_trail": heading_trail
        })

    return results


# Chunking in multiprocess 
def chunk_batchs_in_multiprocess(file_paths: list[str], max_workers:int = None) -> list[dict]:

    if max_workers is None :
        max_workers = min(os.cpu_count(), len(file_paths))

    all_chunks = []

    with ProcessPoolExecutor(max_workers) as executor:
        results = executor.map(chunk_file, file_paths)
        for file_chunks in results:
            all_chunks.extend(file_chunks)

    return all_chunks
