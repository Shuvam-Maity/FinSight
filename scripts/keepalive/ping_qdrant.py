"""Keeps the free-tier Qdrant Cloud cluster from being auto-paused due to
inactivity. Run on a schedule (see .github/workflows/keepalive.yml).

Reads credentials from environment variables rather than .env, since this
runs inside GitHub Actions, not locally.
"""

import os
import sys

from qdrant_client import QdrantClient


def main() -> None:
    url = os.environ["QDRANT_URL"]
    api_key = os.environ["QDRANT_API_KEY"]

    client = QdrantClient(url=url, api_key=api_key)
    collections = client.get_collections()
    print(f"Qdrant ping OK — {len(collections.collections)} collection(s) found.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Qdrant ping FAILED: {e}", file=sys.stderr)
        sys.exit(1)