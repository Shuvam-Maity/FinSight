import bcrypt

from src.db.users import create_user, get_user_by_username

USERNAME_MAX_LEN = 10
PASSWORD_MAX_LEN = 10


def _hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())


def _check_password(password: str, password_hash: bytes) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash)


def _validate_credentials(username: str, password: str) -> str | None:
    if not username or not password:
        return "Username and password are required."
    if len(username) > USERNAME_MAX_LEN:
        return f"Username must be at most {USERNAME_MAX_LEN} characters."
    if len(password) > PASSWORD_MAX_LEN:
        return f"Password must be at most {PASSWORD_MAX_LEN} characters."
    return None


def signup(username: str, password: str) -> dict:
    """Create a new 'user'-role account. Returns the public user dict.

    Raises ValueError on validation failure or a taken username.
    """
    error = _validate_credentials(username, password)
    if error:
        raise ValueError(error)

    user_id = create_user(username, _hash_password(password), role="user")
    return {"id": user_id, "username": username, "role": "user"}


def login(username: str, password: str) -> dict:
    """Verify credentials. Returns the public user dict.

    Raises ValueError if the username doesn't exist or the password is wrong
    (same message either way, so login can't be used to enumerate usernames).
    """
    user = get_user_by_username(username)
    if not user or not _check_password(password, user["password_hash"]):
        raise ValueError("Invalid username or password.")
    return {"id": str(user["_id"]), "username": user["username"], "role": user["role"]}