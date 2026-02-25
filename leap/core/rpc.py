"""RPC execution, logging, and function decorators."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from leap.core import storage

logger = logging.getLogger(__name__)

STUDENT_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,255}$")


def nolog(func):
    """Decorator: skip logging for this function (high-frequency calls)."""
    func._leap_nolog = True
    return func


def noregcheck(func):
    """Decorator: skip registration check for this function."""
    func._leap_noregcheck = True
    return func


def _has_flag(func, flag: str) -> bool:
    return getattr(func, flag, False)


def validate_student_id(student_id: str) -> bool:
    return bool(STUDENT_ID_RE.match(student_id))


def execute_rpc(
    experiment,  # ExperimentInfo
    session: storage.Session,
    *,
    func_name: str,
    args: list | None = None,
    kwargs: dict | None = None,
    student_id: str,
    trial: str | None = None,
) -> Any:
    """Execute an RPC call: validate, run function, log result."""
    if func_name not in experiment.functions:
        raise ValueError(f"Unknown function: '{func_name}'")

    func = experiment.functions[func_name]

    if not validate_student_id(student_id):
        raise ValueError(f"Invalid student_id: '{student_id}'")

    skip_regcheck = _has_flag(func, "_leap_noregcheck")
    if not skip_regcheck and experiment.require_registration:
        if not storage.is_registered(session, student_id):
            raise PermissionError(f"Student '{student_id}' is not registered")

    args = args or []
    kwargs = kwargs or {}
    error_msg = None
    result = None

    try:
        result = func(*args, **kwargs)
    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        logger.warning("RPC %s.%s raised: %s", experiment.name, func_name, error_msg)

    skip_log = _has_flag(func, "_leap_nolog")
    if not skip_log:
        try:
            storage.add_log(
                session,
                student_id=student_id,
                experiment=experiment.name,
                func_name=func_name,
                args=args,
                result=result,
                error=error_msg,
                trial=trial,
            )
        except Exception:
            logger.exception("Failed to log RPC call %s.%s", experiment.name, func_name)

    if error_msg:
        raise RuntimeError(error_msg)

    return result
