Chapter 9 — QA Copilot: Multi-Source RAG Plan                                   
                                                                                 
 Context                                                                         
                                                                                 
 Build QA Copilot in Chapter_09_Project_QACopilot/ that lets a tester ask        
 natural-language questions and get cited answers grounded in 5 heterogeneous QA 
  artifacts:                                                                     
                                                                                 
 1. Selenium TestNG Java framework (clone of                                     
 PramodDutta/ATB14xSeleniumAdvanceFrameworks)                                    
 2. Playwright TS framework (clone of PramodDutta/Advance-Playwright-Framework)  
 3. VWO test case corpus (data/csv/testcases_vwo_100.csv, schema: id, jira_id,   
 summary, module, priority, severity, labels, preconditions, steps,              
 expected_result, test_type, owner, sprint, status)                              
 4. VWO product PDFs (PRDs/specs in data/pdf/)                                   
 5. VWO JIRA bug exports (markdown in data/md/)                                  
                                                                                 
 User answered design choices already (locked):                                  
 - Frontend: React + Vite + Tailwind (Chapter 7 style)                           
 - Backend: FastAPI                                                              
 - Vector DB: Qdrant + bge-m3 hybrid (dense+sparse) + bge-reranker-v2-m3    
 cross-encoder                                                               
 - LLM: Groq openai/gpt-oss-120b                                            
 - Collections: one per source, LLM intent-router picks 1–2 per query (5         
 collections total — adjusted from original 4 because md/ is JIRA bugs not       
 specs)                                                               
 - Code chunking: AST-aware via tree-sitter (Java + TS/JS)                       
 - PDF intake: PyMuPDF, skip empty (<50 chars), write skip report       
 - Chat: per-session multi-turn with history-condensing query rewriter
 - Citations: inline [1][2] with sidebar source cards (file:line / TC id / PDF
 page / JIRA id)                            
                                                                                 
 This chapter is the capstone for the RAG track and should match the repo's      
 pedagogical style: self-contained, runnable, README-explained, sharing patterns 
  with Chapter 8 Advance_RAG.                                                    
                                                                               
 Target directory layout                                                         
                                                        
 Chapter_09_Project_QACopilot/                                                 
 ├── README.md
 ├── CLAUDE.md                        # required by /init invocation
 ├── .env.example
 ├── .gitignore
 ├── data/                            # already created
 │   ├── selenium_repo/               # to clone
 │   ├── playwright_repo/             # to clone
 │   ├── csv/testcases_vwo_100.csv
 │   ├── pdf/*.pdf
 │   └── md/Bug_VWO_*.md
 ├── backend/
 │   ├── main.py                      # FastAPI app: /api/chat (SSE),
 /api/ingest/*, /api/health
 │   ├── requirements.txt
 │   ├── lib/
 │   │   ├── settings.py              # env loader
 │   │   ├── embeddings.py            # bge-m3 dense+sparse (port from Ch8
 Advance lib/)
 │   │   ├── reranker.py              # bge-reranker-v2-m3
 │   │   ├── qdrant_store.py          # 5 collections, hybrid upsert/search, RRF
  fusion
 │   │   ├── router.py                # Groq classifier → list[collection]
 │   │   ├── retriever.py             # query rewrite → route → multi-collection
  retrieve → rerank → top-k
 │   │   ├── prompts.py               # system prompts: router, query-rewrite,
 answer-with-citations
 │   │   ├── chunking_text.py         # row-aware (port from Ch8 Advance
 lib/chunking.py)
 │   │   ├── chunking_code.py         # tree-sitter-java +
 tree-sitter-typescript: function/class chunks
 │   │   └── chunking_md_pdf.py       # PyMuPDF + markdown header-aware splitter
 │   └── ingest/
 │       ├── ingest_selenium.py       # walks data/selenium_repo, AST-chunks
 .java
 │       ├── ingest_playwright.py     # walks data/playwright_repo, AST-chunks
 .ts/.js
 │       ├── ingest_testcases.py      # row-per-TC chunking from CSV
 │       ├── ingest_pdfs.py           # PyMuPDF, skip empty, write
 data/_skip_report.json
 │       ├── ingest_jira.py           # markdown JIRA bugs, parse header fields
 → metadata
 │       └── ingest_all.py            # orchestrator: runs all five
 ├── frontend/
 │   ├── package.json                 # vite + react + ts + tailwind + lucide
 │   ├── vite.config.ts               # proxy /api → http://localhost:8000
 │   ├── index.html
 │   └── src/
 │       ├── main.tsx
 │       ├── App.tsx                  # 3-pane: sidebar (sources/filters), chat,
  citation panel
 │       ├── components/
 │       │   ├── ChatPane.tsx         # SSE streaming, markdown render w/ inline
  [n] citation chips
 │       │   ├── SourcePanel.tsx      # expandable source cards
 (file/TC/PDF/JIRA)
 │       │   ├── SourceFilter.tsx     # per-collection toggle (overrides router
 if user wants)
 │       │   └── IngestStatus.tsx     # shows last ingest counts per collection
 │       ├── api/client.ts            # fetch + EventSource wrappers
 │       └── styles/index.css         # tailwind + minimal claude-css palette
 └── qdrant_data/                     # local Qdrant file store (gitignored)

 Five Qdrant collections

 Collection: selenium_code
 Source: data/selenium_repo/**/*.java
 Chunk strategy: tree-sitter-java; one chunk per method or top-level class
 Key metadata: repo, path, start_line, end_line, symbol, kind (method/class),
   annotations
 ────────────────────────────────────────
 Collection: playwright_code
 Source: data/playwright_repo/**/*.{ts,js}
 Chunk strategy: tree-sitter-typescript; one chunk per function/class/test block
 Key metadata: repo, path, start_line, end_line, symbol, kind, test_title
 ────────────────────────────────────────
 Collection: vwo_testcases
 Source: data/csv/testcases_vwo_100.csv
 Chunk strategy: row-aware (Ch8 Advance pattern)
 Key metadata: tc_id, jira_id, module, priority, severity, labels, sprint,
   status, owner, test_type
 ────────────────────────────────────────
 Collection: vwo_docs
 Source: data/pdf/*.pdf
 Chunk strategy: PyMuPDF page text → header-aware splitter ~800 chars / 120
   overlap
 Key metadata: doc_title, page, section, source_path
 ────────────────────────────────────────
 Collection: vwo_bugs
 Source: data/md/Bug_VWO_*.md
 Chunk strategy: parse JIRA header block → metadata; body as one chunk (or split

   if >1500 chars)
 Key metadata: jira_id, status, priority, reporter, assignee, labels, created,
   updated, summary

 All collections: vector_size=1024, hybrid (dense + sparse). RRF fusion at k=60,
  top-12 candidates, rerank → top-4 to LLM context.

 Query flow

 user query + last N turns
   → query_rewriter (Groq, condenses follow-ups to standalone query)
   → router (Groq, returns ["selenium_code", "vwo_testcases"] etc.)
   → retriever: parallel hybrid search across selected collections, RRF merge
   → reranker: bge-reranker-v2-m3 on top-12 → top-4
   → answer_prompt: system + tagged context blocks <doc id="1"
 source="...">…</doc>
   → Groq stream → SSE to frontend
   → frontend renders markdown; [n] tokens become clickable chips that scroll
 source panel

 Router is small/cheap; user can override via SourceFilter (force collections).

 Files to reuse (port, not copy verbatim)

 - Chapter_08_RAG/Advance_RAG_EXPLAIN/lib/embeddings.py — bge-m3 dual-vector
 encoder. Reuse as-is.
 - Chapter_08_RAG/Advance_RAG_EXPLAIN/lib/chunking.py — assemble_document +
 chunk_test_case. Use for vwo_testcases ingest.
 - Chapter_08_RAG/Advance_RAG_EXPLAIN/ingest.py — Qdrant collection bootstrap
 (named-vectors config), upsert pattern, payload shape. Pattern reused per
 collection.
 - Chapter_08_RAG/Advance_RAG_EXPLAIN/app.py — Groq client init, GROQ_MODEL env,
  system prompt structure. Port to FastAPI handler.
 - Chapter_08_RAG/Advance_RAG_EXPLAIN/static/claude.css — color tokens;
 translate to Tailwind theme extension.
 - Chapter_07_AI_Agent_VIBE_Coding/backend/main.py — FastAPI + CORS + Groq
 client wiring.
 - Chapter_07_AI_Agent_VIBE_Coding/frontend/ — Vite+TS+Tailwind+Router skeleton,
  package.json deps, vite proxy config.

 Build order (4 phases)

 1. Skeleton + ingest: scaffold dirs, requirements.txt, package.json,
 .env.example, clone two repos into data/, port embeddings/chunking libs, write
 5 ingest scripts + ingest_all.py. Verify by running ingest, inspecting
 qdrant_data/ and per-collection counts via /api/health.
 2. Backend retrieval: qdrant_store.py, retriever.py, router.py, /api/chat SSE
 endpoint with multi-turn memory. Verify with curl SSE against 5 sample
 questions (one per source).
 3. Frontend: bootstrap Vite app, ChatPane SSE consumer, SourcePanel,
 SourceFilter, IngestStatus. Wire vite proxy. Verify in browser: ask "show login
  test in Selenium", "list P0 admin TCs", "what is the PRD for login dashboard",
  "open bugs for login", "how does Playwright fixture do auth".
 4. Polish: README.md (matches Ch8 README style with mermaid flow diagram),
 CLAUDE.md (per /init request), .gitignore (chroma_db/, qdrant_data/,
 node_modules/, .venv/, .env), add chapter to root README.md.

 Required secrets / env (.env.example)

 GROQ_API_KEY=
 GROQ_MODEL=openai/gpt-oss-120b

 # Qdrant: file-store mode (no server) by default
 QDRANT_PATH=./qdrant_data
 # Or HTTP mode:
 # QDRANT_URL=http://localhost:6333
 # QDRANT_API_KEY=

 EMBED_MODEL=BAAI/bge-m3
 RERANK_MODEL=BAAI/bge-reranker-v2-m3
 EMBED_DEVICE=cpu        # or mps / cuda

 # Source paths (defaults relative to chapter dir)
 SELENIUM_REPO_DIR=./data/selenium_repo
 PLAYWRIGHT_REPO_DIR=./data/playwright_repo
 TESTCASES_CSV=./data/csv/testcases_vwo_100.csv
 PDFS_DIR=./data/pdf
 JIRA_MD_DIR=./data/md

 # Retrieval knobs
 TOP_K_PER_COLLECTION=12
 RERANK_TOP_K=4
 CHUNK_SIZE=1000
 CHUNK_OVERLAP=150
 HISTORY_TURNS=4

 CLAUDE.md content (deliverable for /init)

 CLAUDE.md will document, for future Claude sessions in this dir:

 - Run commands: pip install -r backend/requirements.txt, python -m
 backend.ingest.ingest_all, uvicorn backend.main:app --reload --port 8000, cd
 frontend && npm install && npm run dev, single ingest e.g. python -m
 backend.ingest.ingest_testcases
 - Architecture (big picture): 5-collection Qdrant store, LLM router,
 hybrid+rerank retrieval, FastAPI SSE → React. Where router decisions live
 (backend/lib/router.py), how to add a 6th source (3 steps: ingest script +
 collection name in qdrant_store.collections + entry in router prompt taxonomy).
 - Key data shapes: chunk payload schema per collection (table), SSE event
 protocol (event: token | sources | done).
 - Common pitfalls: Qdrant file-store can't run two processes simultaneously
 (must stop ingest before serving, or switch to HTTP mode); bge-m3 first load
 downloads ~2GB; tree-sitter wheels needed for Java + TS.
 - Reused libs: pointer to Chapter_08_RAG/Advance_RAG_EXPLAIN/lib/ for the
 chunking and embedding patterns this chapter ports from.
 - Skip non-obvious code/conventions only, no generic "write tests" filler.

 Verification

 End-to-end sanity:

 cd Chapter_09_Project_QACopilot
 # 1. clone source repos into data/
 git clone https://github.com/PramodDutta/ATB14xSeleniumAdvanceFrameworks
 data/selenium_repo
 git clone https://github.com/PramodDutta/Advance-Playwright-Framework
 data/playwright_repo

 # 2. backend
 python -m venv .venv && source .venv/bin/activate
 pip install -r backend/requirements.txt
 cp .env.example .env   # fill GROQ_API_KEY
 python -m backend.ingest.ingest_all
 uvicorn backend.main:app --reload --port 8000 &

 # 3. health probe shows non-zero counts in all 5 collections
 curl http://localhost:8000/api/health

 # 4. five smoke questions (one per collection) via curl SSE OR via UI
 cd frontend && npm install && npm run dev
 # open http://localhost:5173

 Smoke questions per collection:
 1. selenium_code: "Show the BasePage waitForElement implementation"
 2. playwright_code: "How is the login fixture set up in Playwright?"
 3. vwo_testcases: "List all P0 Blocker test cases for the Admin module"
 4. vwo_docs: "What does the PRD say about login dashboard auth flow?"
 5. vwo_bugs: "Show open bugs related to login failures"

 Each answer must include inline [n] citations and matching expandable source
 cards with the right metadata field rendered (file:line / TC-id+jira_id / pdf
 page / JIRA-id).

 Open assumptions (flag if wrong)

 - Test case corpus is 100 rows now; user mentioned 5000 — plan handles either
 size, only ingest time changes.
 - data/md/ only contains JIRA bug exports of the form Bug_VWO_*.md. If other
 doc types appear, add a parser branch.
 - Playwright repo is TS (typical); if it's JS-only the same
 tree-sitter-typescript grammar parses it.
 - Local-only by default (Qdrant file store, embeddings on CPU/MPS). HTTP Qdrant
  + GPU is a documented switch, not the default.