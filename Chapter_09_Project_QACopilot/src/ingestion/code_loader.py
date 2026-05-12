import os
import uuid
from config import SELENIUM_REPO_PATH, PLAYWRIGHT_REPO_PATH


CODE_EXTENSIONS = {".java", ".ts", ".tsx", ".js", ".py"}


def load_source_code(repo_path, extensions=None):
    extensions = extensions or CODE_EXTENSIONS
    documents = []
    if not os.path.exists(repo_path):
        print(f"Source code path not found: {repo_path}")
        return documents

    for root, _, files in os.walk(repo_path):
        if any(skip in root for skip in [".git", "node_modules", "target", "build", "dist", "__pycache__"]):
            continue
        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext in extensions:
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    if content.strip():
                        rel_path = os.path.relpath(filepath, repo_path)
                        documents.append({
                            "id": f"code_{uuid.uuid4().hex[:8]}",
                            "content": content,
                            "source": rel_path,
                            "type": "source_code",
                            "filename": filename,
                            "extension": ext,
                        })
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    return documents


def load_selenium_code(repo_path=None):
    repo_path = repo_path or SELENIUM_REPO_PATH
    return load_source_code(repo_path, extensions={".java"})


def load_playwright_code(repo_path=None):
    repo_path = repo_path or PLAYWRIGHT_REPO_PATH
    return load_source_code(repo_path, extensions={".ts", ".tsx", ".js"})
