"""Python RPC client for students to call remote experiment functions."""

from __future__ import annotations

import json
import os
from typing import Any

import requests


# ── Exception hierarchy ──

class RPCError(Exception):
    """Base exception for RPC client errors."""


class RPCServerError(RPCError):
    """Raised when the server returns a non-2xx response."""


class RPCNetworkError(RPCError):
    """Raised when there is a network/transport error reaching the server."""


class RPCProtocolError(RPCError):
    """Raised when the server responds successfully but the payload is invalid."""


class RPCNotRegisteredError(RPCServerError):
    """Raised when the student_id is not registered (HTTP 403)."""


# ── Client ──

class RPCClient:
    """Client for calling LEAP2 experiment functions via HTTP RPC.

    Usage::

        from leap.client import RPCClient

        client = RPCClient("http://localhost:9000", student_id="s001", experiment="default")

        # Check registration
        if not client.is_registered():
            print("Not registered!")

        # Call a function
        result = client.square(7)

        # List what's available
        client.help()

        # Fetch your logs
        logs = client.fetch_logs(n=20)
    """

    def __init__(
        self,
        server_url: str,
        student_id: str,
        experiment: str | None = None,
        trial_name: str | None = None,
    ):
        self.server_url = server_url.rstrip("/")
        self.student_id = student_id
        self.trial_name = trial_name

        self.experiment = experiment or os.environ.get("DEFAULT_EXPERIMENT")
        if not self.experiment:
            raise ValueError(
                "experiment must be provided or DEFAULT_EXPERIMENT env must be set"
            )

        self._base = f"{self.server_url}/exp/{self.experiment}"
        self._functions: dict[str, dict] | None = None
        self._discover()

    # ── Discovery ──

    def _discover(self):
        """Fetch the list of available functions from the server."""
        try:
            resp = requests.get(f"{self._base}/functions", timeout=10)
            resp.raise_for_status()
            self._functions = resp.json()
        except requests.exceptions.RequestException as e:
            raise RPCNetworkError(f"Error discovering functions: {e}") from e

    # ── RPC call ──

    def call(self, func_name: str, *args, **kwargs) -> Any:
        """Call a remote function by name."""
        payload: dict[str, Any] = {
            "student_id": self.student_id,
            "func_name": func_name,
            "args": list(args),
            "trial": self.trial_name,
        }
        if kwargs:
            payload["kwargs"] = kwargs

        try:
            resp = requests.post(f"{self._base}/call", json=payload, timeout=15)
        except requests.exceptions.RequestException as e:
            raise RPCNetworkError(f"Network error calling '{func_name}': {e}") from e

        if not resp.ok:
            status = resp.status_code
            detail = None
            try:
                detail = resp.json().get("detail")
            except Exception:
                detail = resp.text or resp.reason

            if status == 403:
                raise RPCNotRegisteredError(
                    f"Student '{self.student_id}' is not registered. "
                    f"Register via the Admin UI ({self.server_url}/static/students.html"
                    f"?exp={self.experiment}) or the admin API."
                )
            raise RPCServerError(
                f"Server error calling '{func_name}': {detail or 'unknown'} (HTTP {status})"
            )

        try:
            data = resp.json()
        except json.JSONDecodeError as e:
            raise RPCProtocolError(f"Invalid JSON response for '{func_name}': {e}") from e

        if "result" not in data:
            raise RPCProtocolError(f"Missing 'result' in server response for '{func_name}'.")

        return data["result"]

    # ── Dynamic method dispatch ──

    def __getattr__(self, name: str):
        if self._functions is not None and name in self._functions:
            info = self._functions[name]
            sig = info.get("signature", "(...)")
            doc = info.get("doc", "")

            def method(*args, **kwargs):
                return self.call(name, *args, **kwargs)

            method.__name__ = name
            method.__doc__ = f"{name}{sig}\n\n{doc}" if doc else f"{name}{sig}"
            setattr(self, name, method)
            return method
        raise AttributeError(
            f"No function '{name}' in experiment '{self.experiment}'. "
            f"Use client.help() to see available functions."
        )

    # ── Convenience methods ──

    def list_functions(self) -> dict[str, dict]:
        """Return discovered functions with signatures and docs."""
        if self._functions is None:
            self._discover()
        return self._functions

    def help(self):
        """Print available remote functions with their signatures."""
        if not self._functions:
            print("No functions discovered from the server.")
            return
        print(f"Available functions for experiment '{self.experiment}':\n")
        for name, info in sorted(self._functions.items()):
            sig = info.get("signature", "()")
            doc = info.get("doc", "")
            badges = []
            if info.get("nolog"):
                badges.append("@nolog")
            if info.get("noregcheck"):
                badges.append("@noregcheck")
            badge_str = f"  [{', '.join(badges)}]" if badges else ""
            print(f"  {name}{sig}{badge_str}")
            if doc:
                for line in doc.strip().splitlines():
                    print(f"      {line}")
            print()

    def is_registered(self) -> bool:
        """Check whether this client's student_id is registered.

        Uses the ``/exp/{experiment}/is-registered`` endpoint (no side effects).
        Falls back to probing a function call if the endpoint is unavailable.
        """
        try:
            resp = requests.get(
                f"{self._base}/is-registered",
                params={"student_id": self.student_id},
                timeout=5,
            )
            if resp.ok:
                data = resp.json()
                if isinstance(data, dict) and "registered" in data:
                    return bool(data["registered"])
        except requests.exceptions.RequestException:
            pass

        # Fallback: probe via a real call (may produce one log entry)
        candidates = self._build_probe_candidates()
        for fname, args in candidates:
            try:
                self.call(fname, *args)
                return True
            except RPCNotRegisteredError:
                return False
            except RPCNetworkError:
                raise
            except (RPCServerError, RPCProtocolError):
                return True

        raise RPCError(
            "Cannot determine registration: no callable functions available to probe."
        )

    def _build_probe_candidates(self) -> list[tuple[str, tuple]]:
        """Build a list of (func_name, safe_args) pairs for registration probing."""
        if not self._functions:
            return []

        candidates: list[tuple[str, tuple]] = []
        seen: set[str] = set()

        well_known = {"square": (0,), "cubic": (0,), "quadratic": (0, 0, 0, 0), "rosenbrock": (0, 0)}
        for name, args in well_known.items():
            if name in self._functions:
                candidates.append((name, args))
                seen.add(name)

        for name, info in self._functions.items():
            if name in seen:
                continue
            sig = str(info.get("signature", "()"))
            inner = sig.strip("()")
            required = 0
            if inner.strip():
                for part in (p.strip() for p in inner.split(",")):
                    if not part or part.startswith("*") or "=" in part:
                        continue
                    required += 1
            candidates.append((name, tuple(0 for _ in range(min(required, 4)))))

        return candidates

    def fetch_logs(
        self,
        n: int = 100,
        student_id: str | None = None,
        func_name: str | None = None,
        trial: str | None = None,
        order: str = "latest",
    ) -> list[dict]:
        """Fetch call logs for this experiment.

        Args:
            n: Maximum number of logs (1–10000).
            student_id: Filter by student (defaults to this client's ID if None).
            func_name: Filter by function name.
            trial: Filter by trial name.
            order: ``'latest'`` or ``'earliest'``.

        Returns:
            A list of log dicts with keys: id, ts, student_id, func_name,
            trial, args, result, error.
        """
        params: dict[str, Any] = {"n": n, "order": order}
        if student_id:
            params["student_id"] = student_id
        if func_name:
            params["func_name"] = func_name
        if trial:
            params["trial_name"] = trial

        try:
            resp = requests.get(f"{self._base}/logs", params=params, timeout=10)
        except requests.exceptions.RequestException as e:
            raise RPCNetworkError(f"Network error fetching logs: {e}") from e

        if not resp.ok:
            if resp.status_code == 403:
                raise RPCNotRegisteredError(
                    f"Student '{student_id or self.student_id}' is not registered."
                )
            raise RPCServerError(f"Server error fetching logs: HTTP {resp.status_code}")

        try:
            data = resp.json()
        except json.JSONDecodeError as e:
            raise RPCProtocolError(f"Invalid JSON response from /logs: {e}") from e

        return data.get("logs", [])


Client = RPCClient
