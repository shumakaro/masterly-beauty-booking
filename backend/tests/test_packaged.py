import asyncio
import json

import httpx
import pytest

from app.core.config import get_settings
from app.main import create_app
from app.platform_start import configure_environment


@pytest.fixture
def packaged(tmp_path, monkeypatch):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log('packaged')", encoding="utf-8")
    (tmp_path / "index.html").write_text('<div id="root">Packaged app</div>', encoding="utf-8")
    monkeypatch.setenv("STATIC_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield create_app()
    get_settings.cache_clear()


def request(app, path):
    async def execute():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://app.example.test"
        ) as client:
            return await client.get(path)

    return asyncio.run(execute())


@pytest.mark.parametrize("path", ["/", "/masters", "/master/profile", "/bookings/unknown"])
def test_spa_direct_links_keep_csp_and_avoid_stale_html(packaged, path):
    response = request(packaged, path)
    assert response.status_code == 200 and "Packaged app" in response.text
    assert response.headers["cache-control"] == "no-cache"
    assert "unsafe-eval" not in response.headers["content-security-policy"]
    assert response.headers["x-frame-options"] == "DENY"


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/unknown",
        "/api/unknown",
        "/api",
        "/api%5cv1%5cunknown",
        "/assets/missing.js",
        "/assets/missing",
        "/images/missing",
    ],
)
def test_unknown_api_and_assets_never_return_spa_html(packaged, path):
    response = request(packaged, path)
    assert response.status_code == 404
    assert "Packaged app" not in response.text
    assert response.json()["error"]["code"] == "HTTP_ERROR"


def test_asset_cache_and_api_route_precedence(packaged):
    response = request(packaged, "/assets/app.js")
    assert response.status_code == 200 and "immutable" in response.headers["cache-control"]
    response = request(packaged, "/api/v1/health")
    assert response.status_code == 200 and response.json()["status"] == "ok"
    assert response.headers["cache-control"] == "no-store"


def test_render_origin_and_driver_are_derived_without_overwriting_explicit_cors(monkeypatch):
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://masterly-unique.onrender.com")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    for key in ["DATABASE_URL", "DATABASE_URL_UNPOOLED"]:
        monkeypatch.setenv(key, "postgresql://user:private@db.example/db?sslmode=require")
    configure_environment()
    import os

    assert json.loads(os.environ["CORS_ORIGINS"]) == ["https://masterly-unique.onrender.com"]
    assert os.environ["DATABASE_URL"].startswith("postgresql+psycopg://")
    assert os.environ["DATABASE_URL_UNPOOLED"].endswith("?sslmode=require")
    monkeypatch.setenv("CORS_ORIGINS", '["https://custom.example"]')
    configure_environment()
    assert json.loads(os.environ["CORS_ORIGINS"]) == ["https://custom.example"]
