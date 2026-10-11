import json
from functools import lru_cache

import redis

from src.core.config import get_settings
from src.db.chats import get_chat

_KEY_PREFIX = "chat_history:"


@lru_cache
def get_redis() -> redis.Redis:
    return redis.from_url(get_settings().redis_url, decode_responses=True)


def _key(chat_id: str) -> str:
    return f"{_KEY_PREFIX}{chat_id}"


def _from_mongo(chat_id: str, user_id: str) -> list[dict]:
    """Rebuild recent history from MongoDB's full message log for this chat."""
    chat = get_chat(chat_id, user_id)
    if not chat:
        return []
    s = get_settings()
    recent_messages = chat["messages"][-(s.memory_max_exchanges * 2):]
    return [{"role": m["role"], "content": m["content"]} for m in recent_messages]


def get_history(chat_id: str, user_id: str) -> list[dict]:
    """Last N exchanges as [{role, content}, ...], oldest first.

    Reads from Redis; if the key is missing (expired, evicted, or a fresh
    session), rebuilds it from MongoDB and re-populates Redis.
    """
    r = get_redis()
    raw = r.get(_key(chat_id))
    if raw is not None:
        r.expire(_key(chat_id), get_settings().memory_ttl_seconds)  # refresh TTL on read
        return json.loads(raw)

    history = _from_mongo(chat_id, user_id)
    if history:
        _write(chat_id, history)
    return history


def append_exchange(chat_id: str, user_id: str, question: str, answer: str) -> None:
    """Add a Q/A pair, trimmed to the last N exchanges, and refresh the TTL."""
    history = get_history(chat_id, user_id)
    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer})

    s = get_settings()
    max_messages = s.memory_max_exchanges * 2
    _write(chat_id, history[-max_messages:])


def _write(chat_id: str, history: list[dict]) -> None:
    get_redis().set(
        _key(chat_id), json.dumps(history), ex=get_settings().memory_ttl_seconds
    )


def clear_history(chat_id: str) -> None:
    get_redis().delete(_key(chat_id))