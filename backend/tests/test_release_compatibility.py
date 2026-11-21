"""Проверки перехода A/B выполняются только на изолированной PostgreSQL из fixtures."""

import os
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from alembic.config import Config
from sqlalchemy import select, text

from alembic import command
from app.db.compatibility import SUPPORTED_REVISIONS
from app.db.models import MasterProfile
from app.platform_start import main, run_migrations


@pytest.mark.parametrize("revision", ["004", "005"])
def test_readiness_and_legacy_data_across_release_schemas(api, db, offer, revision):
    master_id = offer[1].id
    offer[1].is_published = True
    expected = (offer[1].user_id, offer[1].bio, offer[1].timezone, offer[1].address)
    db.commit()
    cfg = Config("alembic.ini")
    try:
        command.downgrade(cfg, revision)
        response = api.request("GET", "/ready")
        if revision in SUPPORTED_REVISIONS:
            assert response.status_code == 200
            assert response.json()["schema_revision"] == revision
            assert api.request("GET", f"/masters/{master_id}").status_code == 200
        else:
            assert response.status_code == 503
            assert response.json()["error"]["code"] == "SCHEMA_INCOMPATIBLE"
        actual = db.execute(
            select(
                MasterProfile.user_id,
                MasterProfile.bio,
                MasterProfile.timezone,
                MasterProfile.address,
            ).where(MasterProfile.id == master_id)
        ).one()
        assert tuple(actual) == expected
    finally:
        db.rollback()
        command.upgrade(cfg, "head")


@pytest.mark.parametrize("revision", ["003", "unknown"])
def test_readiness_rejects_incompatible_revision(api, db, revision):
    db.execute(text("UPDATE alembic_version SET version_num = :revision"), {"revision": revision})
    db.commit()
    try:
        response = api.request("GET", "/ready")
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "SCHEMA_INCOMPATIBLE"
        assert response.headers["cache-control"] == "no-store"
    finally:
        db.rollback()
        db.execute(text("UPDATE alembic_version SET version_num = '005'"))
        db.commit()


def test_readiness_rejects_incomplete_schema(api, db):
    db.execute(text("ALTER TABLE reviews RENAME COLUMN photo_url TO temporary_photo"))
    db.commit()
    try:
        assert api.request("GET", "/ready").status_code == 503
    finally:
        db.rollback()
        db.execute(text("ALTER TABLE reviews RENAME COLUMN temporary_photo TO photo_url"))
        db.commit()


def test_a_to_b_to_a_requires_no_database_downgrade(api, db, offer, tmp_path):
    """Обе версии знают 005; повторный upgrade по тому же графу не меняет данные."""
    identifier = offer[1].id
    db.commit()
    before = db.execute(
        text("SELECT bio FROM master_profiles WHERE id = :id"), {"id": identifier}
    ).scalar_one()
    db.rollback()
    copied = tmp_path / "alembic"
    shutil.copytree(Path("alembic"), copied, ignore=shutil.ignore_patterns("__pycache__"))
    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", str(copied))
    for _ in range(2):
        command.upgrade(cfg, "head")
        assert api.request("GET", "/ready").status_code == 200
        assert (
            db.execute(
                text("SELECT bio FROM master_profiles WHERE id = :id"), {"id": identifier}
            ).scalar_one()
            == before
        )
        db.rollback()


def test_migration_timeouts_are_local_to_migration_subprocess(monkeypatch):
    monkeypatch.setenv("PGOPTIONS", "-c application_name=masterly")
    with patch("app.platform_start.subprocess.run") as run:
        run_migrations()
    kwargs = run.call_args.kwargs
    assert kwargs["check"] is True and kwargs["timeout"] == 180
    assert "lock_timeout=5000" in kwargs["env"]["PGOPTIONS"]
    assert "statement_timeout=120000" in kwargs["env"]["PGOPTIONS"]
    assert os.environ["PGOPTIONS"] == "-c application_name=masterly"


def test_render_preview_refuses_start_before_any_migration(monkeypatch):
    monkeypatch.setenv("IS_PULL_REQUEST", "true")
    with patch("app.platform_start.run_migrations") as migrate:
        with pytest.raises(RuntimeError, match="PR previews are disabled"):
            main()
    migrate.assert_not_called()
