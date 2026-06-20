"""Single judge implementation that works for any OpenAI-compatible API.

Why one class for three providers? OpenAI, Groq, and Ollama all expose the
exact same wire protocol at <base_url>/chat/completions, so we only need to
swap the base_url and api_key. `instructor` handles structured-output schema
extraction uniformly across all of them, which is what DeepEval requires for
its metric prompts.
"""
from __future__ import annotations

from typing import Any

import instructor
from deepeval.models.base_model import DeepEvalBaseLLM
from openai import OpenAI


class CompatibleJudge(DeepEvalBaseLLM):
    """OpenAI-compatible judge LLM (works for OpenAI, Groq, Ollama)."""

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str | None = None,
        provider_label: str = "compat",
        instructor_mode: instructor.Mode = instructor.Mode.JSON,
    ):
        self._model = model
        self._provider_label = provider_label
        self._raw = OpenAI(api_key=api_key or "no-key", base_url=base_url)
        self._patched = instructor.from_openai(self._raw, mode=instructor_mode)

    def load_model(self) -> Any:
        return self._patched

    def generate(self, prompt: str, schema: Any | None = None) -> Any:
        if schema is not None:
            return self._patched.chat.completions.create(
                model=self._model,
                response_model=schema,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_retries=2,
            )
        completion = self._raw.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return completion.choices[0].message.content

    async def a_generate(self, prompt: str, schema: Any | None = None) -> Any:
        return self.generate(prompt, schema=schema)

    def get_model_name(self) -> str:
        return f"{self._provider_label}/{self._model}"
