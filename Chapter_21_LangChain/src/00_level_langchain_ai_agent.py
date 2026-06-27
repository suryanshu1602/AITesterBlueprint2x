from dotenv import load_dotenv
from langchain_groq import ChatGroq
import os

load_dotenv()

llm = ChatGroq(model=os.getenv("LLM_MODEL"),temperature=2)
question = input("Enter your query?")
response = llm.invoke(question)
print(response.content)

