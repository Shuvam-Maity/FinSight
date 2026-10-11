from functools import lru_cache

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from src.core.config import get_settings


@lru_cache
def get_client() -> MongoClient:
    s = get_settings()
    return MongoClient(s.mongodb_uri)


@lru_cache
def get_db() -> Database:
    s = get_settings()
    return get_client()[s.mongodb_db_name]


def users_collection() -> Collection:
    return get_db()["users"]


def chats_collection() -> Collection:
    return get_db()["chats"]


def documents_collection() -> Collection:
    return get_db()["documents"]


def ensure_indexes() -> None:
    """Call once at app startup. Safe to call repeatedly (no-op if already present)."""
    users_collection().create_index("username", unique=True)
    chats_collection().create_index([("user_id", 1), ("is_pinned", -1), ("updated_at", -1)])
    documents_collection().create_index("uploaded_at")