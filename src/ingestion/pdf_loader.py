import os
import uuid
from pypdf import PdfReader
from config import PDFS_PATH


def load_pdfs(pdf_path=None):
    pdf_path = pdf_path or PDFS_PATH
    documents = []
    if not os.path.exists(pdf_path):
        print(f"PDF path not found: {pdf_path}")
        return documents

    for filename in os.listdir(pdf_path):
        if filename.lower().endswith(".pdf"):
            filepath = os.path.join(pdf_path, filename)
            try:
                reader = PdfReader(filepath)
                text = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text += page_text + "\n"
                if text.strip():
                    documents.append({
                        "id": f"pdf_{uuid.uuid4().hex[:8]}",
                        "content": text.strip(),
                        "source": filename,
                        "type": "pdf",
                    })
            except Exception as e:
                print(f"Error reading {filename}: {e}")
    return documents


def load_jira_pdfs(pdf_path=None):
    pdf_path = pdf_path or PDFS_PATH
    documents = []
    if not os.path.exists(pdf_path):
        return documents

    for filename in os.listdir(pdf_path):
        if filename.lower().endswith(".pdf") and (
            "jira" in filename.lower() or "summary" in filename.lower()
        ):
            filepath = os.path.join(pdf_path, filename)
            try:
                reader = PdfReader(filepath)
                text = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text += page_text + "\n"
                if text.strip():
                    documents.append({
                        "id": f"jira_{uuid.uuid4().hex[:8]}",
                        "content": text.strip(),
                        "source": filename,
                        "type": "jira",
                    })
            except Exception as e:
                print(f"Error reading {filename}: {e}")
    return documents
