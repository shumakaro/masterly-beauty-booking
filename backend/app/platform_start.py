"""Start the single free Render service after direct-connection migrations."""

import json
import os
import subprocess
import sys


def run_migrations():
    """Блокировка или зависшее соединение не должны бесконечно задерживать запуск."""
    migration_env = os.environ.copy()
    previous = migration_env.get("PGOPTIONS", "")
    migration_env["PGOPTIONS"] = (
        f"{previous} -c lock_timeout=5000 -c statement_timeout=120000"
    ).strip()
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=True,
        env=migration_env,
        timeout=180,
    )


def configure_environment():
    for name in ("DATABASE_URL", "DATABASE_URL_UNPOOLED"):
        url = os.environ.get(name, "")
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                os.environ[name] = "postgresql+psycopg://" + url[len(prefix) :]
                break
    # Render supplies the actual generated URL, including any unique hostname suffix.
    public_url = os.environ.get("RENDER_EXTERNAL_URL")
    if public_url:
        os.environ.setdefault("CORS_ORIGINS", json.dumps([public_url]))


def main():
    configure_environment()
    from app.core.config import get_settings
    from app.core.security import signing_key

    config = get_settings()
    signing_key()  # Refuse to advertise a ready service with missing/weak auth settings.
    if not config.database_url or not config.database_url_unpooled:
        raise RuntimeError("Set both private database URLs before starting the service")
    run_migrations()
    from sqlalchemy.orm import Session

    from app.db.compatibility import schema_revision
    from app.db.session import get_engine

    # Проверяем также подключение приложения, а не только отдельный URL миграций.
    with Session(get_engine()) as db:
        schema_revision(db)
    os.execvp(
        sys.executable,
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            os.environ.get("PORT", "10000"),
            "--workers",
            "1",
            "--proxy-headers",
            "--forwarded-allow-ips",
            "*",
        ],
    )


if __name__ == "__main__":
    main()
