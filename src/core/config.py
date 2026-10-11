import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Silence the Windows symlink warning from huggingface_hub (harmless; cache still works).
# Must be set before huggingface_hub is imported, which happens when fastembed loads.
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

# Load .env from the project root, no matter where the app is launched from
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing environment variable '{name}'. Add it to your .env file."
        )
    return value


@dataclass(frozen=True)
class Settings:
    # Credentials (required)
    qdrant_url: str
    qdrant_api_key: str
    groq_api_key: str
    mongodb_uri: str
    mongodb_db_name: str
    redis_url: str
    tavily_api_key: str

    # Models
    groq_model: str = "openai/gpt-oss-120b"
    embed_model: str = "BAAI/bge-small-en-v1.5"
    embed_dim: int = 384  # must match embed_model; changing the model means a new collection
    embed_cache_dir: Path = PROJECT_ROOT / ".cache" / "fastembed"

    # Vector store
    collection_name: str = "documents"

    # RAG
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k: int = 3
    score_threshold: float = 0.7

    # Memory
    memory_max_exchanges: int = 5
    memory_ttl_seconds: int = 300  # 5 minutes


@lru_cache
def get_settings() -> Settings:
    return Settings(
        qdrant_url=_require("QDRANT_URL"),
        qdrant_api_key=_require("QDRANT_API_KEY"),
        groq_api_key=_require("GROQ_API_KEY"),
        mongodb_uri=_require("MONGODB_URI"),
        mongodb_db_name=os.getenv("MONGODB_DB_NAME") or "chat_rag",
        redis_url=_require("REDIS_URL"),
        tavily_api_key=_require("TAVILY_API_KEY"),
        groq_model=os.getenv("GROQ_MODEL") or Settings.groq_model,
    )