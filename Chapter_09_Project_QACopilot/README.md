# QA Copilot

AI-powered QA assistant that helps search test cases, generate test code, map JIRA tickets, and debug failures.

## Features

- **Chat Mode**: Ask questions about test cases, code, and JIRA tickets
- **Generate Test Code**: Auto-generate Selenium or Playwright test code
- **Search Only**: Search through documentation and test cases
- **Data Ingestion**: Import test cases from PDF, CSV, Selenium, and Playwright files

## Setup

1. Create virtual environment:
```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
copy .env.example .env
# Edit .env with your OpenAI API key
```

4. Run the app:
```bash
streamlit run src/ui/app.py
```

## Project Structure

- `src/ingestion/` - Data loading and processing
- `src/llm/` - RAG chain and LLM service
- `src/retriever/` - Vector store for semantic search
- `src/ui/` - Streamlit UI

## Usage

1. Click "Run Data Ingestion" to load your test cases
2. Select a mode: Chat, Generate Test Code, or Search Only
3. Choose search source (All, Selenium, Playwright, etc.)
4. Ask questions or generate test code