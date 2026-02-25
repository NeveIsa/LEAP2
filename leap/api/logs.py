"""GET /exp/{experiment}/logs and /log-options — Log query endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request

from leap.core import storage

router = APIRouter()


@router.get("/exp/{experiment}/logs")
async def get_logs(
    experiment: str,
    request: Request,
    sid: str | None = Query(None, alias="student_id"),
    trial: str | None = Query(None, alias="trial_name"),
    func_name: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    n: int = Query(100, ge=1, le=10_000),
    order: str = Query("latest", pattern="^(latest|earliest)$"),
    after_id: int | None = None,
):
    experiments = request.app.state.experiments
    if experiment not in experiments:
        raise HTTPException(404, detail=f"Experiment '{experiment}' not found")

    exp_info = experiments[experiment]

    if func_name and func_name not in exp_info.functions:
        raise HTTPException(400, detail=f"Unknown function: '{func_name}'")

    session = storage.get_session(experiment, exp_info.db_path)
    try:
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
    finally:
        session.close()


@router.get("/exp/{experiment}/log-options")
async def get_log_options(experiment: str, request: Request):
    experiments = request.app.state.experiments
    if experiment not in experiments:
        raise HTTPException(404, detail=f"Experiment '{experiment}' not found")

    exp_info = experiments[experiment]
    session = storage.get_session(experiment, exp_info.db_path)
    try:
        return storage.get_log_options(session)
    finally:
        session.close()
