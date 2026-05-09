"""Hybrid search + Reciprocal Rank Fusion."""
from __future__ import annotations

from . import store


def rrf(rank_lists: list[list[str]], k: int = 60) -> list[tuple[str, float, list[int]]]:
    """Reciprocal Rank Fusion.

    Args:
        rank_lists: list of ranked id lists (rank 1 = best).
        k: RRF smoothing constant (60 is standard from the original paper).

    Returns:
        List of (id, fused_score, source_ranks_per_list) sorted by score desc.
        source_ranks is per-input-list 1-based rank or 0 if not present.
    """
    score: dict[str, float] = {}
    sources: dict[str, list[int]] = {}
    n_lists = len(rank_lists)
    for li, ranked in enumerate(rank_lists):
        for r, doc_id in enumerate(ranked, start=1):
            score[doc_id] = score.get(doc_id, 0.0) + 1.0 / (k + r)
            if doc_id not in sources:
                sources[doc_id] = [0] * n_lists
            sources[doc_id][li] = r
    out = [(doc_id, score[doc_id], sources[doc_id]) for doc_id in score]
    out.sort(key=lambda t: t[1], reverse=True)
    return out


def hybrid_search(
    client,
    collection: str,
    queries: list[dict],
    top_n: int = 20,
    flt: dict | None = None,
) -> dict:
    """Run dense + sparse search per query and fuse with RRF.

    Args:
        queries: list of {'text': str, 'dense': np.ndarray, 'sparse': {indices, values}}.

    Returns:
        {
          'per_query': [{'text', 'dense_hits', 'sparse_hits'}, ...]  # raw hits
          'fused': [{'chunk_id', 'rrf_score', 'sources', 'payload', 'best_dense_score'}, ...]
        }
    """
    per_query = []
    rank_lists: list[list[str]] = []
    payload_by_id: dict[str, dict] = {}
    best_dense: dict[str, float] = {}

    for q in queries:
        dense_pts = store.dense_search(client, collection, q["dense"], limit=top_n, flt=flt)
        sparse_pts = store.sparse_search(client, collection, q["sparse"], limit=top_n, flt=flt)

        dense_hits = [_pt_to_dict(p) for p in dense_pts]
        sparse_hits = [_pt_to_dict(p) for p in sparse_pts]

        for h in dense_hits + sparse_hits:
            cid = h["chunk_id"]
            payload_by_id.setdefault(cid, h["payload"])
        for h in dense_hits:
            cid = h["chunk_id"]
            best_dense[cid] = max(best_dense.get(cid, -1.0), h["score"])

        rank_lists.append([h["chunk_id"] for h in dense_hits])
        rank_lists.append([h["chunk_id"] for h in sparse_hits])

        per_query.append({
            "text": q["text"],
            "dense_hits": dense_hits,
            "sparse_hits": sparse_hits,
        })

    fused_raw = rrf(rank_lists, k=60)
    fused = []
    for cid, score, sources in fused_raw:
        fused.append({
            "chunk_id": cid,
            "rrf_score": round(score, 6),
            "sources": sources,  # per-list rank
            "payload": payload_by_id.get(cid, {}),
            "best_dense_score": round(best_dense.get(cid, 0.0), 4),
        })

    return {"per_query": per_query, "fused": fused}


def _pt_to_dict(point) -> dict:
    payload = dict(point.payload or {})
    return {
        "chunk_id": payload.get("chunk_id") or str(point.id),
        "score": float(point.score) if point.score is not None else 0.0,
        "payload": payload,
    }
