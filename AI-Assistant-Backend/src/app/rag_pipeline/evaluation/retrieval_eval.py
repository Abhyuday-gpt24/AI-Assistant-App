"""Standalone retrieval evaluation — run the retrieval path WITHOUT the app.

It exercises exactly what production retrieves (the `source="company"` similarity
pool → Cohere rerank), against a curated query set, and reports three metrics:

  - Keyword match : avg fraction of each query's expected keywords found in the
                    retrieved chunk text (did we surface the right CONTENT?).
  - Source match  : fraction of queries whose expected source `filename` appears
                    in the retrieved set (did we surface the right DOCUMENT?).
  - MRR           : mean reciprocal rank of that expected source in the ranked
                    list (how HIGH did the right document rank?).

It imports only `vector_store` + `reranker` (+ `config`) — no FastAPI/graph/DB.

Prereq — ingest the corpus as company KB first:
    python -m src.app.rag_pipeline.data_ingestion.offline_batch_ingestion \\
        --dir path/to/next.js/docs --topic nextjs

Run:
    python -m src.app.rag_pipeline.evaluation.retrieval_eval \\
        [--topic nextjs] [--top-k 10] [--no-rerank] [--verbose]
"""

import argparse

from src.app.rag_pipeline.vector_store import get_vector_store, RERANK_CANDIDATES
from src.app.rag_pipeline.reranker import rerank_ranked
from src.app.rag_pipeline.evaluation.datasets.nextjs_eval import NEXTJS_EVAL

DATASETS = {"nextjs": NEXTJS_EVAL}


def _scoped_retriever(topic: str | None):
    """Similarity retriever over the company KB, optionally narrowed to one topic
    so the eval is isolated to that corpus."""
    flt = {"source": "company"}
    if topic:
        flt = {"source": "company", "topic": topic}
    return get_vector_store().as_retriever(
        search_type="similarity",
        search_kwargs={"k": RERANK_CANDIDATES, "filter": flt},
    )


def _retrieve(query: str, retriever, use_rerank: bool, top_k: int) -> list:
    """Return up to `top_k` retrieved docs in final ranked order (reranked unless
    --no-rerank); evaluation uses the raw ranking, not the production threshold."""
    docs = retriever.invoke(query)
    if use_rerank:
        ranked = rerank_ranked(query, docs)
        if ranked is not None:  # None = Cohere failed → keep base similarity order
            docs = [doc for doc, _ in ranked]
    return docs[:top_k]


def _as_list(value) -> list[str]:
    return [value] if isinstance(value, str) else list(value or [])


def _keyword_match(keywords: list[str], docs: list) -> float:
    if not keywords:
        return 0.0
    text = "\n".join(d.page_content for d in docs).lower()
    hits = sum(1 for kw in keywords if kw.lower() in text)
    return hits / len(keywords)


def _source_rank(expected, docs: list) -> int:
    """1-based rank of the first retrieved doc whose `filename` contains any
    expected substring; 0 if none match."""
    wanted = [e.lower() for e in _as_list(expected)]
    if not wanted:
        return 0
    for rank, d in enumerate(docs, start=1):
        filename = (d.metadata.get("filename") or "").lower()
        if any(w in filename for w in wanted):
            return rank
    return 0


def evaluate(dataset: list, topic: str | None, use_rerank: bool, top_k: int,
             verbose: bool) -> None:
    retriever = _scoped_retriever(topic)
    n = len(dataset)
    kw_sum = src_hits = rr_sum = 0.0
    empty_queries = 0

    print(f"\n=== Retrieval evaluation "
          f"(topic={topic or 'ALL company'}, rerank={'on' if use_rerank else 'off'}, "
          f"top_k={top_k}, candidates={RERANK_CANDIDATES}) ===\n")

    for i, item in enumerate(dataset, start=1):
        docs = _retrieve(item["query"], retriever, use_rerank, top_k)
        if not docs:
            empty_queries += 1
        kw = _keyword_match(item.get("expected_keywords", []), docs)
        rank = _source_rank(item.get("expected_source"), docs)
        rr = (1.0 / rank) if rank else 0.0

        kw_sum += kw
        src_hits += 1 if rank else 0
        rr_sum += rr

        kw_hits = round(kw * len(item.get("expected_keywords", [])))
        kw_total = len(item.get("expected_keywords", []))
        print(f"[{i:>2}] {item['query']}")
        print(f"     keyword match: {kw:.2f} ({kw_hits}/{kw_total}) | "
              f"source rank: {rank or '—'} | RR: {rr:.2f}")
        if verbose:
            for d in docs[:5]:
                print(f"        · {d.metadata.get('filename', '?')}")
        print()

    print(f"--- Summary ({n} queries) ---")
    print(f"Keyword match (avg):           {kw_sum / n:.3f}")
    print(f"Source match (filename) rate:  {src_hits / n:.3f}  ({int(src_hits)}/{n})")
    print(f"MRR:                           {rr_sum / n:.3f}")
    if empty_queries:
        print(f"\n⚠ {empty_queries}/{n} queries retrieved 0 docs — is the corpus ingested "
              f"for topic '{topic}'? Run the offline pipeline first (see module docstring).")
    print()


def main():
    parser = argparse.ArgumentParser(description="Standalone retrieval evaluation.")
    parser.add_argument("--dataset", default="nextjs", choices=sorted(DATASETS),
                        help="Which curated query set to run")
    parser.add_argument("--topic", default="nextjs",
                        help="Company-KB topic to scope retrieval to (use '' for all)")
    parser.add_argument("--top-k", type=int, default=10,
                        help="How many ranked docs to evaluate per query")
    parser.add_argument("--no-rerank", action="store_true",
                        help="Evaluate base similarity order only (skip Cohere rerank)")
    parser.add_argument("--verbose", action="store_true",
                        help="Print the top retrieved filenames per query")
    args = parser.parse_args()

    evaluate(
        dataset=DATASETS[args.dataset],
        topic=args.topic or None,
        use_rerank=not args.no_rerank,
        top_k=args.top_k,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
