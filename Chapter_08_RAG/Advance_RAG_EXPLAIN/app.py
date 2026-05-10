"""Advanced RAG Explorer - Flask app.

Single-process app that exposes:
  GET  /            -> redirect to /upload (or /chat if collection populated)
  GET  /upload      -> upload form
  POST /upload      -> save file, redirect to /ingest preview
  GET  /ingest      -> ingest preview (column picker, tunables)
  POST /ingest      -> kick off background ingest job; returns job id
  GET  /ingest/stream?job=...  -> SSE stream of stages
  GET  /chunks      -> paginated DB viewer
  GET  /chat        -> chat UI
  POST /chat        -> kick off background chat job; returns job id
  GET  /chat/stream?job=... -> SSE stream of stages + answer
  GET  /api/collection-info  -> JSON {points, exists, ...}
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from collections import Counter
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from flask import (
    Flask, Response, jsonify, redirect, render_template_string, request,
    send_from_directory, url_for,
)

from lib import chunking, embeddings, llm, rerank, retrieve, store

load_dotenv()

# ---- tunables ---------------------------------------------------------------
HERE = Path(__file__).parent
DATA_DIR = HERE / "data"
DATA_DIR.mkdir(exist_ok=True)
STATIC_DIR = HERE / "static"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
INGEST_BATCH = int(os.environ.get("INGEST_BATCH", "16"))

TOP_N_HYBRID = 20
TOP_K_RERANK = 4
RRF_K = 60
REWRITE_ENABLED = os.environ.get("REWRITE_ENABLED", "1") != "0"

COLLECTION = os.environ.get("COLLECTION_NAME", "vwo_test_cases")
QDRANT_URL = os.environ.get("QDRANT_URL", "").strip() or "embedded ./qdrant_data"
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

PORT = int(os.environ.get("PORT", "5050"))

DEFAULT_TEXT_COLS = ["title", "summary", "description", "steps", "expected",
                     "expected_result", "preconditions", "tags", "labels"]
DEFAULT_META_COLS = ["id", "jira_id", "priority", "severity", "module",
                     "owner", "test_type", "sprint", "status"]

# ---- in-memory job state ----------------------------------------------------
_JOBS: dict[str, dict] = {}
_LAST_RETRIEVED: dict[str, list[str]] = {"chunk_ids": []}


def _new_job() -> str:
    jid = uuid.uuid4().hex[:12]
    _JOBS[jid] = {"events": [], "done": False, "lock": threading.Lock()}
    return jid


def _emit(jid: str, stage: str, status: str, payload: dict | None = None) -> None:
    job = _JOBS.get(jid)
    if not job:
        return
    with job["lock"]:
        job["events"].append({
            "stage": stage,
            "status": status,
            "payload": payload or {},
            "t": time.time(),
        })


def _finish(jid: str, payload: dict | None = None) -> None:
    job = _JOBS.get(jid)
    if not job:
        return
    with job["lock"]:
        job["done"] = True
        if payload:
            job["result"] = payload


def _stream(jid: str):
    """SSE generator: yields events as they appear; closes when done=True."""
    sent = 0
    job = _JOBS.get(jid)
    if not job:
        yield f"event: error\ndata: {json.dumps({'error': 'unknown job'})}\n\n"
        return
    while True:
        with job["lock"]:
            evts = job["events"][sent:]
            sent = len(job["events"])
            done = job["done"]
            result = job.get("result")
        for evt in evts:
            yield f"data: {json.dumps(evt)}\n\n"
        if done:
            yield f"event: done\ndata: {json.dumps(result or {})}\n\n"
            return
        time.sleep(0.15)


# ---- Flask app --------------------------------------------------------------
app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB CSV/XLSX

# ---- Layout shell -----------------------------------------------------------
LAYOUT = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{{title or 'Advanced RAG Explorer'}}</title>
  <link rel="stylesheet" href="/static/claude.css">
  {% block head %}{% endblock %}
</head>
<body>
  <div class="layout">
    <aside class="left-panel">
      <div class="brand">
        <div class="brand-logo">A</div>
        <div>
          <div class="brand-name">Advanced RAG</div>
          <div class="brand-sub">Explorer</div>
        </div>
      </div>
      <nav class="nav">
        <a href="/upload" class="{{ 'active' if active=='upload' else '' }}">Upload &amp; Ingest</a>
        <a href="/chunks" class="{{ 'active' if active=='chunks' else '' }}">Chunks Viewer</a>
        <a href="/chat"   class="{{ 'active' if active=='chat'   else '' }}">Chat</a>
      </nav>

      <div class="tracker-title">Pipeline</div>
      <div class="stages" id="stages">
        {% for s in stages %}
          <div class="stage {{s.cls or ''}}" data-stage="{{s.key}}">
            <div class="dot"></div>
            <div class="stage-body">
              <div class="stage-title">{{s.title}}</div>
              <div class="stage-meta">{{s.meta or ''}}</div>
            </div>
          </div>
        {% endfor %}
      </div>

      <hr class="hr">
      <div class="small muted">
        Embed: <span class="mono">bge-m3</span><br>
        DB: <span class="mono">Qdrant ({{qdrant_url}})</span><br>
        Reranker: <span class="mono">bge-reranker-v2-m3</span><br>
        LLM: <span class="mono">{{groq_model}}</span>
      </div>
    </aside>

    <main class="right-pane">
      {% block content %}{% endblock %}
    </main>
  </div>
</body>
</html>
"""

INGEST_STAGES = [
    {"key": "read",   "title": "Read file",     "meta": ""},
    {"key": "build",  "title": "Build documents", "meta": ""},
    {"key": "chunk",  "title": "Chunk",         "meta": ""},
    {"key": "embed",  "title": "Embed (dense+sparse)", "meta": ""},
    {"key": "index",  "title": "Index in Qdrant", "meta": ""},
]

CHAT_STAGES = [
    {"key": "question",     "title": "Question",         "meta": ""},
    {"key": "rewrite",      "title": "Query rewrite",    "meta": ""},
    {"key": "embed",        "title": "Embed queries",    "meta": ""},
    {"key": "dense",        "title": "Dense search",     "meta": ""},
    {"key": "sparse",       "title": "Sparse search",    "meta": ""},
    {"key": "fuse",         "title": "RRF fuse",         "meta": ""},
    {"key": "rerank",       "title": "Cross-encoder rerank", "meta": ""},
    {"key": "generate",     "title": "Groq generate",    "meta": ""},
]


def _render(template: str, *, active: str, stages: list[dict], title: str = "", **ctx):
    page = LAYOUT.replace("{% block content %}{% endblock %}", template)
    return render_template_string(
        page,
        active=active,
        stages=stages,
        title=title,
        groq_model=GROQ_MODEL,
        qdrant_url=QDRANT_URL,
        **ctx,
    )


# ---- routes -----------------------------------------------------------------
@app.route("/")
def home():
    client = store.get_client()
    info = store.collection_info(client, COLLECTION)
    if info["exists"] and info["points"] > 0:
        return redirect(url_for("chat"))
    return redirect(url_for("upload"))


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        f = request.files.get("file")
        if not f or not f.filename:
            return _render(UPLOAD_TPL, active="upload", stages=INGEST_STAGES,
                          title="Upload", error="No file selected")
        ext = Path(f.filename).suffix.lower()
        if ext not in (".csv", ".xlsx", ".xls"):
            return _render(UPLOAD_TPL, active="upload", stages=INGEST_STAGES,
                          title="Upload", error=f"Unsupported file type: {ext}")
        target = DATA_DIR / f.filename
        f.save(target)
        return redirect(url_for("ingest_preview", file=f.filename))
    return _render(UPLOAD_TPL, active="upload", stages=INGEST_STAGES, title="Upload")


@app.route("/ingest", methods=["GET", "POST"])
def ingest_preview():
    if request.method == "POST":
        return _start_ingest()
    fname = request.args.get("file", "")
    if not fname:
        return redirect(url_for("upload"))
    fpath = DATA_DIR / fname
    if not fpath.exists():
        return redirect(url_for("upload"))
    df = _read_dataframe(fpath, nrows=50)
    full_count = _row_count(fpath)
    cols = list(df.columns)
    text_pre = [c for c in cols if c.lower() in DEFAULT_TEXT_COLS]
    meta_pre = [c for c in cols if c.lower() in DEFAULT_META_COLS]
    head_html = df.head(5).to_html(classes="preview-table", index=False, border=0,
                                   na_rep="", escape=True)
    dtypes = [(c, str(df[c].dtype)) for c in cols]
    return _render(
        INGEST_TPL,
        active="upload",
        stages=INGEST_STAGES,
        title="Ingest preview",
        file=fname,
        cols=cols,
        text_pre=text_pre,
        meta_pre=meta_pre,
        head_html=head_html,
        dtypes=dtypes,
        full_count=full_count,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )


def _start_ingest():
    fname = request.form.get("file", "")
    text_cols = request.form.getlist("text_cols")
    meta_cols = request.form.getlist("meta_cols")
    chunk_size = int(request.form.get("chunk_size") or CHUNK_SIZE)
    chunk_overlap = int(request.form.get("chunk_overlap") or CHUNK_OVERLAP)
    recreate = request.form.get("recreate") == "on"
    fpath = DATA_DIR / fname
    if not fpath.exists() or not text_cols:
        return jsonify({"error": "missing file or text columns"}), 400
    jid = _new_job()
    t = threading.Thread(
        target=_ingest_job,
        args=(jid, str(fpath), text_cols, meta_cols, chunk_size, chunk_overlap, recreate),
        daemon=True,
    )
    t.start()
    return jsonify({"job": jid})


@app.route("/ingest/stream")
def ingest_stream():
    jid = request.args.get("job", "")
    return Response(_stream(jid), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _ingest_job(jid, fpath, text_cols, meta_cols, size, overlap, recreate):
    try:
        # Stage 1: read
        _emit(jid, "read", "active", {"file": Path(fpath).name})
        df = _read_dataframe(Path(fpath))
        rows = df.to_dict(orient="records")
        _emit(jid, "read", "done", {
            "rows": len(rows),
            "columns": list(df.columns),
            "dtypes": {c: str(df[c].dtype) for c in df.columns},
            "head": df.head(5).fillna("").astype(str).to_dict(orient="records"),
        })

        # Stage 2: build documents
        _emit(jid, "build", "active")
        sample_docs = []
        for r in rows[:3]:
            sample_docs.append(chunking.assemble_document(r, text_cols))
        _emit(jid, "build", "done", {"sample_docs": sample_docs})

        # Stage 3: chunk
        _emit(jid, "chunk", "active")
        chunks = chunking.chunk_dataframe(
            rows, text_cols=text_cols, meta_cols=meta_cols,
            size=size, overlap=overlap, source_file=Path(fpath).name,
        )
        if not chunks:
            raise RuntimeError("No chunks produced - text columns empty?")
        per_row = Counter(c["metadata"]["row_index"] for c in chunks)
        hist = Counter(per_row.values())
        char_lens = [len(c["text"]) for c in chunks]
        sample_chunks = []
        for c in chunks[:3]:
            sample_chunks.append({
                "id": c["id"],
                "text": c["text"],
                "metadata": _safe(c["metadata"]),
                "overlap_prefix_len": c["overlap_prefix_len"],
            })
        _emit(jid, "chunk", "done", {
            "total_chunks": len(chunks),
            "rows_with_chunks": len(per_row),
            "avg_chars": round(sum(char_lens) / len(char_lens), 1),
            "min_chars": min(char_lens),
            "max_chars": max(char_lens),
            "histogram": sorted(hist.items()),
            "sample_chunks": sample_chunks,
            "chunk_size": size,
            "chunk_overlap": overlap,
        })

        # Stage 4: embed
        _emit(jid, "embed", "active", {"total": len(chunks), "done": 0})
        all_dense = []
        all_sparse: list[dict] = []
        texts = [c["text"] for c in chunks]
        # batch with progress
        bs = INGEST_BATCH
        for i in range(0, len(texts), bs):
            sub = texts[i:i + bs]
            res = embeddings.embed_batch(sub, batch_size=len(sub))
            all_dense.append(res["dense"])
            all_sparse.extend(res["sparse"])
            _emit(jid, "embed", "active", {"total": len(chunks), "done": min(i + bs, len(chunks))})
        import numpy as np
        dense = np.vstack(all_dense)

        sample_emb = []
        for i in range(min(3, len(chunks))):
            d_prev = [round(float(x), 4) for x in dense[i][:8].tolist()]
            sp_terms = embeddings.decode_sparse_terms(all_sparse[i], k=5)
            sample_emb.append({
                "chunk_id": chunks[i]["id"],
                "dense_dim": int(dense.shape[1]),
                "dense_preview": d_prev,
                "sparse_top": [{"term": t, "weight": round(w, 4)} for t, w in sp_terms],
            })
        _emit(jid, "embed", "done", {
            "total": len(chunks),
            "dense_dim": int(dense.shape[1]),
            "sparse_avg_nnz": round(sum(len(s["indices"]) for s in all_sparse) / max(1, len(all_sparse)), 2),
            "sample": sample_emb,
        })

        # Stage 5: index
        _emit(jid, "index", "active")
        client = store.get_client()
        store.bootstrap(client, COLLECTION, recreate=recreate)
        written = store.upsert_chunks(client, COLLECTION, chunks, dense, all_sparse, batch_size=64)
        info = store.collection_info(client, COLLECTION)
        is_server = QDRANT_URL.startswith("http")
        _emit(jid, "index", "done", {
            "written": written,
            "collection": COLLECTION,
            "points": info["points"],
            "qdrant_url": QDRANT_URL,
            "dashboard": (f"{QDRANT_URL.rstrip('/')}/dashboard" if is_server else ""),
        })

        _finish(jid, {"ok": True, "chunks": len(chunks), "written": written})
    except Exception as e:
        _emit(jid, "error", "error", {"message": str(e)})
        _finish(jid, {"ok": False, "error": str(e)})


def _safe(meta: dict) -> dict:
    out = {}
    for k, v in meta.items():
        if v is None:
            continue
        try:
            json.dumps(v)
            out[k] = v
        except Exception:
            out[k] = str(v)
    return out


def _read_dataframe(path: Path, nrows: int | None = None) -> pd.DataFrame:
    ext = path.suffix.lower()
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(path, nrows=nrows, dtype=str)
    return pd.read_csv(path, nrows=nrows, dtype=str)


def _row_count(path: Path) -> int:
    ext = path.suffix.lower()
    if ext in (".xlsx", ".xls"):
        return len(pd.read_excel(path, dtype=str))
    # fast csv line count
    with open(path, "rb") as f:
        return max(0, sum(1 for _ in f) - 1)


# ---- chunks viewer ----------------------------------------------------------
@app.route("/chunks")
def chunks_view():
    page = max(1, int(request.args.get("page", "1")))
    page_size = 50
    q = request.args.get("q", "").strip()
    priority = request.args.get("priority", "").strip()
    module = request.args.get("module", "").strip()

    client = store.get_client()
    info = store.collection_info(client, COLLECTION)
    if not info["exists"] or info["points"] == 0:
        return _render(EMPTY_DB_TPL, active="chunks", stages=INGEST_STAGES, title="Chunks")

    flt = {}
    if priority: flt["priority"] = priority
    if module:   flt["module"] = module

    # naive pagination: scroll page-1 times then read 1 page (small datasets ok)
    offset = None
    points = []
    next_off = None
    seen_pages = 0
    while seen_pages < page:
        points, next_off = store.iter_points(client, COLLECTION, limit=page_size,
                                             offset=offset, flt=flt or None)
        seen_pages += 1
        if seen_pages == page:
            break
        if next_off is None:
            points = []
            break
        offset = next_off

    # optional substring filter
    if q:
        ql = q.lower()
        points = [p for p in points if ql in (p.payload.get("text", "") or "").lower()]

    last_ids = set(_LAST_RETRIEVED.get("chunk_ids") or [])
    cards = []
    for p in points:
        pl = dict(p.payload or {})
        cid = pl.get("chunk_id") or str(p.id)
        cards.append({
            "id": cid,
            "is_retrieved": cid in last_ids,
            "row_index": pl.get("row_index"),
            "test_case_id": pl.get("test_case_id"),
            "jira_id": pl.get("jira_id"),
            "priority": pl.get("priority"),
            "module": pl.get("module"),
            "chunk_index": pl.get("chunk_index"),
            "total_chunks": pl.get("total_chunks"),
            "text": pl.get("text", ""),
            "meta": _safe(pl),
        })

    return _render(
        CHUNKS_TPL,
        active="chunks",
        stages=INGEST_STAGES,
        title="Chunks",
        cards=cards,
        page=page,
        page_size=page_size,
        total_points=info["points"],
        has_next=next_off is not None,
        q=q,
        priority=priority,
        module=module,
        last_count=len(last_ids),
    )


# ---- chat -------------------------------------------------------------------
_CHAT_HISTORY: list[dict] = []  # turns: {"role", "content", "details"?}


@app.route("/chat", methods=["GET"])
def chat():
    client = store.get_client()
    info = store.collection_info(client, COLLECTION)
    return _render(
        CHAT_TPL,
        active="chat",
        stages=CHAT_STAGES,
        title="Chat",
        history=_CHAT_HISTORY,
        collection_points=info.get("points", 0),
        rewrite_default=("checked" if REWRITE_ENABLED else ""),
        rerank_default="checked",
        top_n=TOP_N_HYBRID,
        top_k=TOP_K_RERANK,
    )


@app.route("/chat", methods=["POST"])
def chat_start():
    question = (request.form.get("question") or "").strip()
    if not question:
        return jsonify({"error": "empty question"}), 400
    use_rewrite = request.form.get("rewrite") == "on"
    use_rerank = request.form.get("rerank") == "on"
    top_n = int(request.form.get("top_n") or TOP_N_HYBRID)
    top_k = int(request.form.get("top_k") or TOP_K_RERANK)
    jid = _new_job()
    t = threading.Thread(
        target=_chat_job,
        args=(jid, question, use_rewrite, use_rerank, top_n, top_k),
        daemon=True,
    )
    t.start()
    return jsonify({"job": jid})


@app.route("/chat/stream")
def chat_stream():
    jid = request.args.get("job", "")
    return Response(_stream(jid), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _chat_job(jid, question, use_rewrite, use_rerank, top_n, top_k):
    try:
        client = store.get_client()
        info = store.collection_info(client, COLLECTION)
        if not info["exists"] or info["points"] == 0:
            raise RuntimeError("Collection is empty - ingest data first via /upload.")

        _emit(jid, "question", "done", {"question": question, "mode": llm.detect_mode(question)})

        # rewrite
        if use_rewrite:
            _emit(jid, "rewrite", "active")
            queries_text = llm.rewrite_query(question, n=2)
            _emit(jid, "rewrite", "done", {"queries": queries_text})
        else:
            queries_text = [question]
            _emit(jid, "rewrite", "skipped", {"queries": queries_text})

        # embed
        _emit(jid, "embed", "active")
        queries = []
        sample_emb = []
        for qt in queries_text:
            v = embeddings.embed_query(qt)
            queries.append({"text": qt, "dense": v["dense"], "sparse": v["sparse"]})
            sp_terms = embeddings.decode_sparse_terms(v["sparse"], k=5)
            sample_emb.append({
                "text": qt,
                "dense_preview": [round(float(x), 4) for x in v["dense"][:8].tolist()],
                "sparse_top": [{"term": t, "weight": round(w, 4)} for t, w in sp_terms],
            })
        _emit(jid, "embed", "done", {"queries": sample_emb})

        # hybrid retrieval (split into two visual stages)
        _emit(jid, "dense", "active")
        result = retrieve.hybrid_search(client, COLLECTION, queries, top_n=top_n)
        # produce per-query dense / sparse summaries
        per_q_dense = []
        per_q_sparse = []
        for pq in result["per_query"]:
            per_q_dense.append({
                "text": pq["text"],
                "hits": [{"chunk_id": h["chunk_id"], "score": round(h["score"], 4),
                          "test_case_id": (h["payload"] or {}).get("test_case_id"),
                          "module": (h["payload"] or {}).get("module")}
                         for h in pq["dense_hits"]],
            })
            per_q_sparse.append({
                "text": pq["text"],
                "hits": [{"chunk_id": h["chunk_id"], "score": round(h["score"], 4),
                          "test_case_id": (h["payload"] or {}).get("test_case_id"),
                          "module": (h["payload"] or {}).get("module")}
                         for h in pq["sparse_hits"]],
            })
        _emit(jid, "dense", "done", {"per_query": per_q_dense, "limit": top_n})
        _emit(jid, "sparse", "done", {"per_query": per_q_sparse, "limit": top_n})

        # fuse
        _emit(jid, "fuse", "active")
        fused = result["fused"]
        fused_view = []
        for i, f in enumerate(fused, start=1):
            pl = f.get("payload") or {}
            fused_view.append({
                "rank": i,
                "chunk_id": f["chunk_id"],
                "rrf_score": f["rrf_score"],
                "sources": f["sources"],
                "test_case_id": pl.get("test_case_id"),
                "module": pl.get("module"),
                "text_preview": (pl.get("text") or "")[:200],
            })
        _emit(jid, "fuse", "done", {"fused": fused_view[:top_n], "total": len(fused), "k": RRF_K})

        # rerank
        if use_rerank and fused:
            _emit(jid, "rerank", "active")
            top_for_rerank = fused[:top_n]
            reranked = rerank.rerank(question, top_for_rerank, top_k=top_k)
            rerank_view = []
            for r in reranked:
                pl = r.get("payload") or {}
                rerank_view.append({
                    "fused_rank": r.get("fused_rank"),
                    "rerank_rank": r.get("rerank_rank"),
                    "rerank_score": round(r.get("rerank_score", 0.0), 4),
                    "chunk_id": r["chunk_id"],
                    "test_case_id": pl.get("test_case_id"),
                    "module": pl.get("module"),
                    "text_preview": (pl.get("text") or "")[:200],
                })
            final = reranked
            _emit(jid, "rerank", "done", {"reranked": rerank_view, "top_k": top_k})
        else:
            final = fused[:top_k]
            _emit(jid, "rerank", "skipped", {"top_k": top_k})

        # generate
        _emit(jid, "generate", "active")
        mode = llm.detect_mode(question)
        result_llm = llm.ask_groq(question, final, mode=mode)
        _emit(jid, "generate", "done", {
            "answer": result_llm["answer"],
            "mode": mode,
        })

        # remember which chunks for /chunks viewer
        _LAST_RETRIEVED["chunk_ids"] = [f["chunk_id"] for f in final]

        # save turn
        retrieved_view = []
        for i, f in enumerate(final, start=1):
            pl = f.get("payload") or {}
            retrieved_view.append({
                "label": i,
                "chunk_id": f["chunk_id"],
                "test_case_id": pl.get("test_case_id"),
                "module": pl.get("module"),
                "priority": pl.get("priority"),
                "text": pl.get("text", ""),
            })

        _CHAT_HISTORY.append({"role": "user", "content": question})
        _CHAT_HISTORY.append({
            "role": "assistant",
            "content": result_llm["answer"],
            "mode": mode,
            "retrieved": retrieved_view,
        })
        _finish(jid, {
            "ok": True,
            "answer": result_llm["answer"],
            "mode": mode,
            "retrieved": retrieved_view,
        })
    except Exception as e:
        _emit(jid, "error", "error", {"message": str(e)})
        _finish(jid, {"ok": False, "error": str(e)})


@app.route("/api/collection-info")
def api_collection_info():
    client = store.get_client()
    return jsonify(store.collection_info(client, COLLECTION))


# =========================================================================
# Templates
# =========================================================================

UPLOAD_TPL = """
<h1>Stage 1 - Ingest your test cases</h1>
<p class="muted">Upload a CSV or Excel file of test cases. We'll show you how rows turn into chunks, how chunks turn into vectors, and how they land in Qdrant - every step.</p>

{% if error %}<div class="card" style="border-color:var(--bad)"><strong>Error:</strong> {{error}}</div>{% endif %}

<form method="post" enctype="multipart/form-data">
  <label class="dropzone" id="dz">
    <input type="file" name="file" id="file" accept=".csv,.xlsx,.xls" style="display:none" required>
    <div><strong>Drop a CSV / XLSX here</strong>, or click to choose.</div>
    <div class="hint">Up to 200 MB &middot; CSV, XLSX, XLS</div>
    <div id="fname" class="small" style="margin-top:10px;"></div>
  </label>
  <div style="margin-top:14px"><button class="btn" type="submit">Upload &amp; preview</button></div>
</form>

<script>
  const dz = document.getElementById('dz');
  const fi = document.getElementById('file');
  const fn = document.getElementById('fname');
  dz.addEventListener('click', () => fi.click());
  fi.addEventListener('change', () => { if (fi.files[0]) fn.textContent = fi.files[0].name; });
  ['dragover','dragenter'].forEach(ev => dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.add('hover'); }));
  ['dragleave','drop'].forEach(ev => dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.remove('hover'); }));
  dz.addEventListener('drop', e => { fi.files = e.dataTransfer.files; if (fi.files[0]) fn.textContent = fi.files[0].name; });
</script>
"""

INGEST_TPL = """
<h1>Preview &amp; configure ingestion</h1>
<p class="muted">File: <span class="mono">{{file}}</span> &middot; <strong>{{full_count}} rows</strong> &middot; {{cols|length}} columns</p>

<div class="card">
  <h3>First 5 rows</h3>
  <div class="table-card">{{ head_html|safe }}</div>
</div>

<form id="ingest-form" method="post" action="/ingest">
  <input type="hidden" name="file" value="{{file}}">
  <div class="card">
    <h3>1. Pick text columns</h3>
    <p class="muted small">These columns are concatenated (with field labels) and embedded.</p>
    <div class="checks">
      {% for c in cols %}
        <label><input type="checkbox" name="text_cols" value="{{c}}" {% if c in text_pre %}checked{% endif %}> {{c}}</label>
      {% endfor %}
    </div>
  </div>
  <div class="card">
    <h3>2. Pick metadata columns</h3>
    <p class="muted small">Stored alongside each chunk for filtering &amp; display (jira id, priority, module, etc.).</p>
    <div class="checks">
      {% for c in cols %}
        <label><input type="checkbox" name="meta_cols" value="{{c}}" {% if c in meta_pre %}checked{% endif %}> {{c}}</label>
      {% endfor %}
    </div>
  </div>
  <div class="card">
    <h3>3. Tunables</h3>
    <div class="form-grid">
      <div><label>Chunk size (chars)</label><input type="number" name="chunk_size" value="{{chunk_size}}" min="200" max="4000"></div>
      <div><label>Chunk overlap (chars)</label><input type="number" name="chunk_overlap" value="{{chunk_overlap}}" min="0" max="800"></div>
    </div>
    <label style="margin-top:10px;display:inline-flex;gap:6px;align-items:center;">
      <input type="checkbox" name="recreate"> Drop &amp; recreate the collection (start fresh)
    </label>
  </div>
  <button class="btn" type="submit">Run ingestion</button>
</form>

<div id="ingest-out" style="display:none;margin-top:18px"></div>

<style>
.preview-table th, .preview-table td { border-bottom: 1px solid var(--line-2); padding: 6px 10px; font-size:12.5px; }
.preview-table th { color:var(--muted); text-transform:uppercase; font-size:11px; }
</style>

<script>
const form = document.getElementById('ingest-form');
const out  = document.getElementById('ingest-out');

function setStage(key, status, meta) {
  const el = document.querySelector(`.stage[data-stage="${key}"]`);
  if (!el) return;
  el.classList.remove('active','done','error','skipped');
  if (status) el.classList.add(status);
  if (meta != null) {
    const m = el.querySelector('.stage-meta');
    if (m) m.textContent = meta;
  }
}

function escape(s){ return (s==null?'':String(s)).replace(/[&<>]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c])); }

function renderEvent(e) {
  const p = e.payload || {};
  const div = document.createElement('div');
  div.className = 'card';
  if (e.stage === 'read' && e.status === 'done') {
    setStage('read','done', `${p.rows} rows · ${p.columns.length} columns`);
    div.innerHTML = `<h3>Read file</h3>
      <div class="kv"><span class="k">Rows</span><span class="v">${p.rows}</span></div>
      &nbsp;&nbsp;<div class="kv"><span class="k">Columns</span><span class="v">${p.columns.join(', ')}</span></div>`;
  } else if (e.stage === 'build' && e.status === 'done') {
    setStage('build','done', `${p.sample_docs.length} samples`);
    div.innerHTML = `<h3>Assembled documents (first 3)</h3>` +
      p.sample_docs.map((d,i)=>`<details ${i===0?'open':''}><summary>Doc ${i+1} (${d.length} chars)</summary><pre class="chunk-text">${escape(d)}</pre></details>`).join('');
  } else if (e.stage === 'chunk' && e.status === 'done') {
    setStage('chunk','done', `${p.total_chunks} chunks · avg ${p.avg_chars} chars`);
    let hist = '<table><tr><th>Chunks per row</th><th>Number of rows</th></tr>';
    p.histogram.forEach(([k,v]) => hist += `<tr><td>${k}</td><td>${v}</td></tr>`);
    hist += '</table>';
    let samples = p.sample_chunks.map((c,i)=>{
      const t = c.text;
      const o = c.overlap_prefix_len|0;
      const inner = (o>0
        ? `<span class="ovl">${escape(t.slice(0,o))}</span>${escape(t.slice(o))}`
        : escape(t));
      return `<div class="chunk-card">
        <div class="chunk-head">
          <span class="badge">${escape(c.id)}</span>
          <span class="pill">row ${escape(c.metadata.row_index)} · chunk ${escape(c.metadata.chunk_index)}/${escape(c.metadata.total_chunks-1)}</span>
          ${o>0 ? `<span class="badge muted">overlap prefix: ${o} chars</span>` : ''}
          <span class="muted small">${t.length} chars</span>
        </div>
        <pre class="chunk-text">${inner}</pre>
      </div>`;
    }).join('');
    div.innerHTML = `<h3>Chunking</h3>
      <div class="card-row">
        <div class="kv"><span class="k">Total chunks</span><span class="v">${p.total_chunks}</span></div>
        <div class="kv"><span class="k">Rows w/ chunks</span><span class="v">${p.rows_with_chunks}</span></div>
        <div class="kv"><span class="k">Avg chars</span><span class="v">${p.avg_chars}</span></div>
        <div class="kv"><span class="k">Min</span><span class="v">${p.min_chars}</span></div>
        <div class="kv"><span class="k">Max</span><span class="v">${p.max_chars}</span></div>
        <div class="kv"><span class="k">Size/Overlap</span><span class="v">${p.chunk_size}/${p.chunk_overlap}</span></div>
      </div>
      <details><summary>Chunks-per-row histogram</summary>${hist}</details>
      <h3>First 3 chunks (overlap prefix highlighted)</h3>${samples}`;
  } else if (e.stage === 'embed') {
    if (e.status === 'active') {
      const pct = p.total ? Math.round(100*p.done/p.total) : 0;
      setStage('embed','active', `${p.done}/${p.total} (${pct}%)`);
      let bar = document.getElementById('embed-bar');
      if (!bar) {
        const c = document.createElement('div');
        c.className = 'card'; c.id = 'embed-card';
        c.innerHTML = `<h3>Embedding (bge-m3 · dense + sparse)</h3>
          <div class="progress"><div id="embed-bar"></div></div>
          <div id="embed-status" class="muted small" style="margin-top:6px"></div>`;
        out.appendChild(c);
        bar = document.getElementById('embed-bar');
      }
      bar.style.width = pct+'%';
      document.getElementById('embed-status').textContent = `${p.done} / ${p.total} chunks embedded`;
      return; // don't append a new card
    }
    if (e.status === 'done') {
      setStage('embed','done', `${p.total} chunks · ${p.dense_dim}d dense`);
      let samples = p.sample.map(s=>{
        const sp = s.sparse_top.map(t=>`<span class="pill mono">${escape(t.term)} (${t.weight})</span>`).join(' ');
        return `<div class="chunk-card">
          <div class="chunk-head"><span class="badge">${escape(s.chunk_id)}</span>
            <span class="muted small">dense: ${s.dense_dim} dims</span></div>
          <div class="kv"><span class="k">dense[0:8]</span><span class="v">[${s.dense_preview.join(', ')}]</span></div>
          <div style="margin-top:6px"><span class="muted small">sparse top-5:</span> ${sp}</div>
        </div>`;
      }).join('');
      div.innerHTML = `<h3>Embedding done</h3>
        <div class="card-row">
          <div class="kv"><span class="k">Total</span><span class="v">${p.total}</span></div>
          <div class="kv"><span class="k">Dense dim</span><span class="v">${p.dense_dim}</span></div>
          <div class="kv"><span class="k">Sparse avg nnz</span><span class="v">${p.sparse_avg_nnz}</span></div>
        </div>${samples}`;
    }
  } else if (e.stage === 'index' && e.status === 'done') {
    setStage('index','done', `${p.points} points`);
    div.innerHTML = `<h3>Indexed in Qdrant</h3>
      <div class="card-row">
        <div class="kv"><span class="k">Collection</span><span class="v">${escape(p.collection)}</span></div>
        <div class="kv"><span class="k">Written</span><span class="v">${p.written}</span></div>
        <div class="kv"><span class="k">Total points</span><span class="v">${p.points}</span></div>
      </div>
      <p style="margin-top:10px">${p.dashboard ? `<a href="${p.dashboard}" target="_blank">Open Qdrant dashboard &rarr;</a> &middot; ` : ''}<a href="/chunks">Browse chunks</a> &middot; <a href="/chat">Start chat</a></p>`;
  } else if (e.stage === 'error') {
    setStage('read','error'); setStage('build','error'); setStage('chunk','error');
    setStage('embed','error'); setStage('index','error');
    div.innerHTML = `<h3 style="color:var(--bad)">Error</h3><pre>${escape(p.message)}</pre>`;
  } else if (e.status === 'active') {
    setStage(e.stage,'active');
    return;
  } else {
    return;
  }
  out.appendChild(div);
}

form.addEventListener('submit', async ev => {
  ev.preventDefault();
  out.style.display = 'block';
  out.innerHTML = '';
  ['read','build','chunk','embed','index'].forEach(k => setStage(k,'',''));
  const fd = new FormData(form);
  const r = await fetch('/ingest', {method:'POST', body: fd});
  const j = await r.json();
  if (!j.job) { out.innerHTML = '<div class="card">Error: '+(j.error||'failed')+'</div>'; return; }
  const es = new EventSource('/ingest/stream?job=' + j.job);
  es.onmessage = e => { try { renderEvent(JSON.parse(e.data)); } catch(_){} };
  es.addEventListener('done', () => es.close());
  es.onerror = () => es.close();
});
</script>
"""

EMPTY_DB_TPL = """
<h1>Chunks viewer</h1>
<div class="card">
  <p>The Qdrant collection is empty. Upload a CSV or Excel file to ingest test cases first.</p>
  <p><a class="btn" href="/upload">Go to upload &rarr;</a></p>
</div>
"""

CHUNKS_TPL = """
<h1>Chunks in Qdrant</h1>
<p class="muted">Total points: <strong>{{total_points}}</strong>. Showing page <strong>{{page}}</strong> ({{page_size}} per page).
{% if last_count %} Highlighted in coral = used in your last chat answer ({{last_count}} chunks).{% endif %}</p>

<form method="get" class="card">
  <div class="form-grid">
    <div><label>Search text (substring)</label><input type="search" name="q" value="{{q}}" placeholder="e.g. heatmap, billing"></div>
    <div><label>Priority</label>
      <select name="priority"><option value=""></option>
      {% for p in ['P0','P1','P2','P3'] %}<option value="{{p}}" {% if p==priority %}selected{% endif %}>{{p}}</option>{% endfor %}
      </select>
    </div>
    <div><label>Module</label><input type="text" name="module" value="{{module}}" placeholder="e.g. AB Testing"></div>
    <div style="align-self:end"><button class="btn" type="submit">Filter</button>
      <a class="btn secondary" href="/chunks" style="margin-left:6px">Clear</a></div>
  </div>
</form>

{% for c in cards %}
  <div class="chunk-card {% if c.is_retrieved %}retrieved{% endif %}">
    <div class="chunk-head">
      <span class="badge">{{c.id}}</span>
      {% if c.test_case_id %}<span class="pill mono">{{c.test_case_id}}</span>{% endif %}
      {% if c.jira_id %}<span class="pill mono">{{c.jira_id}}</span>{% endif %}
      {% if c.priority %}<span class="pill">{{c.priority}}</span>{% endif %}
      {% if c.module %}<span class="pill">{{c.module}}</span>{% endif %}
      <span class="muted small">{{c.text|length}} chars</span>
      {% if c.is_retrieved %}<span class="badge good">RETRIEVED</span>{% endif %}
    </div>
    <pre class="chunk-text">{{c.text}}</pre>
  </div>
{% endfor %}

<div class="flex" style="margin-top:18px">
  {% if page > 1 %}
    <a class="btn secondary" href="?page={{page-1}}&q={{q}}&priority={{priority}}&module={{module}}">&larr; Prev</a>
  {% endif %}
  {% if has_next %}
    <a class="btn" href="?page={{page+1}}&q={{q}}&priority={{priority}}&module={{module}}">Next &rarr;</a>
  {% endif %}
</div>
"""

CHAT_TPL = """
<h1>Stage 2 - Ask the explorer</h1>
<p class="muted">Type a question. The left panel will light up step-by-step as the pipeline runs.
Type <em>"Create a new test case for JIRA VWO-1234..."</em> to see the generate mode.</p>

<div class="card flex">
  <div class="kv"><span class="k">Collection</span><span class="v">{{collection_points}} points</span></div>
  <div class="kv"><span class="k">Top-N hybrid</span><span class="v">{{top_n}}</span></div>
  <div class="kv"><span class="k">Top-K rerank</span><span class="v">{{top_k}}</span></div>
</div>

<div class="chat-thread" id="thread">
  {% for turn in history %}
    <div class="bubble {{turn.role}}">{{turn.content}}</div>
  {% endfor %}
</div>

<form id="chat-form">
  <textarea id="q" name="question" placeholder="Ask about your test cases, or 'create a new test case for VWO-1234'..." required></textarea>
  <div class="flex" style="margin-top:10px">
    <label class="checks-inline"><input type="checkbox" name="rewrite" {{rewrite_default}}> Query rewrite</label>
    <label class="checks-inline"><input type="checkbox" name="rerank"  {{rerank_default}}> Re-ranker</label>
    <label class="kv"><span class="k">top-N</span><input type="number" name="top_n" value="{{top_n}}" min="5" max="50" style="width:70px"></label>
    <label class="kv"><span class="k">top-K</span><input type="number" name="top_k" value="{{top_k}}" min="1" max="10" style="width:70px"></label>
    <span class="spacer"></span>
    <button class="btn" type="submit">Ask</button>
  </div>
</form>

<div id="result" style="margin-top:18px"></div>

<script>
const thread = document.getElementById('thread');
const result = document.getElementById('result');
const form = document.getElementById('chat-form');

function setStage(key, status, meta) {
  const el = document.querySelector(`.stage[data-stage="${key}"]`);
  if (!el) return;
  el.classList.remove('active','done','error','skipped');
  if (status) el.classList.add(status);
  if (meta != null) {
    const m = el.querySelector('.stage-meta');
    if (m) m.textContent = meta;
  }
}
function escape(s){ return (s==null?'':String(s)).replace(/[&<>]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c])); }

function bubble(role, html) {
  const d = document.createElement('div');
  d.className = 'bubble ' + role;
  d.innerHTML = html;
  thread.appendChild(d);
  d.scrollIntoView({behavior:'smooth', block:'end'});
  return d;
}

function renderHits(hits) {
  return `<table><tr><th>#</th><th>chunk</th><th>tc</th><th>module</th><th>score</th></tr>` +
    hits.map((h,i)=>`<tr><td>${i+1}</td><td class="mono">${escape(h.chunk_id)}</td><td>${escape(h.test_case_id||'')}</td><td>${escape(h.module||'')}</td><td>${h.score}</td></tr>`).join('') + `</table>`;
}

function renderEvent(e) {
  const p = e.payload || {};
  const stage = e.stage;
  if (stage === 'question') {
    setStage('question','done', `mode=${p.mode}`);
    bubble('user', escape(p.question));
    return;
  }
  if (stage === 'rewrite') {
    if (e.status === 'skipped') { setStage('rewrite','skipped','off'); return; }
    setStage('rewrite','done', `${p.queries.length} queries`);
    const c = document.createElement('div'); c.className='card';
    c.innerHTML = `<h3>Query rewrites</h3>` + p.queries.map((q,i)=>`<div class="pill mono" style="margin:3px">Q${i+1}: ${escape(q)}</div>`).join('');
    result.appendChild(c);
    return;
  }
  if (stage === 'embed' && e.status === 'done') {
    setStage('embed','done', `${p.queries.length} queries embedded`);
    const c = document.createElement('div'); c.className='card';
    c.innerHTML = `<h3>Embedding queries (bge-m3)</h3>` + p.queries.map(q => {
      const sp = q.sparse_top.map(t=>`<span class="pill mono">${escape(t.term)} (${t.weight})</span>`).join(' ');
      return `<div class="chunk-card">
        <div class="muted small">${escape(q.text)}</div>
        <div class="kv"><span class="k">dense[0:8]</span><span class="v">[${q.dense_preview.join(', ')}]</span></div>
        <div style="margin-top:6px"><span class="muted small">sparse top-5:</span> ${sp}</div></div>`;
    }).join('');
    result.appendChild(c);
    return;
  }
  if (stage === 'dense' && e.status === 'done') {
    setStage('dense','done', `${p.per_query.reduce((a,b)=>a+b.hits.length,0)} hits`);
    const c = document.createElement('div'); c.className='card';
    c.innerHTML = `<h3>Dense search (top ${p.limit} per query)</h3>` +
      p.per_query.map(q => `<details ${q===p.per_query[0]?'open':''}><summary>${escape(q.text)} - ${q.hits.length} hits</summary>${renderHits(q.hits)}</details>`).join('');
    result.appendChild(c);
    return;
  }
  if (stage === 'sparse' && e.status === 'done') {
    setStage('sparse','done', `${p.per_query.reduce((a,b)=>a+b.hits.length,0)} hits`);
    const c = document.createElement('div'); c.className='card';
    c.innerHTML = `<h3>Sparse search - BM25-like (top ${p.limit} per query)</h3>` +
      p.per_query.map(q => `<details ${q===p.per_query[0]?'open':''}><summary>${escape(q.text)} - ${q.hits.length} hits</summary>${renderHits(q.hits)}</details>`).join('');
    result.appendChild(c);
    return;
  }
  if (stage === 'fuse' && e.status === 'done') {
    setStage('fuse','done', `${p.fused.length} fused`);
    const c = document.createElement('div'); c.className='card';
    let rows = `<table><tr><th>#</th><th>chunk</th><th>tc</th><th>module</th><th>RRF</th><th>per-list ranks</th><th>preview</th></tr>`;
    p.fused.forEach(f => {
      rows += `<tr><td>${f.rank}</td><td class="mono">${escape(f.chunk_id)}</td><td>${escape(f.test_case_id||'')}</td><td>${escape(f.module||'')}</td><td>${f.rrf_score}</td><td class="mono">[${f.sources.join(',')}]</td><td>${escape(f.text_preview)}</td></tr>`;
    });
    rows += '</table>';
    c.innerHTML = `<h3>RRF fused (k=${p.k})</h3><div class="muted small">A position of 0 means the chunk wasn't in that list.</div>${rows}`;
    result.appendChild(c);
    return;
  }
  if (stage === 'rerank') {
    if (e.status === 'skipped') { setStage('rerank','skipped','off'); return; }
    setStage('rerank','done', `${p.reranked.length} kept`);
    const c = document.createElement('div'); c.className='card';
    let rows = `<table><tr><th>fused #</th><th>rerank #</th><th>score</th><th>chunk</th><th>tc</th><th>module</th><th>preview</th></tr>`;
    p.reranked.forEach(r => {
      rows += `<tr><td>${r.fused_rank}</td><td><strong>${r.rerank_rank}</strong></td><td>${r.rerank_score}</td><td class="mono">${escape(r.chunk_id)}</td><td>${escape(r.test_case_id||'')}</td><td>${escape(r.module||'')}</td><td>${escape(r.text_preview)}</td></tr>`;
    });
    rows += '</table>';
    c.innerHTML = `<h3>Cross-encoder rerank (top-${p.top_k})</h3>${rows}`;
    result.appendChild(c);
    return;
  }
  if (stage === 'generate' && e.status === 'done') {
    setStage('generate','done', `mode=${p.mode}`);
    return;
  }
  if (stage === 'error') {
    setStage(stage,'error');
    const c = document.createElement('div'); c.className='card';
    c.innerHTML = `<h3 style="color:var(--bad)">Error</h3><pre>${escape(p.message)}</pre>`;
    result.appendChild(c);
    return;
  }
  if (e.status === 'active') setStage(stage,'active');
}

function renderRetrieved(retrieved) {
  return `<details style="margin-top:8px"><summary>Show ${retrieved.length} retrieved chunks</summary>` +
    retrieved.map(r => `<div class="chunk-card retrieved">
      <div class="chunk-head">
        <span class="badge">[Chunk ${r.label}]</span>
        <span class="pill mono">${escape(r.chunk_id)}</span>
        ${r.test_case_id?`<span class="pill">${escape(r.test_case_id)}</span>`:''}
        ${r.module?`<span class="pill">${escape(r.module)}</span>`:''}
        ${r.priority?`<span class="pill">${escape(r.priority)}</span>`:''}
      </div><pre class="chunk-text">${escape(r.text)}</pre></div>`).join('') +
    `</details>`;
}

form.addEventListener('submit', async ev => {
  ev.preventDefault();
  result.innerHTML = '';
  ['question','rewrite','embed','dense','sparse','fuse','rerank','generate'].forEach(k=>setStage(k,'',''));
  const fd = new FormData(form);
  const r = await fetch('/chat', {method:'POST', body: fd});
  const j = await r.json();
  if (!j.job) { bubble('assistant', 'Error: '+(j.error||'failed')); return; }
  const es = new EventSource('/chat/stream?job='+j.job);
  let assistantBubble = null;
  es.onmessage = e => { try { renderEvent(JSON.parse(e.data)); } catch(_){} };
  es.addEventListener('done', e => {
    es.close();
    try {
      const r = JSON.parse(e.data);
      if (r.ok) {
        const html = `<div>${escape(r.answer).replace(/\\n/g,'<br>')}</div>${renderRetrieved(r.retrieved)}`;
        bubble('assistant', html);
        document.getElementById('q').value = '';
      } else {
        bubble('assistant', 'Error: '+escape(r.error||''));
      }
    } catch(_) {}
  });
  es.onerror = () => es.close();
});
</script>
"""

# ---- entrypoint -------------------------------------------------------------
if __name__ == "__main__":
    print(f"Groq model      : {GROQ_MODEL}")
    print(f"Qdrant URL      : {QDRANT_URL}")
    print(f"Collection      : {COLLECTION}")
    print(f"Open http://127.0.0.1:{PORT}")
    app.run(host="127.0.0.1", port=PORT, debug=False, threaded=True)
