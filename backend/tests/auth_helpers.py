import asyncio

import httpx


class AuthAPI:
    def __init__(self, app):
        self.app = app
        self.cookies = httpx.Cookies()
        self.token = None

    def request(self, method, path, *, csrf=True, headers=None, **kwargs):
        request_headers = (
            {"Origin": "http://localhost:5173", "X-CSRF-Protection": "1"} if csrf else {}
        )
        if self.token:
            request_headers["Authorization"] = f"Bearer {self.token}"
        request_headers.update(headers or {})

        async def execute():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=self.app),
                base_url="https://api.example.test",
                cookies=self.cookies,
            ) as client:
                response = await client.request(
                    method, "/api/v1" + path, headers=request_headers, **kwargs
                )
                self.cookies = client.cookies
                return response

        return asyncio.run(execute())

    def register(self, email="client@example.com", role="CLIENT", **extra):
        return self.request(
            "POST",
            "/auth/register",
            json={
                "email": email,
                "display_name": "Test User",
                "role": role,
                "password": "ExamplePass-123",
                **extra,
            },
        )

    def login(self, email="client@example.com", password="ExamplePass-123"):
        response = self.request("POST", "/auth/token", json={"email": email, "password": password})
        if response.status_code == 200:
            self.token = response.json()["access_token"]
        return response
