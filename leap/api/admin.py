"""Admin endpoints under /exp/{experiment}/admin/ — protected by require_admin."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from leap.api.deps import get_db_session, get_experiment_info
from leap.core import auth, storage
from leap.core.experiment import ExperimentInfo
from leap.middleware.auth import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


class AddStudentRequest(BaseModel):
    student_id: str
    name: str
    email: str | None = None


class DeleteStudentRequest(BaseModel):
    student_id: str


class DeleteLogRequest(BaseModel):
    log_id: int


class ImportStudentRow(BaseModel):
    student_id: str
    name: str = ""
    email: str | None = None


class ImportStudentsRequest(BaseModel):
    students: list[ImportStudentRow]


@router.post("/exp/{experiment}/admin/add-student")
async def add_student(
    body: AddStudentRequest,
    session: Session = Depends(get_db_session),
):
    try:
        storage.add_student(session, body.student_id, body.name, body.email)
        return {"ok": True, "student_id": body.student_id}
    except ValueError as e:
        raise HTTPException(409, detail=str(e))


@router.get("/exp/{experiment}/admin/students")
async def list_students(
    session: Session = Depends(get_db_session),
):
    return {"students": storage.list_students(session)}


@router.post("/exp/{experiment}/admin/delete-student")
async def delete_student(
    body: DeleteStudentRequest,
    session: Session = Depends(get_db_session),
):
    deleted = storage.delete_student(session, body.student_id)
    if not deleted:
        raise HTTPException(404, detail=f"Student '{body.student_id}' not found")
    return {"ok": True, "student_id": body.student_id}


@router.post("/exp/{experiment}/admin/import-students")
async def import_students(
    body: ImportStudentsRequest,
    session: Session = Depends(get_db_session),
):
    result = storage.bulk_add_students(session, [s.model_dump() for s in body.students])
    return {"ok": True, **result}


@router.post("/exp/{experiment}/admin/delete-log")
async def delete_log(
    body: DeleteLogRequest,
    session: Session = Depends(get_db_session),
):
    deleted = storage.delete_log(session, body.log_id)
    if not deleted:
        raise HTTPException(404, detail=f"Log id {body.log_id} not found")
    return {"ok": True, "log_id": body.log_id}


@router.post("/exp/{experiment}/admin/reload-functions")
async def reload_functions(
    exp_info: ExperimentInfo = Depends(get_experiment_info),
):
    count = exp_info.reload_functions()
    return {"ok": True, "functions_loaded": count}


@router.get("/exp/{experiment}/admin/export-logs")
async def export_logs(
    session: Session = Depends(get_db_session),
    exp_info: ExperimentInfo = Depends(get_experiment_info),
    fmt: str = Query("jsonlines", alias="format"),
):
    if fmt not in ("jsonlines", "csv"):
        raise HTTPException(400, detail=f"Unknown format '{fmt}'. Use 'jsonlines' or 'csv'.")
    all_logs: list[dict] = []
    after_id = None
    while True:
        page = storage.query_logs(session, n=5000, order="earliest", after_id=after_id)
        if not page:
            break
        all_logs.extend(page)
        if len(page) < 5000:
            break
        after_id = page[-1]["id"]
    return {"ok": True, "format": fmt, "count": len(all_logs), "logs": all_logs}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/api/admin/change-password")
async def change_password(body: ChangePasswordRequest, request: Request):
    root = getattr(request.app.state, "root", None)
    cred = auth.load_credentials(root)
    if not cred:
        raise HTTPException(500, detail="No admin credentials configured")
    if not auth.verify_password(body.current_password, cred):
        raise HTTPException(401, detail="Current password is incorrect")
    if not body.new_password.strip():
        raise HTTPException(400, detail="New password cannot be empty")
    new_cred = auth.hash_password(body.new_password)
    auth.save_credentials(new_cred, root)
    return {"ok": True}
