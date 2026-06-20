"""Factory: build a judge LLM from JUDGE_PROVIDER env var."""
from __future__ import annotations

import os

from .base import CompatibleJudge

PROVIDERS = {
    "openai": {
        "base_url": None,  # default
        "api_key_env": "OPENAI_API_KEY",
        "model_env": "JUDGE_MODEL_OPENAI",
        "model_default": "gpt-4o-mini",
        "label": "openai",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "model_env": "JUDGE_MODEL_GROQ",
        "model_default": "openai/gpt-oss-120b",
        "label": "groq",
    },
    "ollama": {
        "base_url_env": "OLLAMA_BASE_URL",
        "base_url_default": "http://localhost:11434/v1",
        "api_key_env": None,
        "model_env": "JUDGE_MODEL_OLLAMA",
        "model_default": "gpt-oss:20b",
        "label": "ollama",
    },
}


def _resolve_provider() -> str:
    return (os.getenv("JUDGE_PROVIDER") or "openai").lower().strip()


def get_judge() -> CompatibleJudge:
    name = _resolve_provider()
    if name not in PROVIDERS:
        raise ValueError(f"Unknown JUDGE_PROVIDER={name!r}. Pick one of {sorted(PROVIDERS)}")
    cfg = PROVIDERS[name]
    api_key = os.getenv(cfg.get("api_key_env") or "", "") if cfg.get("api_key_env") else "ollama"
    model = os.getenv(cfg["model_env"], cfg["model_default"])
    base_url = (
        os.getenv(cfg["base_url_env"], cfg["base_url_default"])
        if "base_url_env" in cfg
        else cfg["base_url"]
    )
    return CompatibleJudge(
        model=model,
        api_key=api_key,
        base_url=base_url,
        provider_label=cfg["label"],
    )


def judge_info() -> dict:
    judge = get_judge()
    return {
        "provider": _resolve_provider(),
        "model": judge.get_model_name(),
    }
