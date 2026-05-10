"""bge-reranker-v2-m3 cross-encoder wrapper."""
from __future__ import annotations

import os
import threading

_RERANKER = None
_LOCK = threading.Lock()


def get_reranker():
    global _RERANKER
    if _RERANKER is not None:
        return _RERANKER
    with _LOCK:
        if _RERANKER is not None:
            return _RERANKER
        from FlagEmbedding import FlagReranker
        use_fp16 = os.environ.get("BGE_USE_FP16", "1") != "0"
        _RERANKER = FlagReranker("BAAI/bge-reranker-v2-m3", use_fp16=use_fp16)
    return _RERANKER


def rerank(question: str, candidates: list[dict], top_k: int = 4) -> list[dict]:
    """Score (question, candidate.text) pairs with the cross-encoder.

    Args:
        candidates: each must have 'chunk_id' and 'payload' (with 'text').

    Returns:
        Top-k candidates with 'rerank_score' and 'rerank_rank' attached, sorted
        by rerank_score descending. Original 'fused_rank' is preserved.
    """
    if not candidates:
        return []
    model = get_reranker()
    pairs = []
    valid: list[dict] = []
    for i, c in enumerate(candidates):
        text = (c.get("payload") or {}).get("text", "")
        if not text:
            continue
        pairs.append([question, text])
        c = {**c, "fused_rank": i + 1}
        valid.append(c)
    if not pairs:
        return []
    scores = model.compute_score(pairs, normalize=True)
    if isinstance(scores, (int, float)):
        scores = [float(scores)]
    out: list[dict] = []
    for c, s in zip(valid, scores):
        out.append({**c, "rerank_score": float(s)})
    out.sort(key=lambda d: d["rerank_score"], reverse=True)
    for r, item in enumerate(out, start=1):
        item["rerank_rank"] = r
    return out[:top_k]
