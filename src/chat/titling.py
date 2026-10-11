from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from src.core.llm import get_llm

MAX_TITLE_LENGTH = 60

_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Write a short chat title (max 6 words) summarizing what the user is "
            "asking about below. Output ONLY the title text: no quotes, no punctuation "
            "at the end, no prefix like 'Title:'.",
        ),
        ("human", "{message}"),
    ]
)


def generate_title(first_message: str) -> str:
    """Raises on failure — the caller decides how to surface that to the user."""
    chain = _PROMPT | get_llm() | StrOutputParser()
    title = chain.invoke({"message": first_message}).strip().strip('"').strip("'")
    if not title:
        raise ValueError("Model returned an empty title")
    return title[:MAX_TITLE_LENGTH]