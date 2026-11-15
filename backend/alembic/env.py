from sqlalchemy import create_engine, pool

from alembic import context
from app.core.config import get_settings
from app.db.models import Base

settings = get_settings()
url = settings.database_url_unpooled or settings.database_url
if not url:
    raise RuntimeError("Set DATABASE_URL_UNPOOLED (direct connection) for migrations")
if "-pooler" in url:
    raise RuntimeError("Migrations require a direct, non-pooled PostgreSQL connection")


def run_migrations_offline():
    context.configure(
        url=url,
        target_metadata=Base.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    engine = create_engine(url, poolclass=pool.NullPool, hide_parameters=True)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
