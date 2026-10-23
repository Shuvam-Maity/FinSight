"""Keeps the free-tier Redis Cloud database from being flagged/deleted due to
inactivity. Run on a schedule (see .github/workflows/keepalive.yml).
"""

import os
import sys

import redis


def main() -> None:
    url = os.environ["REDIS_URL"]
    client = redis.from_url(url, decode_responses=True)

    client.set("_keepalive", "ping", ex=60)
    value = client.get("_keepalive")
    print(f"Redis ping OK - wrote and read back: {value!r}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Redis ping FAILED: {e}", file=sys.stderr)
        sys.exit(1)