from functools import lru_cache

from langchain_groq import ChatGroq

from src.core.config import get_settings


@lru_cache
def get_llm(temperature: float = 0.0) -> ChatGroq:
    """Shared Groq chat model. RAG, agents, and plain chat all use this."""
    s = get_settings()
    return ChatGroq(model=s.groq_model, api_key=s.groq_api_key, temperature=temperature)