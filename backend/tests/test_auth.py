from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password, signing_key
from app.db.models import MasterProfile, RefreshSession, User


def test_register_hashes_password_and_never_returns_it(api, db):
    result = api.register()
    assert result.status_code == 201
    assert "password" not in result.text and "hash" not in result.text
    user = db.scalar(select(User))
    assert user.password_hash.startswith("$2b$")
    assert user.password_hash != "ExamplePass-123"


def test_duplicate_email_is_normalized(api):
    assert api.register(email="Client@Example.com").status_code == 201
    response = api.register(email="client@example.com")
    assert response.status_code == 409
    assert response.json()["error"]["fields"][0]["path"] == "email"


def test_admin_cannot_self_register(api):
    response = api.register(role="ADMIN")
    assert response.status_code == 422


def test_master_registration_creates_private_profile(api, db):
    assert api.register(role="MASTER").status_code == 201
    profile = db.scalar(select(MasterProfile))
    assert profile is not None and not profile.is_published


def test_password_byte_limit_is_not_silent_truncation(api):
    password = "я" * 40
    response = api.register(password=password)
    assert response.status_code == 422 and password not in response.text


def test_login_cookie_is_secure_and_refresh_is_hashed(api, db):
    api.register()
    response = api.login()
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=lax" in cookie
    session = db.scalar(select(RefreshSession))
    assert session.token_hash != api.cookies.get("masterly_refresh")
    assert len(session.token_hash) == 64
    claims = jwt.decode(api.token, signing_key(), algorithms=["HS256"])
    assert set(claims) == {"sub", "role", "iat", "exp", "type"}
    assert claims["exp"] - claims["iat"] == 900


def test_login_errors_do_not_reveal_existing_account(api):
    api.register()
    known = api.login(password="wrong-password").json()["error"]
    unknown = api.login(email="missing@example.com", password="wrong-password").json()["error"]
    assert known == unknown


def test_private_profile_requires_authentication(api):
    response = api.request("GET", "/users/me")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_forged_and_expired_jwt_are_rejected(api):
    api.register()
    api.login()
    valid = api.token
    api.token = ("a" if valid[0] != "a" else "b") + valid[1:]
    assert api.request("GET", "/users/me").status_code == 401
    api.token = jwt.encode(
        {
            "sub": str(uuid4()),
            "role": "CLIENT",
            "iat": datetime.now(UTC) - timedelta(hours=1),
            "exp": datetime.now(UTC) - timedelta(minutes=1),
            "type": "access",
        },
        signing_key(),
        algorithm="HS256",
    )
    assert api.request("GET", "/users/me").status_code == 401


def test_client_cannot_access_master_or_admin(api):
    api.register()
    api.login()
    assert api.request("GET", "/master/profile").status_code == 403
    assert api.request("GET", "/admin/overview").status_code == 403


def test_role_is_checked_in_database_not_only_jwt(api, db):
    api.register()
    api.login()
    user = db.scalar(select(User))
    user.role = "ADMIN"
    db.commit()
    # Even though the old JWT says CLIENT, authorization uses current trusted DB state.
    assert api.request("GET", "/admin/overview").status_code == 200
    user.role = "CLIENT"
    db.commit()
    assert api.request("GET", "/admin/overview").status_code == 403


def test_master_reads_only_own_profile(api):
    api.register(email="first@example.com", role="MASTER")
    api.login(email="first@example.com")
    first = api.request("GET", "/master/profile").json()["id"]
    api.register(email="second@example.com", role="MASTER")
    api.login(email="second@example.com")
    second = api.request("GET", "/master/profile").json()["id"]
    assert first != second


def test_profile_update_cannot_override_role_or_id(api, db):
    api.register()
    api.login()
    response = api.request("PATCH", "/users/me", json={"display_name": "New", "role": "ADMIN"})
    assert response.status_code == 422
    assert db.scalar(select(User)).role == "CLIENT"
    response = api.request("PATCH", "/users/me", json={"display_name": "Новое имя"})
    assert response.status_code == 200 and response.json()["display_name"] == "Новое имя"


def test_refresh_rotation_and_replay_revoke_family(api, db):
    api.register()
    api.login()
    original = api.cookies.get("masterly_refresh")
    rotated = api.request("POST", "/auth/refresh")
    assert rotated.status_code == 200
    replacement = api.cookies.get("masterly_refresh")
    assert replacement != original
    api.cookies.set("masterly_refresh", original, domain="api.example.test", path="/api/v1/auth")
    assert api.request("POST", "/auth/refresh").status_code == 401
    api.cookies.set("masterly_refresh", replacement, domain="api.example.test", path="/api/v1/auth")
    assert api.request("POST", "/auth/refresh").status_code == 401
    assert all(row.revoked_at is not None for row in db.scalars(select(RefreshSession)).all())


def test_logout_revokes_refresh_and_clears_cookie(api):
    api.register()
    api.login()
    response = api.request("DELETE", "/auth/session")
    assert response.status_code == 204 and response.content == b""
    assert api.cookies.get("masterly_refresh") is None
    assert api.request("POST", "/auth/refresh").status_code == 401


def test_missing_and_untrusted_origin_or_csrf_are_rejected(api):
    for headers in [
        {},
        {"Origin": "https://untrusted.example", "X-CSRF-Protection": "1"},
        {"Origin": "http://localhost:5173"},
    ]:
        response = api.request("POST", "/auth/refresh", csrf=False, headers=headers)
        assert response.status_code == 403


def test_blocked_user_loses_access_and_refresh(api, db):
    api.register()
    api.login()
    user = db.scalar(select(User))
    user.is_active = False
    db.commit()
    assert api.request("GET", "/users/me").status_code == 401
    assert api.request("POST", "/auth/refresh").status_code == 401


def test_rate_limit_is_bounded_and_returns_retry_after(api):
    get_settings().auth_rate_limit = 1
    assert api.login().status_code == 401
    response = api.login()
    assert response.status_code == 429 and response.headers["retry-after"] == "60"


def test_admin_can_read_real_overview(api, db):
    db.add(
        User(
            email="admin@example.com",
            display_name="Admin",
            role="ADMIN",
            password_hash=hash_password("ExamplePass-123"),
        )
    )
    db.commit()
    api.login(email="admin@example.com")
    response = api.request("GET", "/admin/overview")
    assert response.status_code == 200 and response.json() == {
        "users": 1,
        "masters": 0,
        "bookings": 0,
    }
