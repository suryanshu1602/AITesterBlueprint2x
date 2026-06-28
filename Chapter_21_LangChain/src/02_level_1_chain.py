from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os

load_dotenv()
llm = ChatGroq(model=os.getenv("LLM_MODEL"),temperature=0)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a senior SDET. Be concrete and terse."),
    ("human", "Summarise this bug in one line, then give a likely "
              "root-cause guess: {bug}"),
])
# Wire it together with the pipe. This is LCEL.

chain  = prompt | llm | StrOutputParser()

user_question = input("Enter the Bug Report!")
print(chain.invoke({
    "bug": user_question
}))

