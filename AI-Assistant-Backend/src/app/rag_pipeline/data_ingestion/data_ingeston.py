from pathlib import Path
import time
from app.rag_pipeline.data_ingestion.utils.clean_markdown_file import clean_markdown
from app.rag_pipeline.data_ingestion.utils.chunker import chunk_batchs_in_multiprocess
from app.rag_pipeline.data_ingestion.utils.store_chunks_in_vs import store_chunks
from app.rag_pipeline.vector_store import get_vector_store
import os


def collect_files(dir_path: str)-> list[str]:
    """Collects all file paths into a list"""
    if not dir_path.exists():
        raise FileNotFoundError(f"Path does not exist: {dir_path}")
    
    file_paths = [str(f) for f in sorted(dir_path.rglob("*.mdx"))]
    return file_paths

# Full Pipeline
def run_pipeline(
    doc_paths:str,
    namespace:str,
    batch_size:int = 20,
    max_workers:int = None,
):

    start = time.time()

    if not namespace:
        raise ValueError("run_pipeline requires a namespace (user_id)")

    # Collect
    file_paths = collect_files(doc_paths)
    if not file_paths:
        print("No Files Found!")
        return

    vector_store = get_vector_store(namespace)

    # Process in batches
    total_files = len(file_paths)
    total_chunks = 0
    num_batches = (total_files + batch_size - 1) // batch_size

    # For process updates logs
    print(f"\n[Pipeline] {total_files} files, {num_batches} batches of {batch_size}")
    print(f"[Pipeline] Workers: {max_workers or os.cpu_count()}")

    # Looping through batches
    for i in range(0, total_files, batch_size):            
        num_of_batchs = i // batch_size + 1                 
        batch_file_paths = file_paths[i : i + batch_size]
 
        # Chunk in parallel (multiprocessing)
        chunks = chunk_batchs_in_multiprocess(batch_file_paths, max_workers)
 
        # Store in vector DB
        if chunks:
            ids = store_chunks(chunks, vector_store)
            total_chunks += len(chunks)
 
        # Free memory before next batch
        del chunks

        # For process updates logs
        files_done = min(i + batch_size, total_files)
        print(f"  Batch {num_of_batchs}/{num_batches}: "
              f"{files_done}/{total_files} files, "
              f"{total_chunks} chunks so far")
 
    elapsed = time.time() - start
 
    # Summary Status
    print(f"\n{'='*50}")
    print(f"  Namespace:   {namespace}")
    print(f"  Files:       {total_files}")
    print(f"  Chunks:      {total_chunks}")
    print(f"  Time:        {elapsed:.1f}s")
    print(f"{'='*50}\n")
 
# Run data ingestion pipeline
# dir_path = Path("data/next_js/docs").resolve()
# print(dir_path)

# def runpipe():
#     run_pipeline(doc_paths=dir_path, namespace="<user_id>", max_workers=4)

