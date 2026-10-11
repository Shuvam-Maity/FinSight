from datetime import datetime, timezone
from typing import TypedDict

from pymongo.errors import DuplicateKeyError

from src.db.mongo import users_collection


class User(TypedDict):
    username: str
    password_hash: bytes
    role: str  # "admin" | "user"
    created_at: datetime


def create_user(username: str, password_hash: bytes, role: str = "user") -> str:
    """Insert a new user. Raises ValueError if the username is taken."""
    doc: User = {
        "username": username,
        "password_hash": password_hash,
        "role": role,
        "created_at": datetime.now(timezone.utc),
    }
    try:
        result = users_collection().insert_one(doc)
    except DuplicateKeyError:
        raise ValueError(f"Username '{username}' is already taken")
    return str(result.inserted_id)


def get_user_by_username(username: str) -> dict | None:
    return users_collection().find_one({"username": username})