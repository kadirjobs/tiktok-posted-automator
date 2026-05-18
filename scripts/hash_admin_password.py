#!/usr/bin/env python3
"""Generate bcrypt hash for ADMIN_PASSWORD_HASH in .env."""

import sys

from app.api.deps import hash_admin_password


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/hash_admin_password.py <plain_password>")
        sys.exit(1)
    print(hash_admin_password(sys.argv[1]))


if __name__ == "__main__":
    main()
