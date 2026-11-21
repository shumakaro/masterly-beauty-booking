"""Совместимость схемы с прикладной логикой текущего выпуска."""

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import Base

# Выпуск A читает прежние данные на обеих схемах; выпуск B требует только 005.
SUPPORTED_REVISIONS = frozenset({"005"})
REVISION_005_COLUMNS = {
    "master_profiles": {"specialization", "experience_years"},
    "portfolio_items": {"title", "description", "category_id"},
    "reviews": {"photo_url", "is_demo"},
}


def schema_revision(db: Session) -> str:
    """Не объявляем приложение готовым только по наличию alembic_version."""
    revisions = db.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
    if len(revisions) != 1 or revisions[0] not in SUPPORTED_REVISIONS:
        raise AppError(503, "SCHEMA_INCOMPATIBLE", "Схема базы несовместима с выпуском приложения.")
    revision = revisions[0]
    required = {table.name: set(table.columns.keys()) for table in Base.metadata.sorted_tables}
    if revision == "005":
        for table, columns in REVISION_005_COLUMNS.items():
            required[table].update(columns)
    # Один запрос метаданных вместо отдельного обращения к каждой таблице.
    columns = db.execute(
        text(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema = current_schema()"
        )
    )
    present: dict[str, set[str]] = {}
    for table, column in columns:
        present.setdefault(table, set()).add(column)
    if any(not names.issubset(present.get(table, set())) for table, names in required.items()):
        raise AppError(503, "SCHEMA_INCOMPATIBLE", "Схема базы несовместима с выпуском приложения.")
    return revision
