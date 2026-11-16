"""Create private Compose settings without printing credentials or overwriting a file."""

import argparse
import json
import os
import re
import secrets
from pathlib import Path
from urllib.parse import urlsplit


def settings(origin: str) -> dict[str, str]:
    parsed = urlsplit(origin)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", parsed.hostname)
        or parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
        or any(char in origin for char in '\n\r$"\\')
    ):
        raise ValueError("Use an exact HTTP(S) origin without path or credentials")
    local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if not local and parsed.scheme != "https":
        raise ValueError("A public deployment requires HTTPS")
    return {
        "POSTGRES_ADMIN_PASSWORD": secrets.token_hex(32),
        "POSTGRES_PASSWORD": secrets.token_hex(32),
        "JWT_SECRET": secrets.token_hex(48),
        "COOKIE_SECURE": str(parsed.scheme == "https").lower(),
        "CORS_ORIGINS": json.dumps([origin], separators=(",", ":")),
        "PUBLIC_HOST": parsed.hostname,
        "WEB_BIND": "127.0.0.1",
        "WEB_PORT": "8080",
        "IMAGE_TAG": "local",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", default="http://127.0.0.1:8080")
    parser.add_argument("--output", type=Path, default=Path(".env.compose"))
    args = parser.parse_args()
    values = settings(args.origin)
    # O_EXCL refuses replacement; mode 0600 restricts new files on Unix hosts.
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
        output.write("".join(f"{name}={value}\n" for name, value in values.items()))
    print(f"Created private settings: {args.output}. Credentials were not displayed.")


if __name__ == "__main__":
    main()
