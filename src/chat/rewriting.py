from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from src.core.llm import get_llm

_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Given the conversation history and a follow-up question, rewrite the "
            "follow-up as a standalone question that makes sense without the history. "
            "If the follow-up is already standalone, return it unchanged. "
            "Output ONLY the rewritten question, nothing else.",
        ),
        ("placeholder", "{history}"),
        ("human", "{question}"),
    ]
)


def rewrite_query(history: list[dict], question: str) -> str:
    """Turn a context-dependent follow-up into a standalone search query.

    `history` is [{role, content}, ...] as returned by memory.get_history().
    Falls back to the original question if history is empty or the rewrite fails.
    """
    if not history:
        return question

    try:
        chain = _PROMPT | get_llm() | StrOutputParser()
        as_tuples = [(m["role"], m["content"]) for m in history]
        rewritten = chain.invoke({"history": as_tuples, "question": question}).strip()
        return rewritten or question
    except Exception:
        return question