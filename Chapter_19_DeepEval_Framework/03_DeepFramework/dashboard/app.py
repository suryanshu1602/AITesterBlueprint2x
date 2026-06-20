"""DeepEval dashboard — FastAPI app on port 8203.

Drives the same metric registry the pytest suite uses, but exposes
each metric as an interactive button in a web UI that streams live
pass/fail/score/reason. Lets the user switch between target apps
(chatbot vs RAG) and judge providers (openai/groq/ollama) without
restarting the server.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# allow imports from parent (llm_providers/, targets/, datasets/)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from llm_providers import judge_info  # noqa: E402
from llm_providers.factory import PROVIDERS, _resolve_provider  # noqa: E402
from targets import ChatbotClient, RagClient  # noqa: E402

from .registry import REGISTRY, REGISTRY_BY_ID, list_for_target  # noqa: E402
from .runner import run_metric  # noqa: E402

HERE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(HERE / "templates"))

app = FastAPI(title="DeepEval Dashboard", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")


class RunRequest(BaseModel):
    metric_id: str
    sample_idx: int = 0


class JudgeRequest(BaseModel):
    provider: str
    model: str | None = None


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/api/info")
def info():
    chatbot_alive = ChatbotClient().is_alive()
    rag_alive = RagClient().is_alive()
    return {
        "judge": judge_info(),
        "providers": list(PROVIDERS.keys()),
        "current_provider": _resolve_provider(),
        "targets": {
            "chatbot": {"alive": chatbot_alive, "url": ChatbotClient().base_url},
            "rag": {"alive": rag_alive, "url": RagClient().base_url},
        },
        "metric_count": len(REGISTRY),
    }


@app.get("/api/metrics")
def metrics(target: str | None = None):
    rows = list_for_target(target)
    return {
        "metrics": [
            {
                "id": m.id,
                "name": m.name,
                "description": m.description,
                "category": m.category,
                "target": m.target,
                "threshold": m.threshold,
                "higher_is_better": m.higher_is_better,
                "display_threshold": m.display_threshold,
                "sample_kind": m.sample_kind,
                "requires": m.requires,
            }
            for m in rows
        ]
    }


@app.post("/api/judge")
def set_judge(req: JudgeRequest):
    if req.provider not in PROVIDERS:
        raise HTTPException(400, f"Unknown provider: {req.provider}")
    os.environ["JUDGE_PROVIDER"] = req.provider
    if req.model:
        cfg = PROVIDERS[req.provider]
        os.environ[cfg["model_env"]] = req.model
    return judge_info()


@app.post("/api/run")
def run(req: RunRequest):
    if req.metric_id not in REGISTRY_BY_ID:
        raise HTTPException(404, f"Unknown metric_id: {req.metric_id}")
    result = run_metric(req.metric_id, sample_idx=req.sample_idx)
    return JSONResponse(result)


@app.post("/api/run-all")
def run_all(req: dict):
    """Sequentially run every metric for the chosen target.

    Note: the UI calls /api/run per-metric for live streaming. This is
    here for completeness / curl users.
    """
    target = req.get("target") or "all"
    rows = list_for_target(target)
    out = []
    for m in rows:
        out.append(run_metric(m.id))
    return {"results": out}
