"""Groq REST call. Mirrors Basic_RAG_EXPLAIN's ask_groq shape."""
from __future__ import annotations

import json
import os
from typing import Iterable

import requests

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _build_context(chunks: list[dict]) -> str:
    blocks = []
    for i, c in enumerate(chunks, start=1):
        payload = c.get("payload", {})
        text = payload.get("text", "")
        cid = c.get("chunk_id", payload.get("chunk_id", "?"))
        meta_bits = []
        for k in ("test_case_id", "jira_id", "priority", "module"):
            v = payload.get(k)
            if v not in (None, ""):
                meta_bits.append(f"{k}={v}")
        meta_line = " | ".join(meta_bits)
        header = f"[Chunk {i}] (id={cid}{', ' + meta_line if meta_line else ''})"
        blocks.append(f"{header}\n{text}")
    return "\n\n---\n\n".join(blocks)


_SYSTEM_ANSWER = (
    "You are a helpful QA-engineering assistant for the VWO product. "
    "Answer ONLY using the provided context chunks (each is a test case or "
    "fragment of one). If the answer is not in the context, say so. "
    "Be concise and cite chunks like [Chunk 1], [Chunk 2]."
)

_SYSTEM_GENERATE = (
    "You are a senior QA engineer. The user wants you to draft a NEW test case "
    "(possibly tied to a Jira ID they mention). Use the provided context chunks "
    "as style and structure templates - they are real existing test cases. "
    "Output a single new test case using exactly this Markdown structure:\n"
    "**Title:** ...\n"
    "**Jira ID:** ... (use what the user gave, else 'N/A')\n"
    "**Priority:** ...\n"
    "**Module:** ...\n"
    "**Preconditions:**\n- ...\n"
    "**Steps:**\n1. ...\n2. ...\n"
    "**Expected Result:**\n- ...\n"
    "**Tags:** ...\n\n"
    "After the test case, add a short line: 'Style borrowed from: [Chunk N], [Chunk M]'."
)


def detect_mode(question: str) -> str:
    q = question.lower()
    triggers = ("create a new test case", "create a test case", "draft a test case",
                "write a test case", "generate a test case", "new test case for")
    return "generate" if any(t in q for t in triggers) else "answer"


def ask_groq(
    question: str,
    chunks: list[dict],
    mode: str = "answer",
    temperature: float = 0.2,
    max_tokens: int = 1024,
) -> dict:
    """Call Groq with system prompt selected by mode."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set in environment")
    model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

    system = _SYSTEM_GENERATE if mode == "generate" else _SYSTEM_ANSWER
    context = _build_context(chunks)
    user = f"CONTEXT:\n{context}\n\nQUESTION: {question}"

    r = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        data=json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }),
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()
    answer = data["choices"][0]["message"]["content"]
    return {"answer": answer, "raw": data, "mode": mode, "system": system}


def rewrite_query(question: str, n: int = 2, temperature: float = 0.4) -> list[str]:
    """Ask Groq for n alternate phrasings of the question. Returns a list including
    the original (so the caller has all queries to embed)."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return [question]
    model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
    sys = (
        "You rewrite user questions about software test cases for retrieval. "
        f"Return exactly {n} alternate phrasings, one per line, no numbering, "
        "no commentary. Keep entity names (Jira ids, modules) intact."
    )
    try:
        r = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": sys},
                    {"role": "user", "content": question},
                ],
                "temperature": temperature,
                "max_tokens": 200,
            }),
            timeout=30,
        )
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"]
    except Exception:
        return [question]
    alts = [ln.strip(" -*\t") for ln in text.splitlines() if ln.strip()]
    alts = [a for a in alts if a and a.lower() != question.lower()][:n]
    return [question, *alts]
