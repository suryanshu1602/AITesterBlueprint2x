# Chapter 17 — Fine-Tuning Open-Source Models on Your Own Data

Take a free, open-source LLM (Qwen2.5-Coder, Llama 3, Mistral, Phi, etc.) and adapt it to **your own knowledge** — a code repository, a Jira project, a stack of PDFs, internal wikis, chat transcripts, anything. The model then answers questions, generates code, and writes content **in your voice and against your facts**, fully on your own machine. No keys, no SaaS, no data leaving the laptop.

> Setup for the Qwen2.5-Coder route is in [Fine_TUNE_Instructions.md](Fine_TUNE_Instructions.md) (and the same content as PDF: [SETUP_GUIDE_FINE_TUNE_QWEN2.5.md.pdf](SETUP_GUIDE_FINE_TUNE_QWEN2.5.md.pdf)).
>
> `fine_tune.py` is left empty for you to fill in as you follow the chapter.

---

## What "fine-tuning" actually means here

Two very different things get called "fine-tuning". This chapter covers both.

| Approach | Weights changed? | Compute needed | When to use |
| :--- | :--- | :--- | :--- |
| **Retrieval-Augmented Generation (RAG)** | No | CPU is fine | Facts that change often, repos that get new commits, PDFs you keep adding. The model stays generic; your data is injected at query time. |
| **LoRA / QLoRA fine-tune** | Yes (a small adapter) | GPU or Apple Silicon (MLX) | Style, tone, domain jargon, a fixed body of knowledge you want baked into the model. Slower to update but the answers feel native. |
| **Full fine-tune** | Yes (all weights) | Multi-GPU cluster | Almost never the right choice for a single developer. Skip. |

Most teams need **RAG first, LoRA second**. The setup guide in this folder describes RAG using `qwen2.5-coder:14b` + `nomic-embed-text` via Ollama — that is the safest, cheapest starting point.

---

## What you can fine-tune against

| Source | How it's fed in | Example use |
| :--- | :--- | :--- |
| **Code repository** | Walk the tree, chunk by file / function, embed each chunk. Re-index on every commit. | "How does `LoginModule` call `LoginPage`?" → bot answers using actual files from the repo. |
| **Jira project** | Pull issues + comments via REST; one chunk per issue + linked comments. Tag chunks with project/sprint/labels. | "List unresolved P0 bugs in the Reports module from sprint 25.S38." |
| **PDF library** | Extract text per page (PyMuPDF / `pdfplumber`), split on headings, embed. | "What does our security playbook say about API token rotation?" |
| **Confluence / wiki** | Hit the REST API, render to text, chunk by page section. | "What is our standard test plan template?" |
| **Slack / chat logs** | Export → strip emojis/mentions → chunk by thread. | "What did the team decide about the discount-code bug?" |
| **Test cases / CSV** | One chunk per row. Add the metadata (priority, module, owner) as filter fields. | "Show me regression tests owned by `aditya.rao` in the Editor module." |
| **Internal training videos** | Whisper → transcript → chunk by timestamp. | "When in the onboarding video do they show the staging credentials?" |
| **Customer tickets** | Same shape as Jira. Be careful with PII. | "Top 5 root causes of refund tickets last quarter." |
| **OpenAPI / Postman collections** | One chunk per endpoint + the request/response examples. | "Generate a Playwright API test for `POST /booking` with full assertions." |

Anything that can be read as text and split into ~512–1024 token chunks is fair game.

---

## Stack you'll use in this chapter

| Layer | Tool |
| :--- | :--- |
| Local LLM | [Ollama](https://ollama.com/) running `qwen2.5-coder:14b` (or `:7b` on lighter hardware) |
| Embeddings | `nomic-embed-text` via Ollama |
| Vector store | LanceDB or Chroma (local file-backed) |
| Glue code | Python (`index_repo.py`, `ask.py`) |
| Optional LoRA | [MLX-LM](https://github.com/ml-explore/mlx-examples) on Apple Silicon, or [Unsloth](https://github.com/unslothai/unsloth) on a CUDA GPU |

Everything runs offline once the models are pulled.

---

## What this chapter is NOT

- Not a managed service. No OpenAI/Anthropic/Groq keys involved.
- Not a guarantee of correctness — your retrieval and your data quality decide that.
- Not LoRA-first. Start with RAG. Move to LoRA only when retrieval already works and you want the model to *sound* like your domain.

---

## Where to go next

1. Read [Fine_TUNE_Instructions.md](Fine_TUNE_Instructions.md). It is the Qwen2.5-Coder + Ollama recipe end to end.
2. Try the bot against the [Advance-Playwright-Framework](https://github.com/PramodDutta/Advance-Playwright-Framework) repo first — it is small enough to index in seconds.
3. Then swap the data source: point `index_repo.py` at a folder of PDFs, or rewrite the indexer to fetch from Jira / Confluence.
4. Once retrieval feels solid, look at LoRA via MLX-LM (Mac) or Unsloth (CUDA) for tone/style fine-tuning.
