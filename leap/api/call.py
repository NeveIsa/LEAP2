"""POST /exp/{experiment}/call — RPC endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from leap.core import rpc, storage

router = APIRouter()


class CallRequest(BaseModel):
    student_id: str
    func_name: str
    args: list | None = None
    kwargs: dict | None = None
    trial: str | None = None


@router.post("/exp/{experiment}/call")
async def call_function(experiment: str, body: CallRequest, request: Request):
    experiments = request.app.state.experiments
    if experiment not in experiments:
        raise HTTPException(404, detail=f"Experiment '{experiment}' not found")

    exp_info = experiments[experiment]
    session = storage.get_session(experiment, exp_info.db_path)

    try:
        result = rpc.execute_rpc(
            exp_info,
            session,
            func_name=body.func_name,
            args=body.args,
            kwargs=body.kwargs,
            student_id=body.student_id,
            trial=body.trial,
        )
        return {"result": result}
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(403, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(500, detail=str(e))
    finally:
        session.close()
