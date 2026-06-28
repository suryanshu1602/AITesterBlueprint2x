from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain.agents import create_agent
import os
from langchain_groq import ChatGroq


load_dotenv()

llm = ChatGroq(model=os.getenv("LLM_MODEL"),temperature=0)



@tool
def get_test_history(test_id: str) -> str:
    """Return the recent Pass or Fail history of a given test by ID."""
    fake_db = {
        "TC-101": "FAIL, PASS, FAIL, FAIL, PASS",
        "TC-102": "PASS, PASS, PASS, PASS, PASS",
    }
    # Make the real call to the Database where you have all the Testcases,
    # Zephyr, TMT, Bugzilla, JIRA, Xray
    return fake_db.get(test_id, "No history found.")


tools = [get_test_history]

# langchain v1: create_agent replaces create_tool_calling_agent + AgentExecutor.
# The scratchpad / tool-loop is handled internally.
agent = create_agent(
    llm,
    tools,
    system_prompt="You are a QA assistant. Use tools when you need data.",
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "Is test TC-101 flaky? Explain why."}]}
)
print(result["messages"][-1].content)
