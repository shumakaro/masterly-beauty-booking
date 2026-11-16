from contextlib import contextmanager

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.core.errors import AppError


def found(value):
    if value is None:
        raise AppError(404, "NOT_FOUND", "Объект не найден.")
    return value


def apply_patch(entity, values):
    for name, value in values.items():
        setattr(entity, name, value)


@contextmanager
def change(db, code="DATA_CONFLICT", message="Изменение конфликтует с существующими данными."):
    try:
        yield
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(409, code, message) from exc
    except ValidationError as exc:
        db.rollback()
        fields = [
            {"path": ".".join(map(str, item["loc"])), "message": "Проверьте значение поля."}
            for item in exc.errors()
        ]
        raise AppError(422, "VALIDATION_ERROR", "Проверьте параметры изменения.", fields) from exc
    except Exception:
        db.rollback()
        raise
