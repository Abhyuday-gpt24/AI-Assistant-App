"""Query-aware selection of an attached document's text for the synthesizer.

When a user attaches a document and asks about it, we can't dump the whole file
into the prompt — a large doc blows the context window and costs tokens every
turn. The old behavior injected only the FIRST `budget` characters, so a question
about anything past the opening pages had no supporting text.

This instead picks the parts of the document MOST relevant to the current
question: a small doc is returned whole; a large doc is chunked (the shared
`chunk_markdown`), Cohere-reranked against the query, and the top chunks are
packed up to `budget`, then re-ordered into document order for readable flow.

For a HUGE doc the chunk count can exceed Cohere's per-call document limit, so a
cheap lexical pre-filter first narrows the pool to the `COHERE_MAX_DOCS` most
query-relevant chunks (whole-doc coverage, no extra API cost) before the rerank.

This is the SAME-TURN complement to RAG retrieval: whole-document coverage across
later turns still comes from `user_docs` retrieval over the chat's ingested
chunks; this covers the current turn without waiting on the async indexing.
"""

import logging
import re

logger = logging.getLogger(__name__)

# Cohere's rerank endpoint caps documents per call (~1000). Beyond this we
# pre-filter the chunk pool down to this many candidates before reranking.
COHERE_MAX_DOCS = 1000

_WORD_RE = re.compile(r"[a-z0-9]+")


def _terms(text: str) -> set[str]:
    return set(_WORD_RE.findall((text or "").lower()))


def _prefilter(chunks: list[dict], query: str, cap: int) -> list[tuple[int, dict]]:
    """Narrow `chunks` to at most `cap` candidates while keeping whole-doc coverage.

    Rank every chunk by cheap lexical overlap with the query and keep the top
    `cap` (ties → earlier chunk first). If nothing overlaps at all (e.g. a pure
    paraphrase), fall back to an EVENLY-SPACED sample across the document so we
    don't silently keep only the opening pages. Returns (original_index, chunk)
    so document order can be restored after reranking.
    """
    q = _terms(query)
    scores = [(len(q & _terms(c["text"])), i) for i, c in enumerate(chunks)]
    if any(s > 0 for s, _ in scores):
        top = sorted(scores, key=lambda t: (t[0], -t[1]), reverse=True)[:cap]
        keep = sorted(i for _, i in top)
    else:
        step = len(chunks) / cap
        keep = sorted({int(k * step) for k in range(cap)})
    return [(i, chunks[i]) for i in keep]


def select_relevant_doc_text(markdown: str, query: str, budget: int) -> str:
    """Return up to ~`budget` chars of `markdown`, biased to what answers `query`.

    - doc fits the budget → returned whole (unchanged behavior for small files);
    - no query to rank against → leading slice (old behavior);
    - otherwise → chunk + (pre-filter if huge) + Cohere-rerank, pack the
      most-relevant chunks up to the budget, re-ordered into document order.
    Any failure (no chunks, Cohere down, import error) degrades to the leading
    slice, so this can never break a turn.
    """
    text = (markdown or "").strip()
    if not text or len(text) <= budget:
        return text
    if not query:
        return text[:budget]

    try:
        from langchain_core.documents import Document
        from src.app.rag_pipeline.data_ingestion.utils.markdown_chunker import chunk_markdown
        from src.app.rag_pipeline.reranker import rerank_ranked

        chunks = chunk_markdown(text, source="attachment")
        if not chunks:
            return text[:budget]

        # Cap the rerank input so a huge doc can't exceed Cohere's per-call limit.
        # The lexical pre-filter keeps the most query-relevant chunks from ANYWHERE
        # in the doc (not just the head), preserving whole-doc coverage.
        if len(chunks) > COHERE_MAX_DOCS:
            candidates = _prefilter(chunks, query, COHERE_MAX_DOCS)
            logger.info("attachment rerank input capped: %d chunks → %d candidates",
                        len(chunks), len(candidates))
        else:
            candidates = list(enumerate(chunks))

        docs = [Document(page_content=c["text"], metadata={"i": i})
                for i, c in candidates]
        ranked = rerank_ranked(query, docs)  # [(doc, score), …] best-first, or None
        if not ranked:
            return text[:budget]  # Cohere unavailable → leading slice

        picked: list[tuple[int, str]] = []
        used = 0
        for doc, _score in ranked:
            block = doc.page_content.strip()
            if not block:
                continue
            cost = len(block) + 2  # +2 for the "\n\n" join between blocks
            if used + cost > budget:
                if not picked:  # the single most-relevant chunk alone exceeds budget
                    picked.append((doc.metadata["i"], block[:budget]))
                break
            picked.append((doc.metadata["i"], block))
            used += cost

        if not picked:
            return text[:budget]

        picked.sort(key=lambda p: p[0])  # document order → readable flow
        return "\n\n".join(block for _, block in picked)
    except Exception:
        logger.warning("Query-aware doc selection failed; using leading slice",
                       exc_info=True)
        return text[:budget]
