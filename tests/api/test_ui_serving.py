"""Phase 2 API tests: static file serving, landing, login pages, experiment UI."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from leap.main import create_app
from leap.core import storage


@pytest.fixture
def client(tmp_credentials: Path):
    app = create_app(root=tmp_credentials)
    with TestClient(app) as c:
        yield c
    storage.close_all_engines()


@pytest.fixture
def admin_client(client: TestClient):
    resp = client.post("/login", json={"password": "testpass"})
    assert resp.status_code == 200
    return client


class TestLandingPage:
    def test_landing_returns_html(self, client):
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_landing_contains_leap2(self, client):
        resp = client.get("/")
        assert "LEAP2" in resp.text

    def test_landing_has_experiments_div(self, client):
        resp = client.get("/")
        assert "experiments" in resp.text


class TestLandingRedirect:
    def test_redirect_when_default_experiment_set(self, tmp_credentials):
        with patch("leap.main.DEFAULT_EXPERIMENT", "default"):
            app = create_app(root=tmp_credentials)
            with TestClient(app, raise_server_exceptions=False) as c:
                resp = c.get("/", follow_redirects=False)
                assert resp.status_code == 307
                assert "/exp/default/ui/dashboard.html" in resp.headers["location"]
            storage.close_all_engines()

    def test_no_redirect_when_default_experiment_not_found(self, tmp_credentials):
        with patch("leap.main.DEFAULT_EXPERIMENT", "nonexistent"):
            app = create_app(root=tmp_credentials)
            with TestClient(app) as c:
                resp = c.get("/", follow_redirects=False)
                assert resp.status_code == 200
            storage.close_all_engines()

    def test_no_redirect_when_default_experiment_empty(self, client):
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 200


class TestLoginPage:
    def test_login_page_returns_html(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_login_page_has_form(self, client):
        resp = client.get("/login")
        assert "login-form" in resp.text

    def test_login_page_has_password_field(self, client):
        resp = client.get("/login")
        assert "password" in resp.text


class TestSharedAssets:
    def test_theme_css(self, client):
        resp = client.get("/static/theme.css")
        assert resp.status_code == 200
        assert "text/css" in resp.headers["content-type"]

    def test_theme_css_content(self, client):
        resp = client.get("/static/theme.css")
        assert "--color-primary" in resp.text

    def test_logclient_js(self, client):
        resp = client.get("/static/logclient.js")
        assert resp.status_code == 200
        assert "javascript" in resp.headers["content-type"]

    def test_adminclient_js(self, client):
        resp = client.get("/static/adminclient.js")
        assert resp.status_code == 200
        assert "javascript" in resp.headers["content-type"]

    def test_nonexistent_shared_file(self, client):
        resp = client.get("/static/nonexistent.js")
        assert resp.status_code == 404


class TestExperimentUI:
    def test_dashboard_html(self, client):
        resp = client.get("/exp/default/ui/dashboard.html")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_dashboard_content(self, client):
        resp = client.get("/exp/default/ui/dashboard.html")
        assert "Default Lab" in resp.text

    def test_nonexistent_experiment_ui(self, client):
        resp = client.get("/exp/nonexistent/ui/dashboard.html")
        assert resp.status_code in (404, 405)

    def test_nonexistent_file_in_experiment_ui(self, client):
        resp = client.get("/exp/default/ui/nonexistent.html")
        assert resp.status_code == 404


class TestStaticMountCoexistence:
    """Ensure static mounts don't interfere with API routes."""

    def test_api_health_still_works(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_api_experiments_still_works(self, client):
        resp = client.get("/api/experiments")
        assert resp.status_code == 200
        assert "experiments" in resp.json()

    def test_rpc_still_works(self, admin_client):
        admin_client.post(
            "/exp/default/admin/add-student",
            json={"student_id": "s001", "name": "Alice"},
        )
        resp = admin_client.post(
            "/exp/default/call",
            json={"student_id": "s001", "func_name": "square", "args": [5]},
        )
        assert resp.status_code == 200
        assert resp.json()["result"] == 25

    def test_login_post_still_works(self, client):
        resp = client.post("/login", json={"password": "testpass"})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_admin_routes_still_work(self, admin_client):
        resp = admin_client.get("/exp/default/admin/students")
        assert resp.status_code == 200
