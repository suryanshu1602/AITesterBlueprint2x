import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

LLM_MODEL = "llama-3.3-70b-versatile"
EMBEDDING_MODEL = "text-embedding-ada-002"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)

SELENIUM_REPO_PATH = os.path.join(BASE_DIR, "data", "selenium")
PLAYWRIGHT_REPO_PATH = os.path.join(BASE_DIR, "data", "playwright")
TEST_CASES_PATH = os.path.join(PARENT_DIR, "data", "csv", "testcases_vwo.csv")
PDFS_PATH = os.path.join(PARENT_DIR, "data", "pdf")

CHROMA_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "chroma_db")

COLLECTIONS = {
    "selenium": "selenium_code",
    "playwright": "playwright_code",
    "test_cases": "test_cases",
    "pdf_docs": "pdf_documentation",
    "jira_summaries": "jira_summaries",
}

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

CODE_CHUNK_SIZE = 800
CODE_CHUNK_OVERLAP = 100
