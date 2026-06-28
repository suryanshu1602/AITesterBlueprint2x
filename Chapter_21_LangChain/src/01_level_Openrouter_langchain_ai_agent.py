from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import os

load_dotenv()

# OpenRouter is OpenAI-compatible: same client, just point base_url at it
# and use the OpenRouter key. Model id comes from .env (e.g. a DeepSeek model).
llm = ChatOpenAI(
    model=os.getenv("LLM_MODEL"),
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    temperature=0.7,
)

question = input("Enter your query?")
response = llm.invoke(question)
print(response.content)
