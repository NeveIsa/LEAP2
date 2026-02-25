"""Tests for leap.core.storage — models, CRUD, log queries."""

from __future__ import annotations

import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from leap.core import storage


@pytest.fixture
def db_session(tmp_path: Path):
    db_path = tmp_path / "db" / "test.db"
    db_path.parent.mkdir(parents=True)
    session = storage.get_session("test", db_path)
    yield session
    session.close()
    storage.close_all_engines()


# ── Student CRUD ──


class TestStudentCRUD:
    def test_add_and_list(self, db_session):
        storage.add_student(db_session, "s001", "Alice")
        storage.add_student(db_session, "s002", "Bob", email="bob@test.com")
        students = storage.list_students(db_session)
        assert len(students) == 2
        assert students[0]["student_id"] == "s001"
        assert students[1]["email"] == "bob@test.com"

    def test_add_duplicate_raises(self, db_session):
        storage.add_student(db_session, "s001", "Alice")
        with pytest.raises(ValueError, match="already exists"):
            storage.add_student(db_session, "s001", "Alice 2")

    def test_delete_student(self, db_session):
        storage.add_student(db_session, "s001", "Alice")
        assert storage.delete_student(db_session, "s001") is True
        assert storage.list_students(db_session) == []

    def test_delete_nonexistent(self, db_session):
        assert storage.delete_student(db_session, "nobody") is False

    def test_is_registered(self, db_session):
        assert storage.is_registered(db_session, "s001") is False
        storage.add_student(db_session, "s001", "Alice")
        assert storage.is_registered(db_session, "s001") is True

    def test_delete_cascades_logs(self, db_session):
        storage.add_student(db_session, "s001", "Alice")
        storage.add_log(
            db_session,
            student_id="s001", experiment="test",
            func_name="square", args=[7], result=49,
        )
        assert len(storage.query_logs(db_session)) == 1
        storage.delete_student(db_session, "s001")
        assert len(storage.query_logs(db_session)) == 0

    def test_delete_only_cascades_own_logs(self, db_session):
        storage.add_student(db_session, "s001", "Alice")
        storage.add_student(db_session, "s002", "Bob")
        storage.add_log(
            db_session,
            student_id="s001", experiment="t", func_name="f", args=[],
        )
        storage.add_log(
            db_session,
            student_id="s002", experiment="t", func_name="f", args=[],
        )
        storage.delete_student(db_session, "s001")
        remaining = storage.query_logs(db_session)
        assert len(remaining) == 1
        assert remaining[0]["student_id"] == "s002"

    def test_add_student_with_email(self, db_session):
        s = storage.add_student(db_session, "s001", "Alice", email="alice@u.edu")
        assert s.email == "alice@u.edu"
        students = storage.list_students(db_session)
        assert students[0]["email"] == "alice@u.edu"

    def test_add_student_without_email(self, db_session):
        storage.add_student(db_session, "s001", "Alice")
        students = storage.list_students(db_session)
        assert students[0]["email"] is None

    def test_list_students_ordered(self, db_session):
        storage.add_student(db_session, "charlie", "Charlie")
        storage.add_student(db_session, "alice", "Alice")
        storage.add_student(db_session, "bob", "Bob")
        students = storage.list_students(db_session)
        ids = [s["student_id"] for s in students]
        assert ids == ["alice", "bob", "charlie"]

    def test_list_students_empty(self, db_session):
        assert storage.list_students(db_session) == []


# ── Log CRUD ──


class TestLogCRUD:
    def test_add_and_query(self, db_session):
        storage.add_log(
            db_session,
            student_id="s001", experiment="test",
            func_name="square", args=[7], result=49,
        )
        logs = storage.query_logs(db_session)
        assert len(logs) == 1
        log = logs[0]
        assert log["func_name"] == "square"
        assert log["args"] == [7]
        assert log["result"] == 49
        assert log["error"] is None
        assert log["ts"] is not None

    def test_log_id_monotonically_increasing(self, db_session):
        ids = []
        for i in range(10):
            log = storage.add_log(
                db_session,
                student_id="s001", experiment="t", func_name="f", args=[i],
            )
            ids.append(log.id)
        assert ids == sorted(ids)
        assert len(set(ids)) == 10

    def test_log_timestamp_format(self, db_session):
        storage.add_log(
            db_session,
            student_id="s001", experiment="t", func_name="f", args=[],
        )
        logs = storage.query_logs(db_session)
        ts_str = logs[0]["ts"]
        assert ts_str.endswith("Z")
        assert "T" in ts_str
        # DuckDB TIMESTAMP is timezone-naive; just verify it parses as ISO 8601
        parsed = datetime.fromisoformat(ts_str.replace("Z", ""))
        assert parsed.year >= 2025

    def test_log_complex_args(self, db_session):
        complex_args = [{"nested": [1, 2, 3]}, "hello", 3.14, None, True]
        storage.add_log(
            db_session,
            student_id="s001", experiment="t", func_name="f",
            args=complex_args,
        )
        logs = storage.query_logs(db_session)
        assert logs[0]["args"] == complex_args

    def test_log_complex_result(self, db_session):
        complex_result = {"matrix": [[1, 0], [0, 1]], "label": "identity"}
        storage.add_log(
            db_session,
            student_id="s001", experiment="t", func_name="f",
            args=[], result=complex_result,
        )
        logs = storage.query_logs(db_session)
        assert logs[0]["result"] == complex_result

    def test_log_none_result(self, db_session):
        storage.add_log(
            db_session,
            student_id="s001", experiment="t", func_name="f",
            args=[], result=None,
        )
        logs = storage.query_logs(db_session)
        assert logs[0]["result"] is None

    def test_log_zero_result(self, db_session):
        storage.add_log(
            db_session,
            student_id="s001", experiment="t", func_name="f",
            args=[], result=0,
        )
        logs = storage.query_logs(db_session)
        assert logs[0]["result"] == 0

    def test_log_false_result(self, db_session):
        storage.add_log(
            db_session,
            student_id="s001", experiment="t", func_name="f",
            args=[], result=False,
        )
        logs = storage.query_logs(db_session)
        assert logs[0]["result"] is False

    def test_log_string_result(self, db_session):
        storage.add_log(
            db_session,
            student_id="s001", experiment="t", func_name="f",
            args=[], result="hello world",
        )
        logs = storage.query_logs(db_session)
        assert logs[0]["result"] == "hello world"

    def test_log_with_trial(self, db_session):
        storage.add_log(
            db_session,
            student_id="s001", experiment="t", func_name="f",
            args=[], trial="run-1",
        )
        logs = storage.query_logs(db_session, trial="run-1")
        assert len(logs) == 1
        assert logs[0]["trial"] == "run-1"

    def test_log_null_trial_not_matched(self, db_session):
        storage.add_log(
            db_session,
            student_id="s001", experiment="t", func_name="f",
            args=[], trial=None,
        )
        storage.add_log(
            db_session,
            student_id="s001", experiment="t", func_name="f",
            args=[], trial="run-1",
        )
        logs = storage.query_logs(db_session, trial="run-1")
        assert len(logs) == 1

    def test_log_with_error(self, db_session):
        storage.add_log(
            db_session,
            student_id="s001", experiment="t", func_name="f",
            args=[], error="ZeroDivisionError: division by zero",
        )
        logs = storage.query_logs(db_session)
        assert logs[0]["error"] == "ZeroDivisionError: division by zero"

    def test_log_experiment_column(self, db_session):
        storage.add_log(
            db_session,
            student_id="s001", experiment="lab-alpha", func_name="f", args=[],
        )
        logs = storage.query_logs(db_session)
        assert logs[0]["experiment"] == "lab-alpha"


# ── Log Query Filters ──


class TestLogQueryFilters:
    def test_filter_student(self, db_session):
        storage.add_log(db_session, student_id="s001", experiment="t", func_name="f", args=[])
        storage.add_log(db_session, student_id="s002", experiment="t", func_name="f", args=[])
        logs = storage.query_logs(db_session, student_id="s001")
        assert len(logs) == 1
        assert logs[0]["student_id"] == "s001"

    def test_filter_func_name(self, db_session):
        storage.add_log(db_session, student_id="s001", experiment="t", func_name="square", args=[])
        storage.add_log(db_session, student_id="s001", experiment="t", func_name="cubic", args=[])
        logs = storage.query_logs(db_session, func_name="square")
        assert len(logs) == 1
        assert logs[0]["func_name"] == "square"

    def test_filter_trial(self, db_session):
        storage.add_log(db_session, student_id="s001", experiment="t", func_name="f", args=[], trial="a")
        storage.add_log(db_session, student_id="s001", experiment="t", func_name="f", args=[], trial="b")
        storage.add_log(db_session, student_id="s001", experiment="t", func_name="f", args=[])
        logs = storage.query_logs(db_session, trial="a")
        assert len(logs) == 1

    def test_filter_start_time(self, db_session):
        storage.add_log(db_session, student_id="s001", experiment="t", func_name="f", args=[1])
        time.sleep(0.05)
        cutoff = datetime.now(timezone.utc)
        time.sleep(0.05)
        storage.add_log(db_session, student_id="s001", experiment="t", func_name="f", args=[2])

        logs = storage.query_logs(db_session, start_time=cutoff, order="earliest")
        assert len(logs) == 1
        assert logs[0]["args"] == [2]

    def test_filter_end_time(self, db_session):
        storage.add_log(db_session, student_id="s001", experiment="t", func_name="f", args=[1])
        time.sleep(0.05)
        cutoff = datetime.now(timezone.utc)
        time.sleep(0.05)
        storage.add_log(db_session, student_id="s001", experiment="t", func_name="f", args=[2])

        logs = storage.query_logs(db_session, end_time=cutoff, order="earliest")
        assert len(logs) == 1
        assert logs[0]["args"] == [1]

    def test_filter_time_range(self, db_session):
        storage.add_log(db_session, student_id="s001", experiment="t", func_name="f", args=[1])
        time.sleep(0.05)
        t1 = datetime.now(timezone.utc)
        time.sleep(0.05)
        storage.add_log(db_session, student_id="s001", experiment="t", func_name="f", args=[2])
        time.sleep(0.05)
        t2 = datetime.now(timezone.utc)
        time.sleep(0.05)
        storage.add_log(db_session, student_id="s001", experiment="t", func_name="f", args=[3])

        logs = storage.query_logs(db_session, start_time=t1, end_time=t2, order="earliest")
        assert len(logs) == 1
        assert logs[0]["args"] == [2]

    def test_combined_filters(self, db_session):
        storage.add_log(db_session, student_id="s001", experiment="t", func_name="square", args=[], trial="a")
        storage.add_log(db_session, student_id="s001", experiment="t", func_name="cubic", args=[], trial="a")
        storage.add_log(db_session, student_id="s002", experiment="t", func_name="square", args=[], trial="a")
        storage.add_log(db_session, student_id="s001", experiment="t", func_name="square", args=[], trial="b")

        logs = storage.query_logs(
            db_session, student_id="s001", func_name="square", trial="a",
        )
        assert len(logs) == 1

    def test_filter_no_match(self, db_session):
        storage.add_log(db_session, student_id="s001", experiment="t", func_name="f", args=[])
        logs = storage.query_logs(db_session, student_id="nobody")
        assert len(logs) == 0


# ── Log Query Ordering, Limit, Pagination ──


class TestLogQueryPagination:
    def test_order_latest(self, db_session):
        for i in range(5):
            storage.add_log(db_session, student_id="s001", experiment="t", func_name="f", args=[i])
        logs = storage.query_logs(db_session, n=3, order="latest")
        assert len(logs) == 3
        assert logs[0]["id"] > logs[1]["id"] > logs[2]["id"]

    def test_order_earliest(self, db_session):
        for i in range(5):
            storage.add_log(db_session, student_id="s001", experiment="t", func_name="f", args=[i])
        logs = storage.query_logs(db_session, n=3, order="earliest")
        assert len(logs) == 3
        assert logs[0]["id"] < logs[1]["id"] < logs[2]["id"]

    def test_limit_default_100(self, db_session):
        for i in range(150):
            storage.add_log(db_session, student_id="s001", experiment="t", func_name="f", args=[i])
        logs = storage.query_logs(db_session)
        assert len(logs) == 100

    def test_n_clamped_to_1_minimum(self, db_session):
        storage.add_log(db_session, student_id="s001", experiment="t", func_name="f", args=[])
        logs = storage.query_logs(db_session, n=0)
        assert len(logs) == 1

    def test_n_clamped_to_10000_maximum(self, db_session):
        storage.add_log(db_session, student_id="s001", experiment="t", func_name="f", args=[])
        logs = storage.query_logs(db_session, n=20000)
        assert len(logs) == 1  # only 1 log exists, but n was clamped not rejected

    def test_cursor_pagination_latest(self, db_session):
        for i in range(5):
            storage.add_log(db_session, student_id="s001", experiment="t", func_name="f", args=[i])

        page1 = storage.query_logs(db_session, n=2, order="latest")
        assert len(page1) == 2
        cursor = page1[-1]["id"]

        page2 = storage.query_logs(db_session, n=2, order="latest", after_id=cursor)
        assert len(page2) == 2
        assert all(log["id"] < cursor for log in page2)

        page3 = storage.query_logs(db_session, n=2, order="latest", after_id=page2[-1]["id"])
        assert len(page3) == 1  # last page

    def test_cursor_pagination_earliest(self, db_session):
        for i in range(5):
            storage.add_log(db_session, student_id="s001", experiment="t", func_name="f", args=[i])

        page1 = storage.query_logs(db_session, n=2, order="earliest")
        assert len(page1) == 2
        cursor = page1[-1]["id"]

        page2 = storage.query_logs(db_session, n=2, order="earliest", after_id=cursor)
        assert len(page2) == 2
        assert all(log["id"] > cursor for log in page2)

    def test_pagination_exhausted(self, db_session):
        storage.add_log(db_session, student_id="s001", experiment="t", func_name="f", args=[])
        logs = storage.query_logs(db_session, n=10, order="latest")
        assert len(logs) == 1
        cursor = logs[0]["id"]
        empty = storage.query_logs(db_session, n=10, order="latest", after_id=cursor)
        assert len(empty) == 0

    def test_empty_db_query(self, db_session):
        assert storage.query_logs(db_session) == []


# ── Log Options ──


class TestLogOptions:
    def test_get_log_options(self, db_session):
        storage.add_student(db_session, "s001", "Alice")
        storage.add_student(db_session, "s002", "Bob")
        storage.add_log(
            db_session,
            student_id="s001", experiment="t", func_name="f", args=[], trial="run-1",
        )
        storage.add_log(
            db_session,
            student_id="s001", experiment="t", func_name="f", args=[], trial="run-2",
        )
        opts = storage.get_log_options(db_session)
        assert "s001" in opts["students"]
        assert "s002" in opts["students"]
        assert set(opts["trials"]) == {"run-1", "run-2"}

    def test_log_options_no_trials(self, db_session):
        storage.add_student(db_session, "s001", "Alice")
        storage.add_log(
            db_session,
            student_id="s001", experiment="t", func_name="f", args=[],
        )
        opts = storage.get_log_options(db_session)
        assert opts["trials"] == []

    def test_log_options_no_students(self, db_session):
        opts = storage.get_log_options(db_session)
        assert opts["students"] == []
        assert opts["trials"] == []

    def test_log_options_deduplicates_trials(self, db_session):
        storage.add_student(db_session, "s001", "Alice")
        for _ in range(3):
            storage.add_log(
                db_session,
                student_id="s001", experiment="t", func_name="f",
                args=[], trial="same-trial",
            )
        opts = storage.get_log_options(db_session)
        assert opts["trials"] == ["same-trial"]


# ── log_to_dict ──


class TestLogToDict:
    def test_all_fields_present(self, db_session):
        storage.add_log(
            db_session,
            student_id="s001", experiment="test", func_name="square",
            args=[7], result=49, trial="run-1",
        )
        logs = storage.query_logs(db_session)
        log = logs[0]
        expected_keys = {"id", "ts", "student_id", "experiment", "trial", "func_name", "args", "result", "error"}
        assert set(log.keys()) == expected_keys

    def test_ts_format_iso8601_utc(self, db_session):
        storage.add_log(
            db_session,
            student_id="s001", experiment="t", func_name="f", args=[],
        )
        logs = storage.query_logs(db_session)
        ts = logs[0]["ts"]
        assert ts.endswith("Z")
        assert "T" in ts


# ── Engine management ──


class TestEngineManagement:
    def test_close_all_engines(self, tmp_path):
        db_path = tmp_path / "db" / "test.db"
        db_path.parent.mkdir(parents=True)
        session = storage.get_session("test", db_path)
        session.close()
        storage.close_all_engines()
        # After close, getting a new session should reinitialize
        session2 = storage.get_session("test", db_path)
        storage.add_student(session2, "s001", "Alice")
        assert len(storage.list_students(session2)) == 1
        session2.close()
        storage.close_all_engines()

    def test_multiple_experiments_separate_dbs(self, tmp_path):
        db1 = tmp_path / "exp1" / "db" / "experiment.db"
        db2 = tmp_path / "exp2" / "db" / "experiment.db"
        db1.parent.mkdir(parents=True)
        db2.parent.mkdir(parents=True)

        s1 = storage.get_session("exp1", db1)
        s2 = storage.get_session("exp2", db2)

        storage.add_student(s1, "s001", "Alice")
        storage.add_student(s2, "s002", "Bob")

        assert len(storage.list_students(s1)) == 1
        assert storage.list_students(s1)[0]["student_id"] == "s001"
        assert len(storage.list_students(s2)) == 1
        assert storage.list_students(s2)[0]["student_id"] == "s002"

        s1.close()
        s2.close()
        storage.close_all_engines()
