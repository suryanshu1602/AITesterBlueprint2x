import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL


class LLMService:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = LLM_MODEL

    def chat(self, messages, temperature=0.7):
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
            )
            return response.choices[0].message.content
        except Exception as e:
            error_msg = str(e).lower()
            if "clipboard" in error_msg or "image" in error_msg:
                raise Exception("This assistant does not support image input. Please enter text only.")
            raise

    def generate_code(self, prompt, context="", temperature=0.3):
        system_msg = {
            "role": "system",
            "content": (
                "You are a QA automation expert. Generate clean, production-ready "
                "test code based on the user's requirements. Use the provided context "
                "from existing test code to follow the same patterns and conventions. "
                "Always include proper imports, assertions, and error handling. "
                "Output only the code in a code block."
            ),
        }
        user_msg = {
            "role": "user",
            "content": f"Context from existing codebase:\n{context}\n\nRequirement: {prompt}",
        }
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[system_msg, user_msg],
            temperature=temperature,
        )
        return response.choices[0].message.content

    def answer_with_context(self, query, context, conversation_history=None):
        system_msg = {
            "role": "system",
            "content": (
                "You are a QA Copilot assistant. You help users search through test cases, "
                "understand test automation code, map JIRA tickets to tests, identify test gaps, "
                "and debug test failures. Use the provided context from the knowledge base to "
                "answer questions accurately. If the context doesn't contain relevant information, "
                "say so clearly. Be concise and helpful."
            ),
        }
        messages = [system_msg]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {query}",
        })
        return self.chat(messages)
