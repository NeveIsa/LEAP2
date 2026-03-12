"""GET /exp/{experiment}/logs and /log-options — Log query endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from leap.api.deps import get_db_session, get_experiment_info
from leap.core import storage
from leap.core.experiment import ExperimentInfo

router = APIRouter()


@router.get("/exp/{experiment}/logs")
async def get_logs(
    exp_info: ExperimentInfo = Depends(get_experiment_info),
    session: Session = Depends(get_db_session),
    sid: str | None = Query(None, alias="student_id"),
    trial: str | None = Query(None, alias="trial_name"),
    func_name: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    n: int = Query(100, ge=1, le=10_000),
    order: str = Query("latest", pattern="^(latest|earliest)$"),
    after_id: int | None = None,
):
    if func_name and func_name not in exp_info.functions:
        raise HTTPException(400, detail=f"Unknown function: '{func_name}'")

    logs = storage.query_logs(
        session,
        student_id=sid,
        trial=trial,
        func_name=func_name,
        start_time=start_time,
        end_time=end_time,
        n=n,
        order=order,
        after_id=after_id,
    )
    return {"logs": logs}


@router.get("/exp/{experiment}/log-options")
async def get_log_options(
    session: Session = Depends(get_db_session),
):
    return storage.get_log_options(session)
