"""One-time script to create the fixed admin account.

Run manually from the project root:
    python scripts/create_admin.py
"""

import getpass

from src.auth.auth import USERNAME_MAX_LEN, PASSWORD_MAX_LEN, _validate_credentials
from src.db.users import create_user, get_user_by_username
from src.auth.auth import _hash_password


def main() -> None:
    print("Create the admin account")
    print(f"(username and password must each be at most {USERNAME_MAX_LEN} characters)\n")

    username = input("Admin username: ").strip()
    if get_user_by_username(username):
        print(f"A user named '{username}' already exists. Aborting.")
        return

    password = getpass.getpass("Admin password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match. Aborting.")
        return

    error = _validate_credentials(username, password)
    if error:
        print(error)
        return

    user_id = create_user(username, _hash_password(password), role="admin")
    print(f"\nAdmin account created (id: {user_id}). You can now log in as '{username}'.")


if __name__ == "__main__":
    main()