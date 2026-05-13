import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.retriever.vector_store import VectorStore
from src.llm.service import LLMService


class RAGChain:
    def __init__(self):
        self.store = VectorStore()
        self.llm = LLMService()

    def search(self, query, n_results=5, source=None):
        if source and source in self.store.collections:
            results = self.store.query(source, query, n_results)
            combined = self._format_results(results)
            return combined, {source: results}
        results = self.store.query_all(query, n_results)
        combined = self._format_all_results(results)
        return combined, results

    def ask(self, query, conversation_history=None, n_results=5, source=None):
        context, raw_results = self.search(query, n_results, source)
        if not context.strip():
            context = "No relevant information found in the knowledge base."
        answer = self.llm.answer_with_context(query, context, conversation_history)
        return answer, raw_results

    def generate_test_code(self, requirement, framework="selenium", language="java", n_results=3):
        source_map = {
            "selenium": "selenium",
            "playwright": "playwright",
        }
        collection_key = source_map.get(framework, "selenium")
        context, _ = self.search(requirement, n_results, source=collection_key)
        code = self.llm.generate_code(requirement, context)
        return code

    def _format_results(self, results):
        parts = []
        if "documents" in results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                source = ""
                if "metadatas" in results and results["metadatas"]:
                    meta = results["metadatas"][0][i] if i < len(results["metadatas"][0]) else {}
                    source = meta.get("source", "")
                parts.append(f"[Source: {source}]\n{doc}")
        return "\n\n---\n\n".join(parts)

    def _format_all_results(self, all_results):
        parts = []
        for source_key, results in all_results.items():
            if isinstance(results, dict) and "error" in results:
                continue
            formatted = self._format_results(results)
            if formatted.strip():
                parts.append(f"### {source_key}\n\n{formatted}")
        return "\n\n---\n\n".join(parts)
