import os
import chromadb
from config import CHROMA_DB_PATH, COLLECTIONS


class VectorStore:
    def __init__(self):
        os.makedirs(CHROMA_DB_PATH, exist_ok=True)
        self.client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        self.collections = {}
        self._init_collections()

    def _init_collections(self):
        for key, name in COLLECTIONS.items():
            try:
                self.collections[key] = self.client.get_collection(name=name)
            except Exception:
                self.collections[key] = self.client.create_collection(name=name)

    def get_collection(self, key):
        return self.collections.get(key)

    def add_documents(self, key, ids, documents, metadatas=None):
        collection = self.collections.get(key)
        if not collection:
            raise ValueError(f"Collection '{key}' not found")
        collection.add(ids=ids, documents=documents, metadatas=metadatas)

    def query(self, key, query_text, n_results=5, where=None):
        collection = self.collections.get(key)
        if not collection:
            raise ValueError(f"Collection '{key}' not found")
        kwargs = {"query_texts": [query_text], "n_results": n_results}
        if where:
            kwargs["where"] = where
        return collection.query(**kwargs)

    def query_all(self, query_text, n_results=5):
        results = {}
        for key in self.collections:
            try:
                results[key] = self.query(key, query_text, n_results)
            except Exception as e:
                results[key] = {"error": str(e)}
        return results

    def get_count(self, key):
        collection = self.collections.get(key)
        if collection:
            return collection.count()
        return 0
