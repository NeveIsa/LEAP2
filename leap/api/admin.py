"""Admin endpoints under /exp/{experiment}/admin/ — protected by require_admin."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from leap.core import storage
from leap.middleware.auth import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


class AddStudentRequest(BaseModel):
    student_id: str
    name: str
    email: str | None = None


class DeleteStudentRequest(BaseModel):
    student_id: str


def _get_experiment(experiment: str, request: Request):
    experiments = request.app.state.experiments
    if experiment not in experiments:
        raise HTTPException(404, detail=f"Experiment '{experiment}' not found")
    return experiments[experiment]


@router.post("/exp/{experiment}/admin/add-student")
async def add_student(experiment: str, body: AddStudentRequest, request: Request):
    exp_info = _get_experiment(experiment, request)
    session = storage.get_session(experiment, exp_info.db_path)
    try:
        storage.add_student(session, body.student_id, body.name, body.email)
        return {"ok": True, "student_id": body.student_id}
    except ValueError as e:
        raise HTTPException(409, detail=str(e))
    finally:
        session.close()


@router.get("/exp/{experiment}/admin/students")
async def list_students(experiment: str, request: Request):
    exp_info = _get_experiment(experiment, request)
    session = storage.get_session(experiment, exp_info.db_path)
    try:
        return {"students": storage.list_students(session)}
    finally:
        session.close()


@router.post("/exp/{experiment}/admin/delete-student")
async def delete_student(experiment: str, body: DeleteStudentRequest, request: Request):
    exp_info = _get_experiment(experiment, request)
    session = storage.get_session(experiment, exp_info.db_path)
    try:
        deleted = storage.delete_student(session, body.student_id)
        if not deleted:
            raise HTTPException(404, detail=f"Student '{body.student_id}' not found")
        return {"ok": True, "student_id": body.student_id}
    finally:
        session.close()


@router.post("/exp/{experiment}/admin/reload-functions")
async def reload_functions(experiment: str, request: Request):
    exp_info = _get_experiment(experiment, request)
    count = exp_info.reload_functions()
    return {"ok": True, "functions_loaded": count}
