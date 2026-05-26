"""Tests for the web dashboard with basic auth and job listing."""

import base64
import os
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from clipper_agency.dashboard.auth import authenticate, check_auth, requires_auth
from clipper_agency.dashboard.app import app as dash_app

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Test credentials
TEST_USER = "admin"
TEST_PASS = "changeme"


class TestAuthFailsClosed:
    """auth fails closed when DASHBOARD_USERNAME or DASHBOARD_PASSWORD is unset."""

    def test_fails_when_username_unset(self):
        with patch.dict(os.environ, {}, clear=True):
            assert check_auth("admin", "changeme") is False

    def test_fails_when_password_unset(self):
        with patch.dict(os.environ, {"DASHBOARD_USERNAME": "admin"}, clear=True):
            assert check_auth("admin", "any") is False

    def test_fails_when_both_unset(self):
        with patch.dict(os.environ, {}, clear=True):
            assert check_auth("any", "any") is False


def test_check_auth_valid():
    """check_auth returns True when credentials match env vars."""
    with patch.dict(os.environ, {"DASHBOARD_USERNAME": TEST_USER, "DASHBOARD_PASSWORD": TEST_PASS}):
        assert check_auth(TEST_USER, TEST_PASS) is True


def test_check_auth_invalid_username():
    """check_auth returns False for wrong username."""
    with patch.dict(os.environ, {"DASHBOARD_USERNAME": TEST_USER, "DASHBOARD_PASSWORD": TEST_PASS}):
        assert check_auth("hacker", TEST_PASS) is False


def test_check_auth_invalid_password():
    """check_auth returns False for wrong password."""
    with patch.dict(os.environ, {"DASHBOARD_USERNAME": TEST_USER, "DASHBOARD_PASSWORD": TEST_PASS}):
        assert check_auth(TEST_USER, "wrongpass") is False


def test_check_auth_custom_env():
    """check_auth respects custom env vars."""
    with patch.dict(os.environ, {"DASHBOARD_USERNAME": "user", "DASHBOARD_PASSWORD": "pass"}):
        assert check_auth("user", "pass") is True
        assert check_auth("admin", "changeme") is False


def test_authenticate_returns_401_response():
    """authenticate returns a 401 with WWW-Authenticate header."""
    resp = authenticate()
    assert resp.status_code == 401
    assert "WWW-Authenticate" in resp.headers


def test_requires_auth_decorator_blocks_unauth():
    """requires_auth returns 401 when no auth header provided."""

    @requires_auth
    def protected():
        return "secret"

    with dash_app.test_request_context("/"):
        resp = protected()
        assert resp.status_code == 401


def test_requires_auth_decorator_allows_auth():
    """requires_auth passes through when correct auth provided."""
    with patch.dict(os.environ, {"DASHBOARD_USERNAME": TEST_USER, "DASHBOARD_PASSWORD": TEST_PASS}):

        @requires_auth
        def protected():
            return "secret"

        credentials = base64.b64encode(b"admin:changeme").decode("utf-8")
        with dash_app.test_request_context(
            "/", headers={"Authorization": f"Basic {credentials}"}
        ):
            assert protected() == "secret"


# ── App Route Tests ──


@pytest.fixture(autouse=True)
def _set_auth_env():
    """Set auth env vars for all dashboard route tests."""
    with patch.dict(
        os.environ,
        {
            "DASHBOARD_USERNAME": TEST_USER,
            "DASHBOARD_PASSWORD": TEST_PASS,
            "DASHBOARD_SECRET_KEY": "test-secret",
        },
    ):
        yield


@pytest.fixture
def client():
    """Flask test client."""
    dash_app.testing = True
    dash_app.config.update(SECRET_KEY="test-secret", WTF_CSRF_ENABLED=True)
    return dash_app.test_client()


def _auth_header():
    credentials = base64.b64encode(b"admin:changeme").decode("utf-8")
    return {"Authorization": f"Basic {credentials}"}


def _csrf_header(client):
    response = client.get("/", headers=_auth_header())
    token_match = re.search(
        r'<meta name="csrf-token" content="([^"]+)">', response.text
    )
    assert token_match is not None
    return {"X-CSRFToken": token_match.group(1)}


def test_index_requires_auth(client):
    """Index route returns 401 without auth."""
    resp = client.get("/")
    assert resp.status_code == 401


def test_index_with_auth(client):
    """Index route returns 200 with valid auth."""
    credentials = base64.b64encode(b"admin:changeme").decode("utf-8")
    resp = client.get("/", headers={"Authorization": f"Basic {credentials}"})
    assert resp.status_code == 200


def test_jobs_page_requires_auth(client):
    """Jobs page returns 401 without auth."""
    resp = client.get("/jobs")
    assert resp.status_code == 401


def test_jobs_page_with_auth(client):
    """Jobs page returns 200 with valid auth."""
    credentials = base64.b64encode(b"admin:changeme").decode("utf-8")
    resp = client.get("/jobs", headers={"Authorization": f"Basic {credentials}"})
    assert resp.status_code == 200


def test_api_jobs_requires_auth(client):
    """API jobs returns 401 without auth."""
    resp = client.get("/api/jobs")
    assert resp.status_code == 401


def test_api_jobs_with_auth_returns_json(client):
    """API jobs returns JSON list with valid auth."""
    credentials = base64.b64encode(b"admin:changeme").decode("utf-8")
    resp = client.get("/api/jobs", headers={"Authorization": f"Basic {credentials}"})
    assert resp.status_code == 200
    assert resp.is_json
    assert isinstance(resp.json, list)


def test_api_job_detail_not_found(client):
    """API job detail returns 404 for non-existent job."""
    credentials = base64.b64encode(b"admin:changeme").decode("utf-8")
    resp = client.get("/api/jobs/99999", headers={"Authorization": f"Basic {credentials}"})
    assert resp.status_code == 404
    assert resp.json["error"] == "Job not found"


def test_api_create_job_missing_topic(client):
    """API create job returns 400 when topic is missing."""
    headers = _auth_header() | _csrf_header(client)
    resp = client.post(
        "/api/jobs",
        json={},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "topic" in resp.json["error"]


def test_api_create_job_requires_csrf_token(client):
    """State-changing API requests require a CSRF token."""
    resp = client.post(
        "/api/jobs",
        json={"topic": "news"},
        headers=_auth_header(),
    )
    assert resp.status_code == 400


def test_api_create_job_fails_when_csrf_secret_missing(client):
    """State-changing API requests fail closed when CSRF config is missing."""
    dash_app.config["SECRET_KEY"] = None
    resp = client.post(
        "/api/jobs",
        json={"topic": "news"},
        headers=_auth_header() | {"X-CSRFToken": "token"},
    )
    assert resp.status_code == 403


def test_dashboard_get_routes_declare_http_methods():
    """GET-only routes declare methods explicitly for static analysis."""
    source = (PROJECT_ROOT / "clipper_agency/dashboard/app.py").read_text(encoding="utf-8")
    assert '@app.route("/", methods=["GET"])' in source
    assert '@app.route("/jobs", methods=["GET"])' in source
    assert '@app.route("/api/jobs", methods=["GET"])' in source
    assert '@app.route("/api/jobs/<int:job_id>", methods=["GET"])' in source


def test_dashboard_index_uses_async_await():
    """Index template uses async/await instead of promise chaining."""
    source = (
        PROJECT_ROOT / "clipper_agency/dashboard/templates/index.html"
    ).read_text(encoding="utf-8")
    assert ".then(" not in source
    assert "await fetch" in source
