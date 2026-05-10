"""End-to-end retrieval: rewrite -> route -> hybrid search -> rerank.

Returns a structured trace for the RAG Explorer alongside the final context.
"""
from __future__ import annotations

import time

from . import embeddings, groq_client, prompts, qdrant_store, reranker, router, settings


def _pt_to_hit(point) -> dict:
    payload = dict(point.payload or {})
    return {
        "chunk_id": payload.get("chunk_id") or str(point.id),
        "score": float(point.score) if point.score is not None else 0.0,
        "payload": payload,
    }


def rewrite_query(question: str, history: list[dict]) -> str:
    """Condense follow-up + history into standalone query. Skip if no history."""
    if not history:
        return question
    convo = "\n".join(f"{t['role']}: {t['content']}" for t in history[-settings.HISTORY_TURNS:])
    try:
        res = groq_client.complete(
            messages=[
                {"role": "system", "content": prompts.REWRITER_SYSTEM},
                {"role": "user", "content": f"Conversation so far:\n{convo}\n\nFollow-up: {question}"},
            ],
            temperature=0.0,
            max_tokens=120,
        )
        out = res["text"].strip().strip('"')
        return out or question
    except Exception:
        return question


def retrieve_with_trace(
    question: str,
    history: list[dict] | None = None,
    forced_collections: list[str] | None = None,
) -> dict:
    """Run the full retrieval pipeline. Return final context + trace dict."""
    history = history or []
    timings: dict[str, float] = {}

    t0 = time.time()
    rewritten = rewrite_query(question, history)
    timings["rewrite_ms"] = round((time.time() - t0) * 1000, 1)

    t0 = time.time()
    if forced_collections:
        decision = {"collections": forced_collections,
                    "reason": "forced via UI source filter"}
    else:
        decision = router.route(rewritten)
    timings["route_ms"] = round((time.time() - t0) * 1000, 1)

    selected = decision["collections"]

    t0 = time.time()
    q_emb = embeddings.embed_query(rewritten)
    timings["embed_query_ms"] = round((time.time() - t0) * 1000, 1)

    client = qdrant_store.get_client()
    per_collection: dict[str, dict] = {}
    fused_all: list[dict] = []

    t0 = time.time()
    for col in selected:
        dense_pts = qdrant_store.dense_search(client, col, q_emb["dense"],
                                              limit=settings.TOP_K_PER_COLLECTION)
        sparse_pts = qdrant_store.sparse_search(client, col, q_emb["sparse"],
                                                limit=settings.TOP_K_PER_COLLECTION)
        dense_hits = [_pt_to_hit(p) for p in dense_pts]
        sparse_hits = [_pt_to_hit(p) for p in sparse_pts]

        payload_by_id: dict[str, dict] = {}
        for h in dense_hits + sparse_hits:
            payload_by_id.setdefault(h["chunk_id"], h["payload"])
        rank_lists = [[h["chunk_id"] for h in dense_hits],
                      [h["chunk_id"] for h in sparse_hits]]
        fused = qdrant_store.rrf(rank_lists, k=60)
        fused_hits = [{
            "chunk_id": cid,
            "rrf_score": round(score, 6),
            "collection": col,
            "payload": payload_by_id.get(cid, {}),
        } for cid, score in fused[:settings.TOP_K_PER_COLLECTION]]

        per_collection[col] = {
            "dense_hits": dense_hits,
            "sparse_hits": sparse_hits,
            "fused": fused_hits,
        }
        fused_all.extend(fused_hits)
    timings["search_ms"] = round((time.time() - t0) * 1000, 1)

    fused_all.sort(key=lambda h: h["rrf_score"], reverse=True)
    fused_all = fused_all[: settings.TOP_K_PER_COLLECTION]

    t0 = time.time()
    reranked = reranker.rerank(rewritten, fused_all, top_k=settings.RERANK_TOP_K)
    timings["rerank_ms"] = round((time.time() - t0) * 1000, 1)

    # Compose context blocks
    blocks = []
    for i, c in enumerate(reranked, start=1):
        payload = c.get("payload") or {}
        blocks.append({
            "id": i,
            "chunk_id": c.get("chunk_id"),
            "collection": c.get("collection") or payload.get("collection"),
            "source": _source_label(payload),
            "text": payload.get("text", ""),
            "rerank_score": c.get("rerank_score"),
            "rrf_score": c.get("rrf_score"),
            "payload": payload,
        })

    return {
        "query": {"original": question, "history": history, "rewritten": rewritten},
        "router": decision,
        "selected_collections": selected,
        "per_collection": per_collection,
        "fused_topk": fused_all,
        "rerank": reranked,
        "context_blocks": blocks,
        "timings_ms": timings,
    }


def _source_label(payload: dict) -> str:
    col = payload.get("collection", "")
    if col in ("selenium_code", "playwright_code"):
        path = payload.get("path", "?")
        sym = payload.get("symbol", "")
        s = payload.get("start_line"); e = payload.get("end_line")
        loc = f":{s}-{e}" if s and e else ""
        return f"{path}{loc} · {payload.get('kind','')} {sym}".strip()
    if col == "vwo_testcases":
        return f"{payload.get('test_case_id','?')} · {payload.get('jira_id','')} · {payload.get('module','')} · {payload.get('priority','')}".strip(" ·")
    if col == "vwo_docs":
        return f"{payload.get('doc_title','?')} · page {payload.get('page','?')}"
    if col == "vwo_bugs":
        return f"{payload.get('jira_id','?')} · {payload.get('summary','')}"
    return payload.get("chunk_id", "?")


def build_user_message(question: str, blocks: list[dict]) -> str:
    parts = []
    for b in blocks:
        parts.append(
            f'<doc id="{b["id"]}" source="{b["source"]}">\n{b["text"]}\n</doc>'
        )
    context = "\n\n".join(parts)
    return f"{context}\n\nQuestion: {question}"
