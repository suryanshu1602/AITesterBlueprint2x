"""
Lightweight Starlette UI for the QA Pipeline.

Run:
    cd Chapter_15_CREW_AI_production_QA_pipeline
    venv/bin/python -m uvicorn ui.app:app --reload --port 8000

Open http://127.0.0.1:8000/
"""

import asyncio
import os
import shutil
import sys
import traceback
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, RedirectResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

# Make the project root importable so `from crew import run_crew` resolves.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from crew import run_crew  # noqa: E402

UI_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = UI_DIR / "templates"
RUNS_DIR = PROJECT_ROOT / "runs"
OUTPUT_DIR = PROJECT_ROOT / "output"

RUNS_DIR.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _snapshot_output_for_ticket(ticket: str) -> Path:
    """Move everything in ./output into ./runs/<ticket>/ so the next run is clean."""
    dest = RUNS_DIR / ticket
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    if OUTPUT_DIR.exists():
        for item in OUTPUT_DIR.iterdir():
            shutil.move(str(item), str(dest / item.name))
    return dest


def _build_tree(root: Path) -> list[dict]:
    """Return a nested list of dicts describing the folder structure."""
    nodes: list[dict] = []
    for entry in sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
        node = {
            "name": entry.name,
            "is_dir": entry.is_dir(),
            "rel": str(entry.relative_to(RUNS_DIR)),
        }
        if entry.is_dir():
            node["children"] = _build_tree(entry)
        else:
            node["size"] = entry.stat().st_size
        nodes.append(node)
    return nodes


def _read_text(path: Path, max_bytes: int = 200_000) -> str:
    try:
        data = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return f"[failed to read {path.name}: {exc}]"
    if len(data) > max_bytes:
        return data[:max_bytes] + f"\n\n... [truncated, file is {len(data):,} bytes]"
    return data


def _parse_csv(text: str) -> list[list[str]]:
    """Tiny CSV parser — handles quoted cells and doubled-quote escapes."""
    rows: list[list[str]] = []
    row: list[str] = []
    cell: list[str] = []
    in_quotes = False
    i = 0
    while i < len(text):
        ch = text[i]
        if in_quotes:
            if ch == '"':
                if i + 1 < len(text) and text[i + 1] == '"':
                    cell.append('"')
                    i += 2
                    continue
                in_quotes = False
                i += 1
                continue
            cell.append(ch)
            i += 1
            continue
        if ch == '"':
            in_quotes = True
            i += 1
            continue
        if ch == ',':
            row.append("".join(cell))
            cell = []
            i += 1
            continue
        if ch == '\n':
            row.append("".join(cell))
            rows.append(row)
            row = []
            cell = []
            i += 1
            continue
        if ch == '\r':
            i += 1
            continue
        cell.append(ch)
        i += 1
    if cell or row:
        row.append("".join(cell))
        rows.append(row)
    return [r for r in rows if any(c.strip() for c in r)]


async def index(request: Request):
    return templates.TemplateResponse(
        request, "index.html", {"runs": sorted(p.name for p in RUNS_DIR.iterdir() if p.is_dir())}
    )


async def run(request: Request):
    form = await request.form()
    raw = (form.get("tickets") or "").strip()
    # Split on newline / comma / whitespace, strip, dedupe in order.
    seen: set[str] = set()
    tickets: list[str] = []
    for token in raw.replace(",", "\n").split():
        t = token.strip()
        if not t or t in seen:
            continue
        seen.add(t)
        tickets.append(t)

    if not tickets:
        return RedirectResponse(url="/", status_code=303)

    results: list[dict] = []
    for ticket in tickets:
        entry: dict = {"ticket": ticket, "ok": False, "error": None}
        try:
            # CrewAI's sync kickoff() refuses to run inside a live asyncio
            # loop (Starlette/uvicorn). Push it to a worker thread.
            await asyncio.to_thread(run_crew, ticket)
            snapshot = _snapshot_output_for_ticket(ticket)
            entry["ok"] = True
            entry["tree"] = _build_tree(snapshot)

            test_plan = snapshot / "test_plan.md"
            test_cases = snapshot / "test_cases.csv"
            if test_plan.exists():
                entry["test_plan_md"] = _read_text(test_plan)
            if test_cases.exists():
                csv_text = _read_text(test_cases)
                entry["test_cases_rows"] = _parse_csv(csv_text)
        except Exception as exc:  # noqa: BLE001
            entry["error"] = f"{exc.__class__.__name__}: {exc}\n\n{traceback.format_exc()}"
        results.append(entry)

    return templates.TemplateResponse(
        request, "results.html", {"results": results, "tickets": tickets}
    )


async def view_file(request: Request):
    rel = request.path_params["full_path"]
    target = (RUNS_DIR / rel).resolve()
    # Path-traversal guard.
    if not str(target).startswith(str(RUNS_DIR.resolve())):
        return FileResponse(status_code=403, path="/dev/null")
    if not target.exists() or not target.is_file():
        return FileResponse(status_code=404, path="/dev/null")
    return FileResponse(target)


routes = [
    Route("/", endpoint=index),
    Route("/run", endpoint=run, methods=["POST"]),
    Route("/runs/{full_path:path}", endpoint=view_file),
]

app = Starlette(debug=True, routes=routes)
