from datetime import datetime, timezone

from bson import ObjectId
from pymongo import ReturnDocument

from src.db.mongo import chats_collection

DEFAULT_TITLE = "New chat"


def create_chat(user_id: str) -> dict:
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user_id,
        "title": DEFAULT_TITLE,
        "is_pinned": False,
        "created_at": now,
        "updated_at": now,
        "messages": [],
    }
    result = chats_collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


def list_chats(user_id: str) -> list[dict]:
    """Pinned chats first, then the rest — each group newest-updated first."""
    return list(
        chats_collection()
        .find({"user_id": user_id})
        .sort([("is_pinned", -1), ("updated_at", -1)])
    )


def get_chat(chat_id: str, user_id: str) -> dict | None:
    """Scoped to user_id so one user can never load another's chat by guessing an ID."""
    return chats_collection().find_one({"_id": ObjectId(chat_id), "user_id": user_id})


def append_message(chat_id: str, user_id: str, role: str, content: str, sources: list[dict] | None = None) -> None:
    message = {
        "role": role,
        "content": content,
        "sources": sources or [],
        "created_at": datetime.now(timezone.utc),
    }
    chats_collection().update_one(
        {"_id": ObjectId(chat_id), "user_id": user_id},
        {
            "$push": {"messages": message},
            "$set": {"updated_at": message["created_at"]},
        },
    )


def set_title(chat_id: str, user_id: str, title: str) -> None:
    chats_collection().update_one(
        {"_id": ObjectId(chat_id), "user_id": user_id},
        {"$set": {"title": title}},
    )


def toggle_pin(chat_id: str, user_id: str) -> bool:
    """Flip is_pinned and return the new value."""
    doc = chats_collection().find_one_and_update(
        {"_id": ObjectId(chat_id), "user_id": user_id},
        [{"$set": {"is_pinned": {"$not": "$is_pinned"}}}],
        return_document=ReturnDocument.AFTER,
    )
    return bool(doc and doc["is_pinned"])


def delete_chat(chat_id: str, user_id: str) -> None:
    chats_collection().delete_one({"_id": ObjectId(chat_id), "user_id": user_id})