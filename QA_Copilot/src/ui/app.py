import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

import streamlit as st
from src.llm.rag_chain import RAGChain


st.set_page_config(page_title="QA Copilot", page_icon="🤖", layout="wide")

st.title("QA Copilot")
st.caption("Search test cases, generate code, map JIRA tickets, and debug failures")


@st.cache_resource
def load_rag():
    return RAGChain()


rag = load_rag()

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

with st.sidebar:
    st.header("Settings")
    mode = st.selectbox(
        "Mode",
        ["Chat", "Generate Test Code", "Search Only"],
    )
    source_filter = st.selectbox(
        "Search Source",
        ["All", "selenium", "playwright", "test_cases", "pdf_docs", "jira_summaries"],
    )
    n_results = st.slider("Results count", 1, 10, 5)
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.header("Ingestion")
    if st.button("Run Data Ingestion"):
        with st.spinner("Ingesting data..."):
            from src.ingestion.pipeline import ingest_all
            ingest_all()
        st.success("Ingestion complete!")

if prompt := st.chat_input("Ask about test cases, code, or JIRA tickets..."):
    if not isinstance(prompt, str) or not prompt.strip():
        st.error("Please enter text input. This app does not support image input.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    source = None if source_filter == "All" else source_filter

                    if mode == "Chat":
                        history = [
                            {"role": m["role"], "content": m["content"]}
                            for m in st.session_state.messages[-6:]
                        ]
                        answer, _ = rag.ask(prompt, conversation_history=history, n_results=n_results, source=source)
                        st.markdown(answer)
                        st.session_state.messages.append({"role": "assistant", "content": answer})

                    elif mode == "Generate Test Code":
                        framework = "selenium" if source_filter in ["All", "selenium"] else "playwright"
                        code = rag.generate_test_code(prompt, framework=framework, n_results=n_results)
                        st.code(code, language="java" if framework == "selenium" else "typescript")
                        st.session_state.messages.append({"role": "assistant", "content": f"```{framework}\n{code}\n```"})

                    elif mode == "Search Only":
                        context, raw = rag.search(prompt, n_results=n_results, source=source)
                        if context.strip():
                            st.markdown(context)
                            st.session_state.messages.append({"role": "assistant", "content": context})
                        else:
                            st.info("No results found. Try running data ingestion first.")
                except Exception as e:
                    error_msg = str(e)
                    if "clipboard" in error_msg.lower() or "image" in error_msg.lower():
                        st.error("This app does not support image input. Please enter text only.")
                    else:
                        st.error(f"Error: {error_msg}")
