import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.ingestion.pdf_loader import load_pdfs, load_jira_pdfs
from src.ingestion.csv_loader import load_test_cases
from src.ingestion.code_loader import load_selenium_code, load_playwright_code
from src.ingestion.chunkers import chunk_source_code, chunk_pdf_text, chunk_test_case
from src.retriever.vector_store import VectorStore


def ingest_all(incremental=True):
    store = VectorStore()
    print("Starting data ingestion...")

    if incremental:
        existing_ids = _get_existing_ids(store)

    sources = [
        ("selenium", lambda: load_selenium_code()),
        ("playwright", lambda: load_playwright_code()),
        ("test_cases", lambda: load_test_cases()),
        ("pdf_docs", lambda: load_pdfs()),
        ("jira_summaries", lambda: load_jira_pdfs()),
    ]

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(func): name for name, func in sources}
        for i, future in enumerate(as_completed(futures), 1):
            name = futures[future]
            try:
                docs = future.result()
                print(f"\n[{i}/5] Loaded {len(docs)} {name} documents")
                if name == "selenium":
                    _ingest_code(store, "selenium", docs, existing_ids)
                elif name == "playwright":
                    _ingest_code(store, "playwright", docs, existing_ids)
                elif name == "test_cases":
                    _ingest_test_cases(store, docs, existing_ids)
                elif name == "pdf_docs":
                    _ingest_pdfs(store, docs, existing_ids)
                elif name == "jira_summaries":
                    _ingest_jira(store, docs, existing_ids)
            except Exception as e:
                print(f"Error loading {name}: {e}")

    print("\n--- Ingestion Summary ---")
    for key in store.collections:
        count = store.get_count(key)
        print(f"  {key}: {count} chunks")
    print("\nIngestion complete!")
    return store


def _get_existing_ids(store):
    existing = {}
    for key in store.collections:
        try:
            collection = store.collections[key]
            if collection.count() > 0:
                existing[key] = set(collection.get(include=[])["ids"])
            else:
                existing[key] = set()
        except:
            existing[key] = set()
    return existing


def _skip_existing(collection_key, doc_id, existing_ids):
    if collection_key not in existing_ids:
        return False
    return any(doc_id in eid for eid in existing_ids[collection_key])


def _ingest_code(store, collection_key, docs, existing_ids=None):
    if existing_ids is None:
        existing_ids = {}

    ids, documents, metadatas = [], [], []
    for doc in docs:
        if _skip_existing(collection_key, doc["id"], existing_ids):
            continue
        chunks = chunk_source_code(doc["source"], doc["content"])
        for i, chunk in enumerate(chunks):
            ids.append(f"{collection_key}_{doc['id']}_{i}")
            documents.append(chunk["content"])
            metadatas.append({
                "source": chunk["source"],
                "language": chunk.get("language", "unknown"),
                "type": chunk.get("type", "code"),
            })

    if ids:
        print(f"  Adding {len(ids)} new chunks...")
        store.add_documents(collection_key, ids, documents, metadatas)


def _ingest_test_cases(store, docs, existing_ids=None):
    if existing_ids is None:
        existing_ids = {}

    ids, documents, metadatas = [], [], []
    for doc in docs:
        if _skip_existing("test_cases", doc.get("row_index", doc["id"]), existing_ids):
            continue
        chunks = chunk_test_case(doc["source"], doc["content"])
        for i, chunk in enumerate(chunks):
            ids.append(f"tc_{doc.get('row_index', doc['id'])}_{i}")
            documents.append(chunk["content"])
            metadatas.append({
                "source": chunk["source"],
                "type": chunk.get("type", "test_case"),
                "row_index": doc.get("row_index", ""),
            })

    if ids:
        print(f"  Adding {len(ids)} new chunks...")
        store.add_documents("test_cases", ids, documents, metadatas)


def _ingest_pdfs(store, docs, existing_ids=None):
    if existing_ids is None:
        existing_ids = {}

    ids, documents, metadatas = [], [], []
    for doc in docs:
        if _skip_existing("pdf_docs", doc["id"], existing_ids):
            continue
        chunks = chunk_pdf_text(doc["source"], doc["content"])
        for i, chunk in enumerate(chunks):
            ids.append(f"pdf_{doc['id']}_{i}")
            documents.append(chunk["content"])
            metadatas.append({
                "source": chunk["source"],
                "type": chunk.get("type", "documentation"),
            })

    if ids:
        print(f"  Adding {len(ids)} new chunks...")
        store.add_documents("pdf_docs", ids, documents, metadatas)


def _ingest_jira(store, docs, existing_ids=None):
    if existing_ids is None:
        existing_ids = {}

    ids, documents, metadatas = [], [], []
    for doc in docs:
        if _skip_existing("jira_summaries", doc["id"], existing_ids):
            continue
        chunks = chunk_pdf_text(doc["source"], doc["content"])
        for i, chunk in enumerate(chunks):
            ids.append(f"jira_{doc['id']}_{i}")
            documents.append(chunk["content"])
            metadatas.append({
                "source": chunk["source"],
                "type": "jira",
            })

    if ids:
        print(f"  Adding {len(ids)} new chunks...")
        store.add_documents("jira_summaries", ids, documents, metadatas)


if __name__ == "__main__":
    ingest_all()
