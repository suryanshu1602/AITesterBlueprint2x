# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project shape

QA Copilot — Chapter 9 of the AI Tester Blueprint 2x course. Multi-source RAG over five
heterogeneous QA artifacts: Selenium Java framework, Playwright TS framework, VWO test
case CSV, VWO PDFs (PRDs), and JIRA bug markdown exports. Stack:

- **Backend**: FastAPI · Qdrant (file-store by default) · BGE-M3 hybrid embeddings · BGE-Reranker-v2-m3 · Groq `openai/gpt-oss-120b`.
- **Frontend**: Vite + React + TypeScript + Tailwind + react-router-dom + react-markdown + lucide-react. Three pages: `/` (Chat), `/explorer` (RAG Explorer debugger), `/status` (health + ingest controls).
- **KT page**: standalone HTML in `KT/index.html` (Mermaid diagram + component breakdown). Linked from the React header.

## Run commands

```bash
# Clone source repos into data/ (gitignored)
git clone https://github.com/PramodDutta/ATB14xSeleniumAdvanceFrameworks data/selenium_repo
git clone https://github.com/PramodDutta/Advance-Playwright-Framework  data/playwright_repo

# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env   # set GROQ_API_KEY
python -m backend.ingest.ingest_all                  # all 5 pipelines
python -m backend.ingest.ingest_testcases            # one pipeline
python -m backend.ingest.ingest_all --recreate       # drop+rebuild collections
uvicorn backend.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev            # http://localhost:5173

# Health probe
curl http://localhost:8000/api/health
```

There is no test suite for this chapter. The "verification" loop is: ingest → check
`/api/health` shows non-zero counts in all 5 collections → ask one smoke question per
collection in the UI → verify citations and source cards line up.

## Architecture (the part you need to read multiple files to grasp)

### 5-collection Qdrant store with named vectors

Every collection (`selenium_code`, `playwright_code`, `vwo_testcases`, `vwo_docs`, `vwo_bugs`)
uses the *same* schema: a `dense` named vector (1024d cosine) and a `sparse` named vector,
both produced by a single BGE-M3 forward pass per chunk. See `backend/lib/qdrant_store.py`
for the bootstrap and the `hybrid_search_collection` helper. The collection list is the
tuple `settings.COLLECTIONS` — that's the single source of truth (see "Adding a 6th source"
below).

### Query path (read this top to bottom)

1. `backend/lib/retriever.py::retrieve_with_trace` is the entry point. It runs:
   1. Query rewrite (`rewrite_query` — Groq, conditioned on the last `HISTORY_TURNS` turns).
   2. Router decision (`backend/lib/router.py::route` — Groq JSON-mode classifier, returns 1–2 collections + reason). UI can override via `forced_collections`.
   3. Embed the rewritten query (`embeddings.embed_query` returns dense + sparse).
   4. Per selected collection: dense top-K + sparse top-K → RRF fuse (k=60).
   5. Cross-encoder rerank top-12 → top-4 (`backend/lib/reranker.py`).
2. `retrieve_with_trace` returns the final `context_blocks` *and* every intermediate stage
   (per-collection hits, fused, rerank). This dual purpose is intentional — the same
   function powers `/api/chat` (uses just `context_blocks`) and `/api/explore` (returns the whole trace to the UI).
3. `backend/main.py::chat` builds the user message (`<doc id="N" source="…">…</doc>` blocks)
   and streams tokens back over SSE with three event types: `meta`, `sources`, `token`,
   `done`.

### Frontend talks to backend via SSE for chat, plain JSON for explore

`frontend/src/api/client.ts::chatStream` parses the SSE stream by splitting on `\n\n`,
then dispatches handlers per event. The `Explorer` page calls `/api/explore` instead and
gets the full `Trace` object in one response — no streaming, because the trace structure
matters more than time-to-first-token for debugging.

`MarkdownAnswer.tsx` rewrites `[N]` tokens in the answer to `<cite>N</cite>` chips that
scroll the matching `#source-N` card into view.

### Adding a 6th source

Three steps, in this order:
1. Add an ingest module in `backend/ingest/` that produces chunks `{id, text, metadata}`
   and calls `_runner.embed_and_upsert("new_collection", chunks)`.
2. Add the collection name to the `COLLECTIONS` tuple in `backend/lib/settings.py`.
3. Add a one-line description to `backend/lib/prompts.py::ROUTER_SYSTEM` so the router
   knows when to pick it. Optionally add a heuristic hint to `router.heuristic_hint`.

The frontend `SourceFilter` reads collection names from a hardcoded list in
`frontend/src/components/SourceFilter.tsx` — update it there too.

## Key data shapes (per-collection chunk payloads)

| Collection | id pattern | distinctive metadata |
|---|---|---|
| `selenium_code` | `path:start-end:kind:symbol` | `language=java`, `package`, `kind ∈ {class, interface, enum, method, constructor}`, `symbol`, `qualified` |
| `playwright_code` | `path:start-end:kind:symbol` | `language=typescript`, `kind ∈ {function, method, class, test}`, `test_title` for `test()` calls |
| `vwo_testcases` | `r{row}-c{idx}` | `test_case_id`, `jira_id`, `module`, `priority`, `severity`, `labels`, `sprint`, `status`, `owner`, `test_type` |
| `vwo_docs` | `{stem}-p{page}-c{idx}` | `doc_title`, `page`, `kind=pdf_page` |
| `vwo_bugs` | `jira-{id}-c{idx}` | `jira_id`, `summary`, `status`, `priority`, `reporter`, `created`, `updated`, `kind=jira_bug` |

Common to all: `chunk_id`, `text`, `collection`, `source_file` (where applicable).

## SSE event protocol (`/api/chat`)

```
event: meta      → { rewritten, router: {collections, reason}, timings_ms }
event: sources   → Source[]   (one per final reranked block)
event: token     → string     (incremental answer text, raw)
event: done      → ""
event: error     → string
```

Tokens may contain newlines; client splits on `\n\n` to delimit SSE frames, then re-joins
the inner `data:` lines.

## Reused libraries (this chapter ports patterns from Chapter 8)

- `Chapter_08_RAG/Advance_RAG_EXPLAIN/lib/embeddings.py` → `backend/lib/embeddings.py` (BGE-M3 dense+sparse)
- `Chapter_08_RAG/Advance_RAG_EXPLAIN/lib/chunking.py` → `backend/lib/chunking_text.py` (row-aware test-case chunker)
- `Chapter_08_RAG/Advance_RAG_EXPLAIN/lib/rerank.py` → `backend/lib/reranker.py` (BGE-Reranker-v2-m3)
- `Chapter_08_RAG/Advance_RAG_EXPLAIN/lib/store.py` → `backend/lib/qdrant_store.py` (extended for 5-collection bootstrap and per-collection RRF)

The Groq REST shape and prompt templates are adapted from `Advance_RAG_EXPLAIN/app.py`.

## Common pitfalls

- **Qdrant file-store is single-process**. If `uvicorn` is running and you launch
  `python -m backend.ingest.ingest_all` in another shell, the second process will block
  on the file lock. Either stop the server, or switch to HTTP mode by setting `QDRANT_URL`.
- **First BGE-M3 load downloads ~2GB** to `~/.cache/huggingface/`. Ingest looks frozen
  for 30–90 seconds the first time. Subsequent runs are fast.
- **tree-sitter wheels** for Java and TypeScript are pinned in `requirements.txt`. If
  the grammar version drifts, `chunk_repo` will silently produce zero chunks — check
  `iter_source_files` first to confirm files are even being seen.
- **Empty data dirs** are tolerated (ingest scripts log "empty/missing" and return zero
  counts) so partial setups still work. The router falls back to "all 5 collections" if
  the JSON parse fails.
- **`.env.example` is a template** — never commit a real `GROQ_API_KEY` value into it.
  Copy to `.env` (gitignored) before adding the key.

## Files to read when debugging

| Symptom | Start here |
|---|---|
| Wrong answer | `/explorer` UI → check router pick & rerank order |
| Zero chunks for a repo | `backend/lib/chunking_code.py::iter_source_files` (SKIP_DIRS, exts) |
| Embedder OOM / slow | `backend/lib/embeddings.py` (set `BGE_USE_FP16=0` for older CPUs) |
| Bad citations | `backend/lib/retriever.py::build_user_message` + `MarkdownAnswer.tsx` |
| Stream cuts off | `backend/lib/groq_client.py::stream` (`[DONE]` handling) |
| CORS errors | `backend/main.py` `CORSMiddleware` allows `*`; check Vite proxy if disabled |

## Glossary (project-specific terms)

- **Trace** — the structured object returned by `/api/explore` containing every pipeline stage. Frontend renders it as expandable stage cards.
- **Forced collections** — UI-driven override of the router. When set, the router stage is bypassed and the listed collections are used directly.
- **Generate mode** — alternate system prompt that asks the LLM to draft a *new* test case using retrieved chunks as style templates (vs. answering from them).
