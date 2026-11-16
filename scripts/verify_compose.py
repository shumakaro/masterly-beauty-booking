"""Exercise real packaged images through Nginx; used only with disposable CI data."""

import argparse
import http.cookiejar
import json
import secrets
import ssl
import subprocess
import tempfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, HTTPSHandler, Request, build_opener


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", default="http://127.0.0.1:8080")
    parser.add_argument("--ca-file")
    args = parser.parse_args()
    context = ssl.create_default_context(cafile=args.ca_file)
    cookies = http.cookiejar.CookieJar()
    client = build_opener(HTTPSHandler(context=context), HTTPCookieProcessor(cookies))
    origin = args.origin

    def request(path, payload=None, token=None):
        headers = {"Origin": origin, "X-CSRF-Protection": "1"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if payload is not None:
            headers["Content-Type"] = "application/json"
        req = Request(
            origin + path,
            json.dumps(payload).encode() if payload is not None else None,
            headers,
        )
        return client.open(req, timeout=20)

    for route in ["/", "/masters", "/master/dashboard", "/bookings/unknown"]:
        with request(route) as response:
            assert response.status == 200 and b'<div id="root">' in response.read()
            assert response.headers["Content-Security-Policy"]
            assert response.headers["X-Frame-Options"] == "DENY"
            if origin.startswith("https:"):
                assert response.headers["Strict-Transport-Security"]
    with request("/api/v1/ready") as response:
        assert json.load(response)["status"] == "ok"
        assert response.headers["Cache-Control"] == "no-store"
    with request("/openapi.json") as response:
        assert "/api/v1/bookings" in json.load(response)["paths"]
    try:
        request("/api/v1/does-not-exist")
    except HTTPError as error:
        assert error.code == 404 and json.load(error)["error"]["code"] == "HTTP_ERROR"
    else:
        raise AssertionError("An unknown API route must not fall back to SPA HTML")

    email, password = (
        f"container-{secrets.token_hex(8)}@example.com",
        secrets.token_urlsafe(32),
    )
    with request(
        "/api/v1/auth/register",
        {
            "email": email,
            "password": password,
            "display_name": "Container smoke",
            "role": "CLIENT",
        },
    ) as response:
        assert response.status == 201
    with request(
        "/api/v1/auth/token", {"email": email, "password": password}
    ) as response:
        session = json.load(response)
    refresh = next(cookie for cookie in cookies if cookie.name == "masterly_refresh")
    assert refresh.secure == origin.startswith("https:")
    assert refresh.has_nonstandard_attr("HttpOnly")
    with request("/api/v1/users/me", token=session["access_token"]) as response:
        assert json.load(response)["email"] == email
    with request("/api/v1/auth/refresh", {}) as response:
        assert json.load(response)["user"]["email"] == email

    compose = ["docker", "compose", "--env-file", ".env.compose"]
    subprocess.run(compose + ["restart", "db", "api"], check=True)
    subprocess.run(
        compose + ["up", "-d", "--wait", "--wait-timeout", "120"], check=True
    )
    with request(
        "/api/v1/auth/token", {"email": email, "password": password}
    ) as response:
        assert json.load(response)["user"]["email"] == email

    with tempfile.TemporaryDirectory() as folder:
        dump = str(Path(folder) / "masterly.dump")
        subprocess.run(
            ["python", "scripts/database_backup.py", "--file", dump], check=True
        )
        subprocess.run(
            ["python", "scripts/database_backup.py", "--file", dump, "--restore-test"],
            check=True,
        )
    result = subprocess.check_output(
        compose
        + [
            "exec",
            "-T",
            "db",
            "psql",
            "-U",
            "postgres",
            "-d",
            "masterly_restore_test",
            "-tAc",
            "SELECT count(*) FROM users WHERE display_name = 'Container smoke'",
        ]
    )
    assert int(result.strip()) >= 1
    print(
        "PASS: packaged SPA/API, security headers, auth/refresh cookie, restart persistence, backup/restore"
    )


if __name__ == "__main__":
    main()
