"""Offline / local bulk RAG ingestion (manual batch job).

Walks a local directory of source documents, converts each to Markdown with the
*same* converter the live upload path uses (so PDF/docx/pptx/xlsx/epub/text/html/
csv are all supported, and vision-extracted images are handled), writes the
artifacts to S3, and embeds the chunks into a Pinecone namespace.

Conversion + chunking are fanned out across processes (see `utils/batch_chunker`);
embedding happens here in the parent, one batch at a time.

Run from the project root (so both `src.…` and `config` resolve):

    python -m src.app.rag_pipeline.data_ingestion.offline_batch_ingestion \\
        --dir path/to/docs --namespace my-kb [--workers 4] [--batch-size 20]
"""

import argparse
import os
import time
from pathlib import Path

from src.app.rag_pipeline.data_ingestion.utils.batch_chunker import (
    SUPPORTED_EXTENSIONS,
    ingest_files_in_multiprocess,
)
from src.app.rag_pipeline.data_ingestion.utils.store_chunks_in_vs import store_chunks
from src.app.rag_pipeline.vector_store import get_vector_store


def collect_files(dir_path: Path) -> list[str]:
    """All supported document paths under dir_path (recursive, sorted)."""
    if not dir_path.exists():
        raise FileNotFoundError(f"Path does not exist: {dir_path}")
    return [
        str(f)
        for f in sorted(dir_path.rglob("*"))
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]


def run_pipeline(doc_paths, namespace, batch_size=20, max_workers=None):
    """Ingest every supported file under `doc_paths` into the `namespace`."""
    start = time.time()

    if not namespace:
        raise ValueError("run_pipeline requires a namespace (the Pinecone / KB id)")

    file_paths = collect_files(Path(doc_paths))
    if not file_paths:
        print("No supported files found!")
        return

    vector_store = get_vector_store(namespace)

    total_files = len(file_paths)
    total_chunks = 0
    num_batches = (total_files + batch_size - 1) // batch_size

    print(f"\n[Pipeline] {total_files} files, {num_batches} batches of {batch_size}")
    print(f"[Pipeline] Workers: {max_workers or os.cpu_count()}")

    for i in range(0, total_files, batch_size):
        batch_no = i // batch_size + 1
        batch = file_paths[i: i + batch_size]

        # Convert + chunk in parallel across processes.
        chunks = ingest_files_in_multiprocess(batch, namespace, max_workers=max_workers)

        # Embed this batch (IO-bound; done in the parent).
        if chunks:
            store_chunks(chunks, vector_store)
            total_chunks += len(chunks)

        # Free memory before the next batch.
        del chunks

        files_done = min(i + batch_size, total_files)
        print(f"  Batch {batch_no}/{num_batches}: "
              f"{files_done}/{total_files} files, "
              f"{total_chunks} chunks so far")

    elapsed = time.time() - start

    print(f"\n{'='*50}")
    print(f"  Namespace:   {namespace}")
    print(f"  Files:       {total_files}")
    print(f"  Chunks:      {total_chunks}")
    print(f"  Time:        {elapsed:.1f}s")
    print(f"{'='*50}\n")


def main():
    parser = argparse.ArgumentParser(description="Offline bulk RAG ingestion.")
    parser.add_argument("--dir", required=True, help="Directory of source documents")
    parser.add_argument("--namespace", required=True, help="Pinecone namespace / KB id")
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--workers", type=int, default=None, help="Process count (default: CPU count)")
    args = parser.parse_args()
    run_pipeline(args.dir, args.namespace, args.batch_size, args.workers)


if __name__ == "__main__":
    main()
