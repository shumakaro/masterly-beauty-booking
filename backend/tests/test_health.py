import asyncio

import httpx

from app.main import create_app


def request(method: str, path: str, **kwargs) -> httpx.Response:
    async def execute() -> httpx.Response:
        transport = httpx.ASGITransport(app=create_app())
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(execute())


def test_health_contract():
    response = request("GET", "/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "masterly-api"}


def test_cors_rejects_untrusted_origin():
    response = request(
        "OPTIONS",
        "/api/v1/health",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_unexpected_failure_is_private_and_does_not_disclose_internal_details():
    app = create_app()

    @app.get("/api/v1/test-failure")
    def failure():
        raise RuntimeError("private-database-password")

    async def execute():
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/api/v1/test-failure")

    response = asyncio.run(execute())
    assert response.status_code == 500
    assert "private-database-password" not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.json()["request_id"] == response.headers["x-request-id"]
