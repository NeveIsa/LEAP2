"""Tests for the Python LogClient against a real FastAPI test server."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from leap.main import create_app
from leap.core import storage
from leap.client.logclient import LogClient


@pytest.fixture
def server(tmp_credentials: Path):
    """Start a test server and return (base_url_override, TestClient)."""
    app = create_app(root=tmp_credentials)
    with TestClient(app) as c:
        yield c
    storage.close_all_engines()


@pytest.fixture
def seeded_server(server: TestClient):
    """Server with a student and some log entries."""
    server.post("/login", json={"password": "testpass"})
    server.post("/exp/default/admin/add-student", json={"student_id": "s001", "name": "Alice"})
    server.post("/exp/default/admin/add-student", json={"student_id": "s002", "name": "Bob"})

    for i in range(5):
        server.post("/exp/default/call", json={
            "student_id": "s001", "func_name": "square", "args": [i], "trial": "run-1",
        })
    for i in range(3):
        server.post("/exp/default/call", json={
            "student_id": "s002", "func_name": "add", "args": [i, i + 1], "trial": "run-2",
        })

    return server


def _make_client(test_client: TestClient, experiment: str = "default") -> LogClient:
    """Create a LogClient that routes through the TestClient via mocked requests."""
    client = LogClient.__new__(LogClient)
    client.server_url = "http://testserver"
    client.experiment = experiment
    client._api_base = f"http://testserver/exp/{experiment}"

    original_get = client._get

    def patched_get(url, params=None):
        path = url.replace("http://testserver", "")
        resp = test_client.get(path, params=params)
        if resp.status_code != 200:
            detail = f"HTTP {resp.status_code}"
            try:
                body = resp.json()
                if "detail" in body:
                    detail = body["detail"]
            except Exception:
                pass
            raise RuntimeError(f"LogClient: {detail}")
        return resp.json()

    client._get = patched_get
    return client


class TestLogClientInit:
    def test_requires_experiment(self):
        with pytest.raises(ValueError, match="experiment is required"):
            LogClient("http://localhost:9000", experiment="")

    def test_strips_trailing_slash(self):
        c = LogClient("http://localhost:9000/", experiment="default")
        assert c.server_url == "http://localhost:9000"
        assert c._api_base == "http://localhost:9000/exp/default"

    def test_api_base_construction(self):
        c = LogClient("http://example.com", experiment="my-lab")
        assert c._api_base == "http://example.com/exp/my-lab"


class TestGetLogs:
    def test_get_logs_empty(self, server):
        client = _make_client(server)
        logs = client.get_logs()
        assert isinstance(logs, list)
        assert len(logs) == 0

    def test_get_logs_returns_entries(self, seeded_server):
        client = _make_client(seeded_server)
        logs = client.get_logs()
        assert len(logs) == 8

    def test_get_logs_filter_student(self, seeded_server):
        client = _make_client(seeded_server)
        logs = client.get_logs(student_id="s001")
        assert len(logs) == 5
        assert all(l["student_id"] == "s001" for l in logs)

    def test_get_logs_filter_func_name(self, seeded_server):
        client = _make_client(seeded_server)
        logs = client.get_logs(func_name="add")
        assert len(logs) == 3
        assert all(l["func_name"] == "add" for l in logs)

    def test_get_logs_filter_trial(self, seeded_server):
        client = _make_client(seeded_server)
        logs = client.get_logs(trial="run-1")
        assert len(logs) == 5

    def test_get_logs_limit(self, seeded_server):
        client = _make_client(seeded_server)
        logs = client.get_logs(n=3)
        assert len(logs) == 3

    def test_get_logs_order_earliest(self, seeded_server):
        client = _make_client(seeded_server)
        logs = client.get_logs(order="earliest")
        assert len(logs) == 8
        ids = [l["id"] for l in logs]
        assert ids == sorted(ids)

    def test_get_logs_order_latest(self, seeded_server):
        client = _make_client(seeded_server)
        logs = client.get_logs(order="latest")
        ids = [l["id"] for l in logs]
        assert ids == sorted(ids, reverse=True)

    def test_get_logs_pagination(self, seeded_server):
        client = _make_client(seeded_server)
        page1 = client.get_logs(n=4, order="earliest")
        assert len(page1) == 4
        page2 = client.get_logs(n=4, order="earliest", after_id=page1[-1]["id"])
        assert len(page2) == 4
        all_ids = [l["id"] for l in page1] + [l["id"] for l in page2]
        assert len(set(all_ids)) == 8

    def test_get_logs_combined_filters(self, seeded_server):
        client = _make_client(seeded_server)
        logs = client.get_logs(student_id="s001", func_name="square", trial="run-1")
        assert len(logs) == 5

    def test_log_entry_shape(self, seeded_server):
        client = _make_client(seeded_server)
        logs = client.get_logs(n=1)
        entry = logs[0]
        assert "id" in entry
        assert "ts" in entry
        assert "student_id" in entry
        assert "func_name" in entry
        assert "args" in entry
        assert "result" in entry


class TestGetLogOptions:
    def test_get_log_options(self, seeded_server):
        client = _make_client(seeded_server)
        opts = client.get_log_options()
        assert "students" in opts
        assert "trials" in opts

    def test_students_list(self, seeded_server):
        client = _make_client(seeded_server)
        opts = client.get_log_options()
        assert "s001" in opts["students"]
        assert "s002" in opts["students"]

    def test_trials_list(self, seeded_server):
        client = _make_client(seeded_server)
        opts = client.get_log_options()
        assert "run-1" in opts["trials"]
        assert "run-2" in opts["trials"]

    def test_empty_options(self, server):
        client = _make_client(server)
        opts = client.get_log_options()
        assert opts["students"] == []


class TestGetAllLogs:
    def test_get_all_logs(self, seeded_server):
        client = _make_client(seeded_server)
        all_logs = client.get_all_logs(page_size=3)
        assert len(all_logs) == 8

    def test_get_all_logs_with_filter(self, seeded_server):
        client = _make_client(seeded_server)
        all_logs = client.get_all_logs(student_id="s001", page_size=2)
        assert len(all_logs) == 5
        assert all(l["student_id"] == "s001" for l in all_logs)

    def test_get_all_logs_empty(self, server):
        client = _make_client(server)
        all_logs = client.get_all_logs()
        assert all_logs == []


class TestErrorHandling:
    def test_unknown_experiment(self, server):
        client = _make_client(server, experiment="nonexistent")
        with pytest.raises(RuntimeError, match="(?i)not found"):
            client.get_logs()

    def test_unknown_experiment_options(self, server):
        client = _make_client(server, experiment="nonexistent")
        with pytest.raises(RuntimeError, match="(?i)not found"):
            client.get_log_options()
