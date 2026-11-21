from auth_helpers import AuthAPI
from sqlalchemy.exc import OperationalError

from app.db.compatibility import SUPPORTED_REVISIONS
from app.db.session import get_db
from app.main import create_app


def test_readiness_checks_the_migrated_database(api):
    response = api.request("GET", "/ready")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "masterly-api",
        "schema_revision": "005",
        "compatible_revisions": sorted(SUPPORTED_REVISIONS),
    }


def test_readiness_failure_is_sanitized():
    app = create_app()

    def unavailable():
        raise OperationalError("private connection details", {}, Exception("private password"))

    app.dependency_overrides[get_db] = unavailable
    response = AuthAPI(app).request("GET", "/ready")
    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"
    assert "private" not in response.text
