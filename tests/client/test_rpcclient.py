"""Tests for the Python RPCClient against a real FastAPI test server."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from leap.main import create_app
from leap.core import storage
from leap.client.rpc import (
    RPCClient,
    RPCError,
    RPCServerError,
    RPCNetworkError,
    RPCNotRegisteredError,
)


# ── Fixtures ──


@pytest.fixture
def server(tmp_credentials: Path):
    app = create_app(root=tmp_credentials)
    with TestClient(app) as c:
        yield c
    storage.close_all_engines()


@pytest.fixture
def seeded_server(server: TestClient):
    """Server with registered students and some log entries."""
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


def _make_client(
    test_client: TestClient,
    student_id: str = "s001",
    experiment: str = "default",
    trial_name: str | None = None,
) -> RPCClient:
    """Create an RPCClient that routes HTTP through the FastAPI TestClient."""

    real_get = test_client.get
    real_post = test_client.post

    class FakeResponse:
        """Adapt TestClient responses to look like requests.Response."""

        def __init__(self, tc_resp):
            self._r = tc_resp
            self.status_code = tc_resp.status_code
            self.ok = 200 <= tc_resp.status_code < 400
            self.text = tc_resp.text
            self.reason = ""

        def json(self):
            return self._r.json()

        def raise_for_status(self):
            if not self.ok:
                raise Exception(f"HTTP {self.status_code}")

    def fake_get(url, **kwargs):
        path = url.replace("http://testserver", "")
        params = kwargs.get("params")
        return FakeResponse(real_get(path, params=params))

    def fake_post(url, **kwargs):
        path = url.replace("http://testserver", "")
        json_data = kwargs.get("json")
        return FakeResponse(real_post(path, json=json_data))

    with patch("leap.client.rpc.requests") as mock_requests:
        mock_requests.get = fake_get
        mock_requests.post = fake_post
        mock_requests.exceptions = __import__("requests").exceptions
        client = RPCClient(
            server_url="http://testserver",
            student_id=student_id,
            experiment=experiment,
            trial_name=trial_name,
        )

    client._patch_requests = mock_requests
    client._fake_get = fake_get
    client._fake_post = fake_post

    # Patch requests globally for subsequent calls on this client
    _orig_call = client.call

    def patched_call(func_name, *args, **kwargs):
        with patch("leap.client.rpc.requests") as mr:
            mr.get = fake_get
            mr.post = fake_post
            mr.exceptions = __import__("requests").exceptions
            return _orig_call(func_name, *args, **kwargs)

    client.call = patched_call

    _orig_is_reg = client.is_registered

    def patched_is_registered():
        with patch("leap.client.rpc.requests") as mr:
            mr.get = fake_get
            mr.post = fake_post
            mr.exceptions = __import__("requests").exceptions
            return _orig_is_reg()

    client.is_registered = patched_is_registered

    _orig_fetch_logs = client.fetch_logs

    def patched_fetch_logs(**kwargs):
        with patch("leap.client.rpc.requests") as mr:
            mr.get = fake_get
            mr.post = fake_post
            mr.exceptions = __import__("requests").exceptions
            return _orig_fetch_logs(**kwargs)

    client.fetch_logs = patched_fetch_logs

    return client


# ── Init & Discovery ──


class TestInit:
    def test_requires_experiment(self, server):
        with pytest.raises(ValueError, match="experiment must be provided"):
            with patch("leap.client.rpc.requests") as mr:
                RPCClient("http://testserver", student_id="s001")

    def test_discovers_functions(self, server):
        client = _make_client(server)
        assert client._functions is not None
        assert "square" in client._functions
        assert "add" in client._functions

    def test_experiment_stored(self, server):
        client = _make_client(server, experiment="default")
        assert client.experiment == "default"

    def test_trial_name_stored(self, server):
        client = _make_client(server, trial_name="trial-1")
        assert client.trial_name == "trial-1"

    def test_strips_trailing_slash(self, server):
        with patch("leap.client.rpc.requests") as mr:
            mr.get = lambda url, **kw: MagicMock(
                status_code=200, ok=True,
                json=lambda: {"square": {"signature": "(x)", "doc": ""}},
                raise_for_status=lambda: None,
            )
            mr.exceptions = __import__("requests").exceptions
            client = RPCClient("http://localhost:9000/", student_id="s001", experiment="default")
        assert client.server_url == "http://localhost:9000"


# ── Function calls ──


class TestCall:
    def test_call_square(self, seeded_server):
        client = _make_client(seeded_server, student_id="s001")
        result = client.call("square", 7)
        assert result == 49

    def test_call_add(self, seeded_server):
        client = _make_client(seeded_server, student_id="s001")
        result = client.call("add", 3, 4)
        assert result == 7

    def test_call_cubic(self, seeded_server):
        client = _make_client(seeded_server, student_id="s001")
        result = client.call("cubic", 3)
        assert result == 27

    def test_unregistered_student_raises(self, server):
        client = _make_client(server, student_id="unregistered")
        with pytest.raises(RPCNotRegisteredError, match="not registered"):
            client.call("square", 5)

    def test_unknown_function_raises(self, seeded_server):
        client = _make_client(seeded_server, student_id="s001")
        with pytest.raises(RPCServerError):
            client.call("nonexistent_func", 1)


# ── Dynamic dispatch ──


class TestDynamicDispatch:
    def test_dynamic_method(self, seeded_server):
        client = _make_client(seeded_server, student_id="s001")
        assert client.square(5) == 25

    def test_dynamic_method_cached(self, seeded_server):
        client = _make_client(seeded_server, student_id="s001")
        _ = client.square(2)
        assert hasattr(client, "square")
        assert callable(client.square)

    def test_unknown_attr_raises(self, server):
        client = _make_client(server)
        with pytest.raises(AttributeError, match="No function 'nonexistent'"):
            client.nonexistent()

    def test_attr_error_suggests_help(self, server):
        client = _make_client(server)
        with pytest.raises(AttributeError, match="client.help()"):
            client.does_not_exist


# ── list_functions ──


class TestListFunctions:
    def test_returns_dict(self, server):
        client = _make_client(server)
        funcs = client.list_functions()
        assert isinstance(funcs, dict)

    def test_contains_expected_functions(self, server):
        client = _make_client(server)
        funcs = client.list_functions()
        assert "square" in funcs
        assert "add" in funcs
        assert "cubic" in funcs

    def test_function_info_shape(self, server):
        client = _make_client(server)
        funcs = client.list_functions()
        info = funcs["square"]
        assert "signature" in info
        assert "doc" in info


# ── help ──


class TestHelp:
    def test_help_prints_functions(self, server, capsys):
        client = _make_client(server)
        client.help()
        output = capsys.readouterr().out
        assert "square" in output
        assert "add" in output
        assert "Available functions" in output

    def test_help_shows_signatures(self, server, capsys):
        client = _make_client(server)
        client.help()
        output = capsys.readouterr().out
        assert "(x)" in output or "(a, b)" in output

    def test_help_shows_badges(self, server, capsys):
        client = _make_client(server)
        client.help()
        output = capsys.readouterr().out
        assert "@nolog" in output
        assert "@noregcheck" in output

    def test_help_shows_docstrings(self, server, capsys):
        client = _make_client(server)
        client.help()
        output = capsys.readouterr().out
        assert "x squared" in output


# ── is_registered ──


class TestIsRegistered:
    def test_registered_student(self, seeded_server):
        client = _make_client(seeded_server, student_id="s001")
        assert client.is_registered() is True

    def test_unregistered_student(self, seeded_server):
        client = _make_client(seeded_server, student_id="nobody")
        assert client.is_registered() is False

    def test_registered_via_endpoint(self, seeded_server):
        """Verify it uses the /is-registered endpoint (no side effects)."""
        client = _make_client(seeded_server, student_id="s002")
        assert client.is_registered() is True


# ── fetch_logs ──


class TestFetchLogs:
    def test_fetch_all_logs(self, seeded_server):
        client = _make_client(seeded_server, student_id="s001")
        logs = client.fetch_logs()
        assert isinstance(logs, list)
        assert len(logs) == 8

    def test_fetch_logs_with_limit(self, seeded_server):
        client = _make_client(seeded_server, student_id="s001")
        logs = client.fetch_logs(n=3)
        assert len(logs) == 3

    def test_fetch_logs_filter_student(self, seeded_server):
        client = _make_client(seeded_server, student_id="s001")
        logs = client.fetch_logs(student_id="s001")
        assert len(logs) == 5
        assert all(l["student_id"] == "s001" for l in logs)

    def test_fetch_logs_filter_func(self, seeded_server):
        client = _make_client(seeded_server, student_id="s001")
        logs = client.fetch_logs(func_name="add")
        assert len(logs) == 3
        assert all(l["func_name"] == "add" for l in logs)

    def test_fetch_logs_filter_trial(self, seeded_server):
        client = _make_client(seeded_server, student_id="s001")
        logs = client.fetch_logs(trial="run-1")
        assert len(logs) == 5

    def test_fetch_logs_order_earliest(self, seeded_server):
        client = _make_client(seeded_server, student_id="s001")
        logs = client.fetch_logs(order="earliest")
        ids = [l["id"] for l in logs]
        assert ids == sorted(ids)

    def test_fetch_logs_order_latest(self, seeded_server):
        client = _make_client(seeded_server, student_id="s001")
        logs = client.fetch_logs(order="latest")
        ids = [l["id"] for l in logs]
        assert ids == sorted(ids, reverse=True)

    def test_fetch_logs_empty(self, server):
        client = _make_client(server)
        logs = client.fetch_logs()
        assert logs == []

    def test_log_entry_shape(self, seeded_server):
        client = _make_client(seeded_server, student_id="s001")
        logs = client.fetch_logs(n=1)
        entry = logs[0]
        assert "id" in entry
        assert "ts" in entry
        assert "student_id" in entry
        assert "func_name" in entry
        assert "args" in entry
        assert "result" in entry


# ── Exception hierarchy ──


class TestExceptions:
    def test_rpc_error_is_base(self):
        assert issubclass(RPCServerError, RPCError)
        assert issubclass(RPCNetworkError, RPCError)

    def test_not_registered_is_server_error(self):
        assert issubclass(RPCNotRegisteredError, RPCServerError)

    def test_catch_all_with_rpc_error(self, server):
        client = _make_client(server, student_id="unregistered")
        with pytest.raises(RPCError):
            client.call("square", 5)


# ── Noregcheck & Nolog ──


class TestDecorators:
    def test_noregcheck_skips_registration(self, server):
        """Unregistered student can call @noregcheck functions."""
        client = _make_client(server, student_id="anon-user")
        result = client.call("echo", 42)
        assert result == 42

    def test_noregcheck_ping(self, server):
        client = _make_client(server, student_id="anon-user")
        result = client.call("ping")
        assert result == "pong"

    def test_nolog_function_works(self, seeded_server):
        client = _make_client(seeded_server, student_id="s001")
        result = client.call("fast_step", 5)
        assert result == 10

    def test_nolog_not_in_logs(self, seeded_server):
        """@nolog function calls should not appear in logs."""
        client = _make_client(seeded_server, student_id="s001")
        client.call("fast_step", 5)
        logs = client.fetch_logs(func_name="fast_step")
        assert len(logs) == 0


# ── Trial name ──


class TestTrialName:
    def test_trial_recorded(self, seeded_server):
        client = _make_client(seeded_server, student_id="s001", trial_name="my-trial")
        client.call("square", 10)
        logs = client.fetch_logs(trial="my-trial")
        assert len(logs) >= 1
        assert logs[0]["trial"] == "my-trial"

    def test_no_trial(self, seeded_server):
        client = _make_client(seeded_server, student_id="s001")
        client.call("square", 99)
        logs = client.fetch_logs(n=1)
        assert logs[0]["trial"] is None or logs[0]["trial"] == ""
