"""
CrewAI + Jira MCP: Auto-Generate Test Plans, Test Cases & Playwright Scripts
─────────────────────────────────────────────────────────────────────────────
Input  : A Jira ticket ID (e.g., VWO-48)
Output : test_plan.md, test_cases.md, playwright_tests.md

Pipeline:
  1. Jira Analyst       → fetches ticket via MCP, extracts requirements
  2. Test Plan Writer   → writes complete test plan (12 sections)
  3. Test Case Writer   → writes detailed test cases table
  4. Playwright Coder   → generates automation scripts
"""
import os
import re
import datetime
from pathlib import Path
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import MCPServerAdapter
from dotenv import load_dotenv
import requests
from mcp import StdioServerParameters

PROJECT_ROOT = Path(__file__).resolve().parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
OUTPUT_DIR = PROJECT_ROOT / "output"
PW_FRAMEWORK_DIR = OUTPUT_DIR / "advanced-playwright-framework"


load_dotenv()


# Workaround: CrewAI 1.14.6 attaches a `cache_breakpoint` field to chat
# messages that Groq's OpenAI-compatible endpoint rejects. Strip it before
# every call.
class GroqLLM(LLM):
    def call(self, messages, *args, **kwargs):
        if isinstance(messages, list):
            cleaned = []
            for m in messages:
                if isinstance(m, dict):
                    m = {k: v for k, v in m.items() if k != "cache_breakpoint"}
                cleaned.append(m)
            messages = cleaned
        return super().call(messages, *args, **kwargs)

# Step 0 - Setup the Brain.
# gpt-oss-120b free tier on Groq caps at 8000 TPM, which this 4-task pipeline
# (with accumulated context) blows past. llama-3.3-70b-versatile sits at 30k
# TPM on the same tier — plenty for the full crew. Swap back if you upgrade.
groq_llm = GroqLLM(
    model="openai/llama-3.3-70b-versatile",
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_KEY"),
)

# ══════════════════════════════════════════════════════════════════
#  MCP SERVER CONFIGURATION
# ══════════════════════════════════════════════════════════════════

def get_mcp_server_params() -> StdioServerParameters:
    """
    Configure the mcp-atlassian server connection.

    This tells CrewAI to launch `uvx mcp-atlassian` as a subprocess
    and communicate with it over STDIO (stdin/stdout).

    The MCP server handles:
    - Jira REST API authentication
    - ADF (Atlassian Document Format) → text conversion
    - Pagination for large result sets
    - Error handling and retries
    """
    # Accept either JIRA_USERNAME or JIRA_EMAIL (Atlassian Cloud uses email
    # as the username). Default JIRA_URL to the known workspace if missing.
    jira_username = os.getenv("JIRA_USERNAME") or os.getenv("JIRA_EMAIL", "")
    jira_url = os.getenv("JIRA_URL", "https://bugzz.atlassian.net")
    return StdioServerParameters(
        command="uvx",
        args=["mcp-atlassian"],
        env={
            # Pass Jira credentials to the MCP server process
            "JIRA_URL": jira_url,
            "JIRA_USERNAME": jira_username,
            "JIRA_API_TOKEN": os.getenv("JIRA_API_TOKEN", ""),
            # Inherit PATH so `uvx` can find Python/Node
            "PATH": os.environ.get("PATH", ""),
            # Pin python for the uvx-spawned tool
            "UV_PYTHON": "3.12",
        },
    )

# ══════════════════════════════════════════════════════════════════
#  TEST PLAN TEMPLATE
# ══════════════════════════════════════════════════════════════════

# Test plan structure now lives in templates/testplan.md.
TEST_PLAN_TEMPLATE = (TEMPLATES_DIR / "testplan.md").read_text(encoding="utf-8")


# ══════════════════════════════════════════════════════════════════
#  AGENTS
# ══════════════════════════════════════════════════════════════════

def create_agents(mcp_tools: list, ticket_id: str):
    """Create all four agents with MCP tools and return them."""

    # ── Agent 1: Jira Ticket Analyst ──────────────────────────────
    jira_analyst = Agent(
        role="Senior QA Analyst",
        goal=(
            f"Fetch Jira ticket {ticket_id} using the available Jira tools, "
            "then extract ALL testable requirements, acceptance criteria, "
            "edge cases, and risks."
        ),
        backstory=(
            "You are a senior QA analyst with 15+ years of experience. "
            "You have access to Jira through MCP tools. "
            "Your job is to fetch the ticket details and perform "
            "a thorough analysis of what needs to be tested. "
            "You identify functional requirements, acceptance criteria, "
            "edge cases, boundary conditions, and risks. "
            "IMPORTANT: Use the Jira tools to fetch the ticket first, "
            "then analyze what you receive."
        ),
        tools=mcp_tools,  # ← MCP tools injected here!
        llm=groq_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )
    # ── Agent 2: Test Plan Writer ─────────────────────────────────
    test_plan_writer = Agent(
        role="Test Plan Documentation Specialist",
        goal=(
            "Create a comprehensive, professional test plan document "
            "following the standard 12-section template."
        ),
        backstory=(
            f"You are a certified ISTQB test planning expert. "
            f"You write detailed test plans that teams can immediately execute. "
            f"You MUST follow this template:\n{TEST_PLAN_TEMPLATE}\n"
            f"Today's date is {datetime.date.today().strftime('%B %d, %Y')}. "
            f"Use professional markdown formatting."
        ),
        llm=groq_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )
    # ── Agent 3: Test Case Writer ─────────────────────────────────
    test_case_writer = Agent(
        role="Test Case Design Specialist",
        goal=(
            "Design detailed, executable test cases covering positive, "
            "negative, edge, and boundary scenarios."
        ),
        backstory=(
            "You are a QA engineer who specializes in test case design. "
            "You write test cases that are so clear and detailed that "
            "anyone — even a junior tester — can execute them without "
            "asking questions. Each test case includes: TC ID, Title, "
            "Preconditions, Step-by-step instructions, Expected Results, "
            "Test Data, and Priority. You always cover: "
            "happy path, negative scenarios, edge cases, boundary values, "
            "UI validations, and error handling."
        ),
        llm=groq_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )

    # ── Agent 4: Playwright Script Generator ──────────────────────
    playwright_coder = Agent(
        role="Playwright Automation Engineer",
        goal=(
            "Generate production-ready Playwright test scripts in "
            "TypeScript that automate the key test cases."
        ),
        backstory=(
            "You are a senior SDET who writes clean, maintainable "
            "Playwright tests in TypeScript. Your scripts follow best "
            "practices:\n"
            "- Page Object Model (POM) structure\n"
            "- Proper locator strategies (data-testid > CSS > XPath)\n"
            "- Meaningful test descriptions using test.describe/test()\n"
            "- Proper assertions with expect()\n"
            "- Setup/teardown with beforeEach/afterEach\n"
            "- Error handling and retry logic where needed\n"
            "- Comments explaining the test logic\n"
            "You generate COMPLETE, RUNNABLE TypeScript files. "
        ),
        llm=groq_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )

    return jira_analyst, test_plan_writer, test_case_writer, playwright_coder

# ══════════════════════════════════════════════════════════════════
#  TASKS
# ══════════════════════════════════════════════════════════════════

def create_tasks(agents: tuple, ticket_id: str):
    """Create all four tasks and wire them together."""

    jira_analyst, test_plan_writer, test_case_writer, playwright_coder = agents

    # ── Task 1: Fetch & Analyze Jira Ticket ───────────────────────
    analysis_task = Task(
        description=(
            f"Fetch Jira ticket **{ticket_id}** using the available Jira MCP tools.\n\n"
            "Look for a tool that can get issue details — it might be called "
            "something like 'jira_get_issue' or 'get_issue' or similar.\n\n"
            f"Pass the ticket ID '{ticket_id}' to fetch the full details.\n\n"
            "After fetching, provide a DETAILED analysis:\n"
            "1. Summary of the ticket (what the feature/bug is about)\n"
            "2. ALL testable requirements extracted from the ticket\n"
            "3. Acceptance criteria (explicit and implicit)\n"
            "4. Potential edge cases and boundary conditions\n"
            "5. Risks and dependencies\n"
            "6. Suggested testing types (functional, regression, performance, etc.)\n\n"
            "Be thorough — all other agents depend on your analysis."
        ),
        expected_output=(
            "A detailed analysis report containing: ticket summary, "
            "testable requirements list, acceptance criteria, edge cases, "
            "risks, and recommended testing types."
        ),
        agent=jira_analyst,
    )

    # ── Task 2: Write Test Plan ───────────────────────────────────
    test_plan_task = Task(
        description=(
            f"Based on the Jira ticket analysis, create a COMPLETE test plan "
            f"for {ticket_id}.\n\n"
            "Follow the standard 12-section template EXACTLY. Include:\n"
            "- All 12 sections from the template\n"
            "- High-level test scenarios (NOT detailed test cases)\n"
            "- Realistic risk assessment with 3-5 risks\n"
            "- Proper test schedule with phases\n"
            f"- Use today's date: {datetime.date.today().strftime('%B %d, %Y')}\n\n"
            "Format everything in clean, professional markdown."
        ),
        expected_output=(
            "A complete, professional test plan document in markdown format "
            "following all 12 sections of the template."
        ),
        agent=test_plan_writer,
        context=[analysis_task],
        output_file="output/test_plan.md",
    )
    # ── Task 3: Write Detailed Test Cases (Jira-importable CSV) ───
    test_cases_task = Task(
        description=(
            f"Based on the ticket analysis and test plan, produce DETAILED "
            f"test cases for {ticket_id} as **Jira-importable CSV**.\n\n"
            "OUTPUT FORMAT (strict):\n"
            "- Plain CSV only. No markdown fences. No prose before or after.\n"
            "- First row is the header EXACTLY:\n"
            "  Summary,Issue Type,Priority,Labels,Components,"
            "Description,Reporter,Assignee\n"
            "- Use these column rules:\n"
            "  * Summary       — one-line title of the test case\n"
            "  * Issue Type    — always 'Test'\n"
            "  * Priority      — Highest|High|Medium|Low (map P0->Highest, "
            "P1->High, P2->Medium, P3->Low)\n"
            "  * Labels        — pipe-separated tags (smoke|regression|edge|...)\n"
            "  * Components    — the module under test\n"
            "  * Description   — Jira Wiki markup with the full body:\n"
            "                    h3. Preconditions\\n<text>\\n\\n"
            "                    h3. Steps\\n# step 1\\n# step 2 ...\\n\\n"
            "                    h3. Expected Result\\n<text>\\n\\n"
            "                    h3. Test Data\\n<text>\\n\\n"
            "                    h3. Category\\nPositive|Negative|Edge|UI|API|Perf\n"
            "  * Reporter      — 'qa-bot'\n"
            "  * Assignee      — leave blank\n"
            "- Quote any cell that contains a comma, quote, or newline with "
            "double quotes; escape inner quotes by doubling them.\n"
            "- Generate at least 12-15 rows covering:\n"
            "  positive (3-4), negative (3-4), edge (2-3), UI (2-3), API (1-2), "
            "performance (1)."
        ),
        expected_output=(
            "A valid CSV file body ready for Jira CSV import. First row is the "
            "exact header. 12-15 data rows. No markdown, no commentary."
        ),
        agent=test_case_writer,
        context=[analysis_task, test_plan_task],
        output_file="output/test_cases.csv",
    )

    # ── Task 4: Generate Playwright Scripts (Advanced Framework) ──
    playwright_task = Task(
        description=(
            f"Generate Playwright automation code for {ticket_id} that fits "
            "the **Advanced Playwright Framework** (Pages / Modules / Tests / "
            "Fixtures / Utils layering).\n\n"
            "OUTPUT FORMAT (strict — do not deviate):\n"
            "- Emit one or more files separated by literal markers.\n"
            "- For each file emit ONLY:\n\n"
            "  === FILE: <relative/path/from/framework/root> ===\n"
            "  <complete file contents, no markdown fences>\n"
            "  === END FILE ===\n\n"
            "- The relative paths MUST match this folder layout:\n"
            "    src/pages/<Feature>Page.ts        — locators (arrow fns) + "
            "tiny UI actions; NO business logic.\n"
            "    src/modules/<Feature>Module.ts    — business logic "
            "(doLogin, addToCart, applyDiscount, ...).\n"
            "    src/tests/<feature>.spec.ts       — specs using "
            "test.describe('@P0 ...'), test.step(), fixtures.\n"
            "    src/fixtures/<feature>.fixture.ts — custom fixtures wiring "
            "pages + modules; export `test`.\n"
            "    src/testdata/<feature>.json       — JSON test data.\n\n"
            "Hard rules:\n"
            "- Pages contain ONLY locators as arrow functions and simple "
            "page.fill / page.click wrappers. No conditionals.\n"
            "- Modules contain business orchestration that calls page methods.\n"
            "- Specs use the custom fixture: `import { test } from "
            "'../fixtures/<feature>.fixture'`. Wrap each step in "
            "`test.step()`. Tag describes with @P0/@P1/etc.\n"
            "- TypeScript strict. Use `import type` where appropriate.\n"
            "- No placeholders, no TODO, no `// fill this in`.\n"
            "- Do not output anything outside the FILE markers."
        ),
        expected_output=(
            "A sequence of `=== FILE: <path> ===` ... `=== END FILE ===` "
            "blocks. Each block contains the complete, runnable TypeScript "
            "source for that file. Paths follow src/pages, src/modules, "
            "src/tests, src/fixtures, src/testdata."
        ),
        agent=playwright_coder,
        context=[analysis_task, test_cases_task],
        output_file="output/playwright_raw.txt",
    )

    return analysis_task, test_plan_task, test_cases_task, playwright_task


# ══════════════════════════════════════════════════════════════════
#  POST-PROCESS: split Agent 4 output into the framework folders
# ══════════════════════════════════════════════════════════════════

_FILE_BLOCK = re.compile(
    r"===\s*FILE:\s*(?P<path>[^\n=]+?)\s*===\n(?P<body>.*?)\n===\s*END FILE\s*===",
    re.DOTALL,
)


def split_playwright_files(raw_text: str, target_dir: Path) -> list[Path]:
    """Parse Agent 4 output and write each block to its file under target_dir.

    Returns the list of written paths. Strips wrapping ``` fences if the LLM
    couldn't help itself.
    """
    written: list[Path] = []
    matches = list(_FILE_BLOCK.finditer(raw_text))
    if not matches:
        print("⚠️  No FILE markers found in Agent 4 output. "
              "Raw text left at output/playwright_raw.txt for debugging.")
        return written

    for m in matches:
        rel = m.group("path").strip().lstrip("/")
        body = m.group("body")
        # Strip a leading/trailing ```ts / ``` fence if the model added one.
        body = re.sub(r"^```[a-zA-Z]*\n", "", body)
        body = re.sub(r"\n```$", "", body)
        dest = target_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body.rstrip() + "\n", encoding="utf-8")
        written.append(dest)
    return written

# ══════════════════════════════════════════════════════════════════
#  CREW ORCHESTRATION
# ══════════════════════════════════════════════════════════════════

def run_crew(ticket_id: str):
    """
    Main function: Connect to Jira MCP → Create Crew → Run Pipeline.

    The MCPServerAdapter handles:
    1. Launching `uvx mcp-atlassian` as a subprocess
    2. Discovering all available Jira tools via MCP protocol
    3. Converting MCP tools to CrewAI-compatible BaseTool instances
    4. Cleaning up the subprocess when done (context manager)
    """
    print(f"\n📡 Target Jira Ticket: {ticket_id}")
    print("=" * 60)

    # Create output directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PW_FRAMEWORK_DIR.mkdir(parents=True, exist_ok=True)

    # ── Connect to Jira MCP Server ────────────────────────────────
    server_params = get_mcp_server_params()

    print("🔌 Connecting to Jira MCP server (mcp-atlassian)...")

    with MCPServerAdapter(server_params, connect_timeout=60) as mcp_tools:
        # Show discovered tools
        tool_names = [t.name for t in mcp_tools]
        print(f"✅ Connected! Discovered {len(mcp_tools)} Jira tools:")
        for name in tool_names:
            print(f"   • {name}")
        print()

        # Groq free tier caps `gpt-oss-120b` at 8000 TPM. mcp-atlassian
        # exposes ~49 tools — every tool schema is added to the system
        # prompt and easily blows the budget. Filter to just what Agent 1
        # actually needs: read a Jira issue.
        ALLOWED = {"jira_get_issue", "jira_search"}
        filtered_tools = [t for t in mcp_tools if t.name in ALLOWED]
        print(f"🔧 Using {len(filtered_tools)} tool(s) to stay under TPM limit: "
              f"{[t.name for t in filtered_tools]}\n")

        # ── Create Agents (inject MCP tools into Agent 1) ─────────
        agents = create_agents(filtered_tools, ticket_id)

        # ── Create Tasks (wired sequentially) ─────────────────────
        tasks = create_tasks(agents, ticket_id)

        # ── Assemble the Crew ─────────────────────────────────────
        crew = Crew(
            agents=list(agents),
            tasks=list(tasks),
            process=Process.sequential,
            verbose=True,
            max_rpm=4,  # Rate limit for Groq free tier
        )

        # ── Run! ──────────────────────────────────────────────────
        print(f"\n🚀 Starting QA Pipeline for {ticket_id}")
        print("=" * 60)

        result = crew.kickoff()

        # ── Post-process: split Agent 4 raw output into framework tree ────
        raw_pw = OUTPUT_DIR / "playwright_raw.txt"
        written_files: list[Path] = []
        if raw_pw.exists():
            written_files = split_playwright_files(
                raw_pw.read_text(encoding="utf-8"), PW_FRAMEWORK_DIR
            )

        print("\n" + "=" * 60)
        print("🎉 QA PIPELINE COMPLETE!")
        print("=" * 60)
        print(f"\n📁 Generated artefacts under ./output/:")
        print(f"   📋 test_plan.md                          — Complete test plan")
        print(f"   🧪 test_cases.csv                        — Jira-importable test cases (CSV)")
        print(f"   📦 advanced-playwright-framework/        — Playwright sources:")
        if written_files:
            for p in written_files:
                rel = p.relative_to(PW_FRAMEWORK_DIR)
                print(f"        • {rel}")
        else:
            print(f"        (no FILE blocks parsed — see output/playwright_raw.txt)")
        print()

        return result