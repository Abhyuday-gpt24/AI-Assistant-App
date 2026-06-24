"""Cohere re-ranking for retrieval.

The vector store returns a broad candidate pool (`RERANK_CANDIDATES` via cosine
similarity); this module re-orders those candidates by true query relevance with
Cohere's cross-encoder rerank model and keeps **every chunk scoring at/above a
relevance threshold** — NOT a fixed top-k. So a sharply-on-topic query keeps
several chunks, a vague one keeps few, and an off-topic one keeps none (rather
than always padding the context to k chunks of dubious relevance).

Best-effort by design: any failure (no key, network, rate limit, SDK mismatch)
falls back to the base similarity order (capped) so retrieval — and the chat —
never break on a reranker hiccup.
"""

import logging

from config import settings

logger = logging.getLogger(__name__)

# Latest Cohere rerank model (multilingual; matches the assistant's multilingual
# replies). Bump here if Cohere ships a newer one.
COHERE_RERANK_MODEL = "rerank-v3.5"

# Keep only chunks Cohere scores at/above this relevance (scores are 0..1).
# Higher = stricter (less, more on-point context); lower = more recall. This is
# the single knob that replaces a fixed top-k.
RELEVANCE_THRESHOLD = 0.3

# Degraded fallback ONLY: if the Cohere call fails there are no scores to
# threshold on, so fall back to the base similarity order capped to a small set
# (avoids dumping the whole candidate pool into the prompt).
_FALLBACK_CAP = 5

_client = None  # lazy singleton — the cohere SDK is only imported when first used


def _cohere():
    global _client
    if _client is None:
        import cohere
        _client = cohere.ClientV2(api_key=settings.COHERE_API_KEY)
    return _client


def rerank_ranked(query: str, docs: list):
    """Cohere-rank `docs` (LangChain `Document`s) by relevance to `query`. Returns
    `[(doc, relevance_score), …]` most-relevant first for ALL candidates (no
    threshold, no top-k), or **None** on any error so the caller picks a fallback.
    Used by `rerank` (production) and the retrieval evaluation (raw ranking)."""
    if not docs:
        return []
    try:
        texts = [d.page_content for d in docs]
        response = _cohere().rerank(
            model=COHERE_RERANK_MODEL,
            query=query,
            documents=texts,
        )
        return [(docs[r.index], r.relevance_score) for r in response.results]
    except Exception:
        logger.warning("Cohere rerank failed; falling back to base order", exc_info=True)
        return None


def rerank(query: str, docs: list, threshold: float = RELEVANCE_THRESHOLD) -> list:
    """Re-rank `docs` by Cohere relevance to `query` and return every chunk scoring
    at/above `threshold`, most-relevant first (may be empty if nothing clears the
    bar). Falls back to the base order (capped) on any error."""
    if not docs:
        return docs
    ranked = rerank_ranked(query, docs)
    if ranked is None:  # Cohere failed — no scores to threshold on.
        return docs[:_FALLBACK_CAP]
    return [doc for doc, score in ranked if score >= threshold]
