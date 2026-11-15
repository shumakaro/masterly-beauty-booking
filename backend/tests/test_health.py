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
