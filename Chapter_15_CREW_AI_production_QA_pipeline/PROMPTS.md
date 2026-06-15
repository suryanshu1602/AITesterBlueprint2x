# Chapter 15 — All Prompts (Session Log)

Captures every natural-language prompt used to build Chapter 14 (base pipeline) and Chapter 15 (production version with template/CSV/framework split and the lightweight UI). Useful for reproducing the build, training future agents, or auditing how the pipeline evolved.

---

## Chapter 14 — Base Pipeline

### Setup
> in the chapter 14, I want you to please start a virtual environment.

> Please install pip install crewai crewai-tools[mcp] mcp python-dotenv litellm

### Build crew.py
> fix itendetaion

> okay, so your task is to run this main.py with the argument of vwo-48, which is the default version. You need to also show me step by step:
> - what is the output
> - how the connection is getting made with mcp
> - what data we are fetching

### Iterate
> rerun fresh token is added

---

## Chapter 15 — Production Version

### Promote to its own chapter
> can you please create a production folder in this? We are going to copy the crew.AI main file as well as the ENV file in the production folder. We are going to make certain changes. It will be a separate production-ready AI agents.

> Can you please make the production as a chapter 15? We are going to make some changes in the chapter 15. Chapter_15_Kru.ai_production_QA_pipeline

> please make sure that environment variable is also created.

### Restructure outputs (template + CSV + framework)
> Please pull out the test plan out of the folder and create a template folder where the testplan.md file will be present. Second thing is I want to create test cases in a CSV Jira format. Can you please do that? Another important thing is that whatever the playwright test case is created by the fourth agent, it should be in a proper folder structure. It should follow my advanced playwright framework, which I am going to attach right now with you. I want you to add the file where agent four will only create the files into my advanced playwright framework architecture. I have attached the architecture.md file in this folder. I want a Playwright test case to be created in the output folder, so in the output folder/advanced-playwright-framework, the files should be created properly.

### Lightweight UI
> Please create a lightweight UI in the /ui folder where I can mention the multiple Jira IDs. When you run it, you will give me the proper folder structure output, as well as the CSV file and the MD file generated also.

### Debug UI
> http://127.0.0.1:8000/ is not working

> RuntimeError: Agent execution was invoked synchronously from within a running event loop. Use `agent.kickoff_async()` / `crew.kickoff_async()` (or `await agent.aexecute_task(...)`) when calling from async code.

### Docs + ship
> update the README.md, commit the changes, and push the code.

> Can you please add the creative prompts.md file where all the prompts which we have mentioned here? I just put it there.

---

## What the prompts built

| Asset | Origin prompt |
| --- | --- |
| `Chapter_14_Crew_AI_QA_Pipeline/` venv + `crewai 1.14.6` + tools | Setup prompts |
| `crew.py` — 4-agent pipeline (analyst → plan → cases → playwright) over Jira MCP | "fix indentation" + first run prompt |
| Sequential crew with `MCPServerAdapter`, `uvx mcp-atlassian`, tool filter to fit Groq 8k TPM | First run + retry prompts |
| Model swap `gpt-oss-120b → llama-3.3-70b-versatile` | TPM diagnosis during the retry |
| `Chapter_15_CREW_AI_production_QA_pipeline/` (promoted from `production/`) | "production folder" + "make it chapter 15" |
| `templates/testplan.md` | Restructure prompt |
| `output/test_cases.csv` in Jira-import format | Restructure prompt |
| `output/advanced-playwright-framework/src/{pages,modules,tests,fixtures,testdata}/` + Python splitter on `=== FILE: ... ===` markers | Restructure prompt + `docs/ARCHITECTURE.html` |
| `ui/app.py` Starlette + Jinja2 + `templates/{index,results}.html` | UI prompt |
| Server start, `--reload`, `asyncio.to_thread(run_crew, ticket)` fix | Debug prompts |

---

## How to add a new agent (template)

1. Decide its **role / goal / backstory** (1-2 sentences each).
2. Write the prompt for its **Task**: description + `expected_output`.
3. Add `context=[upstream_task, ...]` so it reads prior agents' outputs.
4. Set `output_file="output/<artifact>"` and adapt the post-process step (e.g. CSV parsing, file splitting) if the artifact isn't plain text.

Same loop the four current agents follow.
