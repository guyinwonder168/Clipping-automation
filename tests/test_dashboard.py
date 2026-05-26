"""Tests for the web dashboard with basic auth and job listing."""

import os
from unittest.mock import patch

import pytest

from clipper_agency.dashboard.auth import authenticate, check_auth, requires_auth
from clipper_agency.dashboard.app import app as dash_app


# ── Auth Tests ──


def test_check_auth_valid():
    """check_auth returns True when credentials match env vars."""
    assert check_auth("admin", "changeme") is True


def test_check_auth_invalid_username():
    """check_auth returns False for wrong username."""
    assert check_auth("hacker", "changeme") is False


def test_check_auth_invalid_password():
    """check_auth returns False for wrong password."""
    assert check_auth("admin", "wrongpass") is False


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
    import base64

    @requires_auth
    def protected():
        return "secret"

    credentials = base64.b64encode(b"admin:changeme").decode("utf-8")
    with dash_app.test_request_context(
        "/", headers={"Authorization": f"Basic {credentials}"}
    ):
        assert protected() == "secret"


# ── App Route Tests ──


@pytest.fixture
def client():
    """Flask test client."""
    dash_app.testing = True
    return dash_app.test_client()


def test_index_requires_auth(client):
    """Index route returns 401 without auth."""
    resp = client.get("/")
    assert resp.status_code == 401


def test_index_with_auth(client):
    """Index route returns 200 with valid auth."""
    import base64
    credentials = base64.b64encode(b"admin:changeme").decode("utf-8")
    resp = client.get("/", headers={"Authorization": f"Basic {credentials}"})
    assert resp.status_code == 200


def test_jobs_page_requires_auth(client):
    """Jobs page returns 401 without auth."""
    resp = client.get("/jobs")
    assert resp.status_code == 401


def test_jobs_page_with_auth(client):
    """Jobs page returns 200 with valid auth."""
    import base64
    credentials = base64.b64encode(b"admin:changeme").decode("utf-8")
    resp = client.get("/jobs", headers={"Authorization": f"Basic {credentials}"})
    assert resp.status_code == 200


def test_api_jobs_requires_auth(client):
    """API jobs returns 401 without auth."""
    resp = client.get("/api/jobs")
    assert resp.status_code == 401


def test_api_jobs_with_auth_returns_json(client):
    """API jobs returns JSON list with valid auth."""
    import base64
    credentials = base64.b64encode(b"admin:changeme").decode("utf-8")
    resp = client.get("/api/jobs", headers={"Authorization": f"Basic {credentials}"})
    assert resp.status_code == 200
    assert resp.is_json
    assert isinstance(resp.json, list)


def test_api_job_detail_not_found(client):
    """API job detail returns 404 for non-existent job."""
    import base64
    credentials = base64.b64encode(b"admin:changeme").decode("utf-8")
    resp = client.get("/api/jobs/99999", headers={"Authorization": f"Basic {credentials}"})
    assert resp.status_code == 404
    assert resp.json["error"] == "Job not found"


def test_api_create_job_missing_topic(client):
    """API create job returns 400 when topic is missing."""
    import base64
    credentials = base64.b64encode(b"admin:changeme").decode("utf-8")
    resp = client.post(
        "/api/jobs",
        json={},
        headers={"Authorization": f"Basic {credentials}"},
    )
    assert resp.status_code == 400
    assert "topic" in resp.json["error"]
