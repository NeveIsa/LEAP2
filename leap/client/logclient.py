"""Python Log Client — read-only access to experiment logs via HTTP.

Usage:
    from leap.client import LogClient

    client = LogClient("http://localhost:9000", experiment="default")
    logs = client.get_logs(student_id="s001", n=50)
    options = client.get_log_options()
    all_logs = client.get_all_logs(func_name="square")
"""

from __future__ import annotations

from typing import Any

import requests


class LogClient:
    """Read-only client for querying LEAP2 experiment logs.

    Args:
        server_url: Server origin (e.g. "http://localhost:9000").
        experiment: Experiment name.
    """

    def __init__(self, server_url: str, experiment: str):
        if not experiment:
            raise ValueError("experiment is required")
        self.server_url = server_url.rstrip("/")
        self.experiment = experiment
        self._api_base = f"{self.server_url}/exp/{self.experiment}"

    def get_logs(
        self,
        *,
        student_id: str | None = None,
        trial: str | None = None,
        func_name: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        n: int = 100,
        order: str = "latest",
        after_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Query logs with optional filters.

        Args:
            student_id: Filter by student.
            trial: Filter by trial name.
            func_name: Filter by function name.
            start_time: ISO 8601 lower bound.
            end_time: ISO 8601 upper bound.
            n: Max results (1–10000, default 100).
            order: "latest" (default) or "earliest".
            after_id: Cursor for pagination.

        Returns:
            List of log entry dicts.
        """
        params: dict[str, Any] = {}
        if student_id is not None:
            params["student_id"] = student_id
        if trial is not None:
            params["trial_name"] = trial
        if func_name is not None:
            params["func_name"] = func_name
        if start_time is not None:
            params["start_time"] = start_time
        if end_time is not None:
            params["end_time"] = end_time
        if n != 100:
            params["n"] = n
        if order != "latest":
            params["order"] = order
        if after_id is not None:
            params["after_id"] = after_id

        data = self._get(f"{self._api_base}/logs", params=params)
        return data["logs"]

    def get_log_options(self) -> dict[str, Any]:
        """Get filter options (students, trials) for the experiment.

        Returns:
            Dict with "students" and "trials" lists.
        """
        return self._get(f"{self._api_base}/log-options")

    def get_all_logs(self, *, page_size: int = 1000, **filter_kwargs) -> list[dict[str, Any]]:
        """Fetch all logs matching filters by auto-paginating with cursor.

        Iterates until a page returns fewer than page_size results.

        Args:
            page_size: Results per page (default 1000).
            **filter_kwargs: Same keyword args as get_logs (except after_id).

        Returns:
            List of all matching log entry dicts.
        """
        all_logs: list[dict] = []
        after_id = None
        order = filter_kwargs.pop("order", "latest")

        while True:
            logs = self.get_logs(
                n=page_size,
                order=order,
                after_id=after_id,
                **filter_kwargs,
            )
            if not logs:
                break
            all_logs.extend(logs)
            if len(logs) < page_size:
                break
            after_id = logs[-1]["id"]

        return all_logs

    def _get(self, url: str, params: dict | None = None) -> dict:
        resp = requests.get(url, params=params)
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
