# Repo Q&A Bot — Setup Guide

Ask questions about the Advance-Playwright-Framework repo and get answers
from a local AI model. Everything runs on your own machine. No internet, no API keys.

---

## What you need first

- A computer with at least 16GB RAM (Mac, Windows, or Linux)
- Python installed (3.9 or newer)
- About 11GB of free disk space for the AI model

---

## Step 1 — Install Ollama

Ollama runs the AI model locally.

Download and install from: https://ollama.com/download

After installing, open a terminal and check it works:

```
ollama --version
```

---

## Step 2 — Download the two AI models

Run these two commands. They download once and stay on your machine.

```
ollama pull qwen2.5-coder:14b
ollama pull nomic-embed-text
```

> On a slower or smaller laptop, use `qwen2.5-coder:7b` instead of the 14b.
> It is lighter and still works well.

---

## Step 3 — Get the project files

Make sure you have these 3 files in one folder:

- index_repo.py
- ask.py
- requirements.txt

Put them inside the cloned repository folder (Advance-Playwright-Framework).

---

## Step 4 — Install the Python packages

In the terminal, go to that folder and run:

```
pip install -r requirements.txt
```

---

## Step 5 — Build the index (do this once)

This reads the whole repo and prepares it for questions.

```
python index_repo.py
```

Wait until it prints "Done." Re-run this command any time the code changes.

---

## Step 6 — Ask questions

Ask one question directly:

```
python ask.py "How does the LoginModule work?"
```

Or start chat mode and ask many questions:

```
python ask.py
```

Press Ctrl+C to exit chat mode.

---

## Example questions to try

- How does the LoginModule call the LoginPage?
- What test tags does the framework use?
- Where is the API testing layer?
- How do I write a new test in this framework?

---

## If something goes wrong

- "No index found" → run Step 5 first.
- Model not found → re-run the `ollama pull` commands in Step 2.
- Very slow answers → switch to the 7b model (see note in Step 2).
- Ollama errors → make sure the Ollama app is running.

---

That's it. You now have a local AI assistant trained on this exact repo.