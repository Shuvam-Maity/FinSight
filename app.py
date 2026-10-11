import asyncio
import json

import streamlit as st

from src import rag
from src.agent.finsight_agent import build_agent, clean_citations
from src.auth.auth import login, signup
from src.chat.titling import generate_title
from src.core.config import get_settings
from src.db.chats import (
    append_message, create_chat, delete_chat, get_chat, list_chats, set_title, toggle_pin,
)
from src.db.mongo import ensure_indexes
from src.memory.redis_memory import append_exchange, clear_history, get_history

st.set_page_config(page_title="FinSight", page_icon="📊", layout="wide")

try:
    get_settings()
except RuntimeError as e:
    st.error(str(e))
    st.stop()

if "indexes_ready" not in st.session_state:
    ensure_indexes()
    st.session_state.indexes_ready = True

st.session_state.setdefault("user", None)
st.session_state.setdefault("current_chat_id", None)
st.session_state.setdefault("uploaded_seen", set())
st.session_state.setdefault("upload_errors", {})


@st.cache_resource
def get_cached_agent():
    return asyncio.run(build_agent())


def _escape_markdown_dollars(text: str) -> str:
    return text.replace("$", "\\$")


# ---------- login / signup ----------

def login_signup_view() -> None:
    st.markdown(
        """
        <style>
        div[data-testid="stForm"] {
            border: 1px solid rgba(128,128,128,0.3);
            border-radius: 12px;
            padding: 1.5rem 1.5rem 0.5rem 1.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    left, center, right = st.columns([1, 1, 1])
    with center:
        st.markdown(
            "<h2 style='text-align: center;'>📊 FinSight</h2>",
            unsafe_allow_html=True,
        )
        tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Username", max_chars=10)
                password = st.text_input("Password", type="password", max_chars=10)
                submitted = st.form_submit_button("Log in", use_container_width=True)
            if submitted:
                try:
                    st.session_state.user = login(username, password)
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

        with tab_signup:
            with st.form("signup_form"):
                username = st.text_input("Choose a username", max_chars=10)
                password = st.text_input("Choose a password", type="password", max_chars=10)
                submitted = st.form_submit_button("Sign up", use_container_width=True)
            if submitted:
                try:
                    st.session_state.user = signup(username, password)
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))


# ---------- sidebar: new chat, pinned/history, rename/pin/delete, logout ----------

def render_chat_row(chat: dict, user_id: str) -> None:
    chat_id = str(chat["_id"])
    is_current = chat_id == st.session_state.current_chat_id

    col_title, col_menu = st.columns([3, 1])
    with col_title:
        clicked = st.button(
            chat["title"],
            key=f"select-{chat_id}",
            use_container_width=True,
            type="primary" if is_current else "secondary",
        )
        if clicked:
            st.session_state.current_chat_id = chat_id
            st.rerun()

    with col_menu:
        with st.popover("⋮"):
            new_title = st.text_input("Rename", value=chat["title"], key=f"rename-{chat_id}")
            if st.button("Save", key=f"save-{chat_id}", use_container_width=True):
                set_title(chat_id, user_id, new_title.strip() or chat["title"])
                st.rerun()

            pin_label = "Unpin" if chat["is_pinned"] else "Pin"
            if st.button(pin_label, key=f"pin-{chat_id}", use_container_width=True):
                toggle_pin(chat_id, user_id)
                st.rerun()

            if st.button("Delete", key=f"delete-{chat_id}", use_container_width=True):
                delete_chat(chat_id, user_id)
                clear_history(chat_id)
                if is_current:
                    st.session_state.current_chat_id = None
                st.rerun()


def render_sidebar(user: dict) -> None:
    with st.sidebar:
        st.markdown(f"**{user['username']}** · {user['role']}")
        if st.button("Log out", use_container_width=True):
            st.session_state.user = None
            st.session_state.current_chat_id = None
            st.rerun()

        st.divider()

        if st.button("+ New chat", use_container_width=True):
            current = (
                get_chat(st.session_state.current_chat_id, user["id"])
                if st.session_state.current_chat_id
                else None
            )
            if not current or current["messages"]:
                chat = create_chat(user["id"])
                st.session_state.current_chat_id = str(chat["_id"])
                st.rerun()

        chats = list_chats(user["id"])
        pinned = [c for c in chats if c["is_pinned"]]
        others = [c for c in chats if not c["is_pinned"]]

        if pinned:
            st.caption("Pinned")
            for c in pinned:
                render_chat_row(c, user["id"])

        if others:
            st.caption("Chats")
            for c in others:
                render_chat_row(c, user["id"])


# ---------- chat pane ----------

def ensure_current_chat(user_id: str) -> dict:
    if st.session_state.current_chat_id:
        chat = get_chat(st.session_state.current_chat_id, user_id)
        if chat:
            return chat

    chats = list_chats(user_id)
    if chats:
        st.session_state.current_chat_id = str(chats[0]["_id"])
        return chats[0]

    chat = create_chat(user_id)  # brand-new user: auto-start a chat
    st.session_state.current_chat_id = str(chat["_id"])
    return chat


def render_sources(sources: list[dict]) -> None:
    if not sources:
        return
    with st.expander(f"Sources ({len(sources)})"):
        for i, s in enumerate(sources, 1):
            if s.get("type") == "web":
                title = s.get("title", "Web result")
                url = s.get("url", "")
                if url:
                    st.markdown(f"**[{i}] [{title}]({url})**")
                else:
                    st.markdown(f"**[{i}] {title}**")
                st.caption(_escape_markdown_dollars(s.get("text", "")))
            elif s.get("type") == "document":
                st.markdown(f"**[{i}] Document**")
                text = s.get("text", "")
                preview = text[:400] + ("…" if len(text) > 400 else "")
                st.caption(_escape_markdown_dollars(preview))
            else:
                page = f" · page {s.get('page')}" if s.get("page") else ""
                st.markdown(f"**[{i}] {s.get('filename', 'Document')}**{page}")
                st.caption(_escape_markdown_dollars(s.get("text", "")[:400]))


_TOOL_LABELS = {
    "search_documents": "Searching documents...",
    "calculate": "Calculating...",
    "tavily_search": "Searching the web...",
    "tavily_extract": "Reading a web page...",
}


def _parse_tavily_sources(raw) -> list[dict]:
    """Tavily's MCP tool returns a list of content blocks; the 'text' block is a
    JSON string with a 'results' array, each a distinct web result."""
    try:
        text_block = raw[0]["text"] if isinstance(raw, list) else raw
        data = json.loads(text_block)
        results = data.get("results", [])
        return [
            {
                "type": "web",
                "title": r.get("title", "Untitled"),
                "url": r.get("url", ""),
                "text": r.get("content", "")[:400],
            }
            for r in results
        ]
    except Exception:
        return [{"type": "web", "text": str(raw)[:500]}]


def _dedupe_sources(sources: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for s in sources:
        key = (s.get("type", ""), s.get("url", "") or s.get("text", "")[:200])
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return unique


async def _run_agent(agent, messages: list[dict], status) -> dict:
    """Stream the agent's steps, updating `status` live, and collect sources."""
    sources: list[dict] = []
    final_answer = ""

    async for chunk in agent.astream({"messages": messages}, stream_mode="updates"):
        for node_name, node_output in chunk.items():
            msgs = node_output.get("messages", [])
            for msg in msgs:
                tool_calls = getattr(msg, "tool_calls", None)
                if tool_calls:
                    for tc in tool_calls:
                        label = _TOOL_LABELS.get(tc["name"], f"Using {tc['name']}...")
                        status.update(label=label)

                if getattr(msg, "type", None) == "tool":
                    if msg.name == "search_documents" and "No relevant" not in msg.content:
                        sources.append({"type": "document", "text": msg.content})
                    elif msg.name in ("tavily_search", "tavily_extract"):
                        sources.extend(_parse_tavily_sources(msg.content))

                if getattr(msg, "type", None) == "ai" and msg.content and not getattr(msg, "tool_calls", None):
                    final_answer = msg.content

    status.update(label="Done", state="complete")
    return {"answer": final_answer, "sources": _dedupe_sources(sources)}


def render_chat(user: dict) -> None:
    chat = ensure_current_chat(user["id"])
    chat_id = str(chat["_id"])
    is_first_exchange = chat["title"] == "New chat" and not chat["messages"]

    st.title(chat["title"])

    for m in chat["messages"]:
        with st.chat_message(m["role"]):
            st.markdown(_escape_markdown_dollars(m["content"]))
            render_sources(m.get("sources", []))

    question = st.chat_input("Ask about a financial report, or anything else")
    if not question:
        return

    append_message(chat_id, user["id"], "user", question)
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        text, sources = "", []
        try:
            agent = get_cached_agent()
            history = get_history(chat_id, user["id"])
            lc_messages = [{"role": m["role"], "content": m["content"]} for m in history]
            lc_messages.append({"role": "user", "content": question})

            with st.status("Thinking...", expanded=False) as status:
                result = asyncio.run(_run_agent(agent, lc_messages, status))

            text = clean_citations(result["answer"])
            sources = result["sources"]
            st.markdown(_escape_markdown_dollars(text))
            render_sources(sources)
        except Exception as e:
            if "rate_limit_exceeded" in str(e) or "413" in str(e):
                text = (
                    "That question needs more context than I can process right now. "
                    "Try asking something more specific, or wait a moment and try again."
                )
            else:
                text = f"Sorry, something went wrong: {e}"
            st.error(text)

    append_message(chat_id, user["id"], "assistant", text, sources)
    append_exchange(chat_id, user["id"], question, text)

    if is_first_exchange:
        try:
            title = generate_title(question)
            set_title(chat_id, user["id"], title)
        except Exception as e:
            st.error(f"Could not generate a chat title: {e}")

    st.rerun()


# ---------- admin: document management ----------

def render_admin_documents() -> None:
    st.header("Manage documents")

    types = sorted(ext.lstrip(".") for ext in rag.SUPPORTED_EXTENSIONS)
    files = st.file_uploader(
        "Upload documents", type=types, accept_multiple_files=True, key="admin-uploader"
    )
    for f in files or []:
        key = getattr(f, "file_id", None) or f"{f.name}-{f.size}"
        if key in st.session_state.uploaded_seen:
            continue
        with st.spinner(f"Indexing {f.name}..."):
            try:
                rag.ingest_file(f.name, f.getvalue())
            except ValueError as e:
                st.session_state.upload_errors[key] = f"{f.name}: {e}"
            except Exception as e:
                st.session_state.upload_errors[key] = f"{f.name}: could not be indexed ({e})"
        st.session_state.uploaded_seen.add(key)

    for msg in st.session_state.upload_errors.values():
        st.error(msg)

    st.divider()

    docs = rag.list_documents()
    if not docs:
        st.info("No documents uploaded yet.")
        return

    header = st.columns([4, 2, 3, 2])
    header[0].markdown("**Filename**")
    header[1].markdown("**Chunks**")
    header[2].markdown("**Uploaded**")

    for doc in docs:
        col1, col2, col3, col4 = st.columns([4, 2, 3, 2])
        col1.write(doc["filename"])
        col2.write(doc["chunk_count"])
        col3.write(doc["uploaded_at"].strftime("%Y-%m-%d %H:%M"))
        if col4.button("Delete", key=f"del-doc-{doc['_id']}"):
            rag.delete_document(doc["_id"])
            st.rerun()


# ---------- run ----------

if not st.session_state.user:
    login_signup_view()
else:
    current_user = st.session_state.user
    render_sidebar(current_user)

    if current_user["role"] == "admin":
        tab_chat, tab_docs = st.tabs(["Chat", "Manage documents"])
        with tab_chat:
            render_chat(current_user)
        with tab_docs:
            render_admin_documents()
    else:
        render_chat(current_user)