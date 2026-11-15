"""Initialize a local .env secret without printing it or replacing existing values."""

import re
from pathlib import Path
from secrets import token_urlsafe


def main():
    root = Path(__file__).resolve().parents[2]
    target = root / ".env"
    content = (
        target.read_text(encoding="utf-8-sig")
        if target.exists()
        else (root / ".env.example").read_text(encoding="utf-8-sig")
    )
    match = re.search(r"^\s*JWT_SECRET\s*=\s*(.*)$", content, flags=re.MULTILINE)
    if match and match.group(1).strip().strip("\"'"):
        print("Existing JWT_SECRET preserved. No secret was printed.")
        return
    line = "JWT_SECRET=" + token_urlsafe(48)
    if match:
        content = content[: match.start()] + line + content[match.end() :]
    else:
        content = content.rstrip() + "\n" + line + "\n"
    target.write_text(content, encoding="utf-8")
    print("Local .env prepared. Keep it private; PostgreSQL URL must be configured separately.")


if __name__ == "__main__":
    main()
