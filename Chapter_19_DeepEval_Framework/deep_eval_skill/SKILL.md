---
name: deepeval-framework-setup
description: >-
  Set up a DeepEval LLM-as-judge evaluation framework from scratch for any
  chatbot, RAG pipeline, AI agent, or LLM-backed app under test — the same
  architecture used in Chapter 19 (ShopSphere chatbot, RAG Explorer, and the
  live BrowserBash bot). Use this skill WHENEVER the user wants to "evaluate",
  "test", "score", "benchmark", "add metrics to", "measure quality of", or
  "QA" a chatbot / RAG / agent / LLM app, or asks to "set up DeepEval", "build
  an eval harness", "judge an LLM", "add a new eval target", "add a metric",
  or replicate the Chapter 19 framework for a new application — even if they
  don't say the word "DeepEval". Covers the judge factory (OpenAI/Groq/Ollama),
  HTTP target clients, the metric registry, golden datasets, the FastAPI
  dashboard, the pytest suites, version pins, and the known gotchas.
---

# DeepEval Framework Setup

This skill builds a reusable **LLM-as-judge evaluation harness** around one or
more *apps under test* (a chatbot, a RAG pipeline, an AI agent — anything that
answers over HTTP). It is the generalized form of `Chapter_19_DeepEval_Framework/03_DeepFramework`,
which already evaluates three live targets. Treat that directory as the canonical
reference implementation; this skill tells you how to stand up the same thing for
a brand-new application.

## When you're invoked, first establish three things

1. **What is the target?** A chatbot, a RAG system, or an agent? How is it
   reached — local FastAPI, a hosted URL, a function call? What's the request
   shape and the response shape (JSON vs plain text)?
2. **What does "good" mean here?** Which qualities matter — staying on topic,
   grounding in retrieved context, no hallucination, no bias/toxicity, no PII
   leak, citing sources, multi-turn memory?
3. **Which judge LLM?** OpenAI (highest limits), Groq (fast, free tier is
   rate-limited), or local Ollama (no key, fully offline).

Don't guess these. If the user hasn't said, ask — the answers decide the
targets, the metric registry rows, and the datasets.

## The mental model

```
app under test  ──HTTP──▶  target client  ──▶  LLMTestCase  ──▶  metric
                                                                   │
                                                  judge LLM ◀──────┘
                                                       │
                                          score + pass/fail + reason
```

The framework never inspects the model inside the app — it treats the app as a
black box reached over HTTP, wraps each response in a DeepEval `LLMTestCase`,
and hands it to a metric. The metric prompts the **judge LLM** (a different,
trusted model) which returns a numeric score and a written reason. This
separation is the whole point: the thing being graded and the grader are
different models, so the grade is independent.

## Directory layout to create

Mirror this structure. It's deliberately flat so the dashboard and the pytest
suites import the *same* modules — never duplicate metric logic between them.

```
<framework>/
├── .env                      # keys + JUDGE_PROVIDER (gitignored — never commit)
├── requirements.txt          # pinned (see Versions below)
├── conftest.py               # loads .env, fixtures, liveness skip, run capture
├── pytest.ini                # markers
├── llm_providers/
│   ├── base.py               # CompatibleJudge(DeepEvalBaseLLM)
│   └── factory.py            # get_judge() reads JUDGE_PROVIDER
├── targets/
│   └── <app>.py              # HTTP client per app under test
├── datasets/
│   └── <app>_goldens.py      # golden Q&A + safety/PII probes
├── dashboard/
│   ├── app.py                # FastAPI on :8203 (interactive UI + REST)
│   ├── registry.py           # the single source of truth: MetricDef rows
│   ├── runner.py             # run one registry metric end-to-end → JSON
│   └── runs_store.py         # local run-history capture
└── tests/
    └── <app>/test_NN_*.py    # one pytest file per metric
```

The full, working code for every one of these files lives in
`references/templates.md`. Read it when you're writing the files — don't
reconstruct them from memory. Read `references/metrics-catalog.md` for the
complete list of metrics, their thresholds, and their score directions.

## Setup workflow

Follow these in order. Each step is small on purpose — verify before moving on.

1. **Scaffold + venv.** Create the directory tree, a `requirements.txt` with the
   pinned versions below, then `python3 -m venv venv && venv/bin/pip install -r
   requirements.txt`. Verify with `venv/bin/python -c "import deepeval,
   instructor, openai; print(deepeval.__version__)"`.

2. **Judge factory** (`llm_providers/`). Copy `CompatibleJudge` and the factory
   from `references/templates.md`. One class serves all three providers because
   OpenAI, Groq, and Ollama all speak the OpenAI-compatible wire protocol;
   `instructor` handles structured output uniformly. Verify:
   `JUDGE_PROVIDER=openai venv/bin/python -c "from llm_providers import get_judge; print(get_judge().get_model_name())"`.

3. **Target client(s)** (`targets/`). One small `requests`-based class per app —
   a `health()`/`is_alive()` and a `chat()` that returns a dataclass. Match the
   app's real contract: JSON body vs form, JSON response vs plain text, whether
   it takes conversation `history`. See the two contrasting examples in the
   templates (local JSON chatbot vs plain-text hosted bot).

4. **Golden dataset(s)** (`datasets/`). A dataclass per golden carrying `input`,
   `expected_output`, `context` (ground-truth facts), and `categories`. Plus a
   flat list of adversarial `SAFETY_PROMPTS`. Ground every `expected_output` and
   `context` in the app's real source of truth — a golden that cites facts the
   app doesn't have produces a misleading score.

5. **Metric registry** (`dashboard/registry.py`). This is the heart. One
   `MetricDef` row per (metric × target). Each row names a `factory(judge,
   threshold)`, a `sample_kind` (which dataset the runner pulls from), a
   `requires` list (which `LLMTestCase` fields the metric needs), and a
   `higher_is_better` flag that sets the threshold direction. Adding a metric =
   adding a row; it appears in the dashboard instantly.

6. **Runner** (`dashboard/runner.py`). Maps a `sample_kind` to a dataset, calls
   the target, builds the right `LLMTestCase`, runs the metric, returns a
   JSON-friendly dict. Copy it as-is; extend only the `sample_kind` switch when
   you add a new kind.

7. **conftest + pytest.ini.** `conftest.py` loads `.env`, exposes
   `judge`/target/golden fixtures, and auto-skips a suite when its target app is
   down (`needs_<app>` markers). Register the markers in `pytest.ini` so pytest
   doesn't warn.

8. **Dashboard** (`dashboard/app.py`). FastAPI on `:8203` that renders straight
   from the registry — click a metric, see live pass/fail/score/reason, switch
   judge provider on the fly. Start it with `uvicorn dashboard.app:app --port 8203`.

9. **pytest suites** (`tests/<app>/`). One file per metric, using
   `assert_test(test_case, [metric])` so `deepeval test run` captures each case
   (needed for the Confident AI cloud dashboard). Plain `metric.measure()` +
   `assert is_successful()` works for local pytest but is NOT captured by the CLI.

10. **Verify end-to-end.** Start the target app(s), then run one metric through
    the dashboard (`curl -X POST localhost:8203/api/run -d '{"metric_id":"...","sample_idx":0}'`)
    and one pytest suite. Confirm a real score comes back before declaring done.

## Versions — pin these

DeepEval's API and packaging move fast; pin to avoid surprises.

| Package | Version | Why |
|---------|---------|-----|
| `deepeval` | **`3.9.9`** | `4.0.6` (latest) ships a **broken `deepeval test run` CLI** — its code does `from deepeval.deepeval.config.settings import ...`, a typo; there is no nested `deepeval/deepeval/` package. The *library* works on 4.x, only the CLI crashes. `3.9.9` is the last release whose CLI works out of the box **and** still has every metric (`PIILeakageMetric`, `KnowledgeRetentionMetric`, `ConversationCompletenessMetric`). |
| `openai` | `>=2.0` | judge transport (also used for Groq/Ollama via base_url) |
| `groq` | `>=1.0` | optional, for Groq-hosted apps under test |
| `instructor` | `>=1.6` | structured output for judge prompts |
| `fastapi` / `uvicorn` / `jinja2` | `0.115 / 0.32 / 3.1` | the dashboard |
| `pytest` | `>=8` | the suites |

Judge models per provider: `openai` → `gpt-4o-mini`, `groq` → `openai/gpt-oss-120b`,
`ollama` → `gpt-oss:20b`. Override with `JUDGE_MODEL_OPENAI` / `_GROQ` / `_OLLAMA`.

## Gotchas worth knowing up front

These come from actually running the framework — flag them before the user hits them.

- **`HallucinationMetric` needs a non-empty `context`.** It throws on an empty
  list. Out-of-scope / refusal goldens often have no natural context — give them
  a scope-policy line, or tag them to skip hallucination.
- **`.env` is not auto-loaded by the apps under test.** The eval framework's
  `conftest.py` / dashboard load it, but the chatbot/RAG apps read raw
  `os.getenv` — export the key (or `set -a; source .env; set +a`) when launching them.
- **Groq's free tier caps `gpt-oss-120b` at 8000 TPM.** `deepeval test run` fans
  out judge calls concurrently and blows past it (429). For large or CLI runs,
  use the OpenAI judge (`JUDGE_PROVIDER=openai`, `gpt-4o-mini`).
- **Score direction is inverted for safety metrics.** Higher is better for
  quality (threshold = floor); lower is better for hallucination/bias/toxicity/PII
  (threshold = ceiling). Don't hand-roll the comparison — `metric.is_successful()`
  already handles the inversion.
- **`deepeval test run` only captures `assert_test()` cases.** A manual
  `measure()` loop runs fine locally but the CLI reports "No test cases found" and
  pushes nothing to Confident AI.
- **Different apps have different contracts.** A local FastAPI bot may return JSON
  `{reply, model, mode}`; a hosted bot may return plain text with a `visitorId`.
  The target client absorbs that difference so the rest of the framework doesn't care.

## Adding a new target (a new app to evaluate)

Common request: "evaluate my agent the same way." Steps:

1. Add `targets/<app>.py` — a client matching that app's HTTP contract.
2. Add `datasets/<app>_goldens.py` — goldens grounded in that app's truth.
3. Add `<app>` fixtures + a `needs_<app>` liveness skip in `conftest.py`, and the
   markers in `pytest.ini`.
4. Add `MetricDef` rows with `target="<app>"` to `registry.py` (reuse the metric
   factories — only the target + dataset change).
5. Extend `runner.py`'s `_call_target` to dispatch to the new client.
6. Add `tests/<app>/test_NN_*.py` suites.

Because the registry drives the dashboard, the new target's metrics become
clickable buttons with no UI changes.

## Adding a new metric

1. Use a built-in DeepEval metric, or define a `GEval` with a plain-English
   rubric (best for bespoke criteria like "cites a real source filename").
2. Write a one-line `factory(judge, threshold)` in `registry.py`.
3. Append a `MetricDef` row (set `higher_is_better` and `sample_kind`).
4. Optionally mirror it as a `tests/<app>/test_NN_*.py` using `assert_test`.

That's it — see `references/templates.md` for the exact code shapes.
