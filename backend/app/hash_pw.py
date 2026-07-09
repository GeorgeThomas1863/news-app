"""CLI: prints a bcrypt hash for the .env PW_HASH value.

Usage: uv run python -m app.hash_pw
"""

import getpass

import bcrypt


def main():
    password = getpass.getpass("Password to hash: ")
    if not password:
        print("empty password — aborting")
        return
    print(bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode())


if __name__ == "__main__":
    main()
