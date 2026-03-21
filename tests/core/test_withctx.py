"""Tests for @withctx decorator and ctx proxy — context injection for RPC functions."""

from __future__ import annotations

from pathlib import Path

import pytest

from leap.core import rpc, storage
from leap.core.experiment import ExperimentInfo


@pytest.fixture
def ctx_exp(tmp_path: Path):
    """Experiment with a @withctx function that reads ctx."""
    exp_dir = tmp_path / "experiments" / "ctxlab"
    funcs_dir = exp_dir / "funcs"
    funcs_dir.mkdir(parents=True)
    (exp_dir / "db").mkdir()
    (exp_dir / "README.md").write_text(
        "---\nname: ctxlab\nrequire_registration: false\n---\n"
    )
    (funcs_dir / "ctx_funcs.py").write_text(
        "from leap import withctx, ctx\n\n"
        "@withctx\n"
        "def whoami():\n"
        '    """Return caller context."""\n'
        "    return {'student': ctx.student_id, 'trial': ctx.trial, 'experiment': ctx.experiment}\n\n"
        "@withctx\n"
        "def get_trial():\n"
        "    return ctx.trial\n\n"
        "def plain(x):\n"
        "    return x * 2\n"
    )
    exp = ExperimentInfo("ctxlab", exp_dir)
    session = storage.get_session("ctxlab", exp.db_path)
    yield exp, session
    session.close()
    storage.close_all_engines()


class TestWithctxDecorator:
    def test_flag_set(self):
        @rpc.withctx
        def fn(): pass
        assert rpc._has_flag(fn, "_leap_withctx") is True

    def test_no_flag_by_default(self):
        def fn(): pass
        assert rpc._has_flag(fn, "_leap_withctx") is False

    def test_preserves_function(self):
        @rpc.withctx
        def calc(x): return x + 1
        assert calc(5) == 6

    def test_combined_with_nolog(self):
        @rpc.nolog
        @rpc.withctx
        def fn(): pass
        assert rpc._has_flag(fn, "_leap_withctx") is True
        assert rpc._has_flag(fn, "_leap_nolog") is True


class TestCtxInjection:
    def test_student_id_injected(self, ctx_exp):
        exp, session = ctx_exp
        result = rpc.execute_rpc(
            exp, session, func_name="whoami", args=[], student_id="alice"
        )
        assert result["student"] == "alice"

    def test_trial_injected(self, ctx_exp):
        exp, session = ctx_exp
        result = rpc.execute_rpc(
            exp, session, func_name="get_trial", args=[], student_id="s001", trial="run-A"
        )
        assert result == "run-A"

    def test_experiment_name_injected(self, ctx_exp):
        exp, session = ctx_exp
        result = rpc.execute_rpc(
            exp, session, func_name="whoami", args=[], student_id="s001"
        )
        assert result["experiment"] == "ctxlab"

    def test_trial_none_when_omitted(self, ctx_exp):
        exp, session = ctx_exp
        result = rpc.execute_rpc(
            exp, session, func_name="whoami", args=[], student_id="s001"
        )
        assert result["trial"] is None

    def test_plain_function_unaffected(self, ctx_exp):
        """Non-@withctx functions work normally without context."""
        exp, session = ctx_exp
        result = rpc.execute_rpc(
            exp, session, func_name="plain", args=[7], student_id="s001"
        )
        assert result == 14

    def test_multiple_students_isolated(self, ctx_exp):
        """Different student calls get their own context."""
        exp, session = ctx_exp
        r1 = rpc.execute_rpc(exp, session, func_name="whoami", args=[], student_id="alice", trial="t1")
        r2 = rpc.execute_rpc(exp, session, func_name="whoami", args=[], student_id="bob", trial="t2")
        assert r1["student"] == "alice"
        assert r1["trial"] == "t1"
        assert r2["student"] == "bob"
        assert r2["trial"] == "t2"
