"""bge-reranker-v2-m3 cross-encoder. Ported from Ch8 Advance lib/rerank.py."""
from __future__ import annotations

import os
import threading

from . import settings

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
        _RERANKER = FlagReranker(settings.RERANK_MODEL, use_fp16=use_fp16)
    return _RERANKER


def rerank(question: str, candidates: list[dict], top_k: int = 4) -> list[dict]:
    """Score (question, candidate.text) pairs. Returns top-k with rerank_score."""
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
        valid.append({**c, "fused_rank": i + 1})
    if not pairs:
        return []
    scores = model.compute_score(pairs, normalize=True)
    if isinstance(scores, (int, float)):
        scores = [float(scores)]
    out = [{**c, "rerank_score": float(s)} for c, s in zip(valid, scores)]
    out.sort(key=lambda d: d["rerank_score"], reverse=True)
    for r, item in enumerate(out, start=1):
        item["rerank_rank"] = r
    return out[:top_k]
