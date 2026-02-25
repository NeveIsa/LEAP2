"""Root-level API: experiments list, health, functions, is-registered, login/logout."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from leap.core import auth, storage
from leap import __version__

router = APIRouter()


@router.get("/api/experiments")
async def list_experiments(request: Request):
    experiments = request.app.state.experiments
    result = []
    for exp in experiments.values():
        meta = exp.to_metadata()
        try:
            session = storage.get_session(exp.name, exp.db_path)
            meta["student_count"] = storage.count_students(session)
            session.close()
        except Exception:
            meta["student_count"] = 0
        result.append(meta)
    return {"experiments": result}


@router.get("/api/health")
async def health():
    return {"ok": True, "version": __version__}


@router.get("/exp/{experiment}/functions")
async def list_functions(experiment: str, request: Request):
    experiments = request.app.state.experiments
    if experiment not in experiments:
        raise HTTPException(404, detail=f"Experiment '{experiment}' not found")
    return experiments[experiment].get_functions_info()


@router.get("/exp/{experiment}/readme")
async def get_readme(experiment: str, request: Request):
    experiments = request.app.state.experiments
    if experiment not in experiments:
        raise HTTPException(404, detail=f"Experiment '{experiment}' not found")
    exp = experiments[experiment]
    if not exp.readme_path.exists():
        raise HTTPException(404, detail="No README found for this experiment")
    text = exp.readme_path.read_text(encoding="utf-8")
    frontmatter = dict(exp.frontmatter)
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            body = parts[2].strip()
    return {"frontmatter": frontmatter, "body": body}


@router.get("/exp/{experiment}/is-registered")
async def is_registered(experiment: str, student_id: str = Query(...), request: Request = None):
    experiments = request.app.state.experiments
    if experiment not in experiments:
        raise HTTPException(404, detail=f"Experiment '{experiment}' not found")

    exp_info = experiments[experiment]
    session = storage.get_session(experiment, exp_info.db_path)
    try:
        registered = storage.is_registered(session, student_id)
        return {"registered": registered}
    finally:
        session.close()


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
async def login(body: LoginRequest, request: Request):
    root = getattr(request.app.state, "root", None)
    cred = auth.load_credentials(root)
    if not cred:
        raise HTTPException(500, detail="No admin credentials configured")
    if not auth.verify_password(body.password, cred):
        raise HTTPException(401, detail="Invalid password")
    request.session["admin"] = True
    return {"ok": True}


@router.get("/api/auth-status")
async def auth_status(request: Request):
    is_admin = request.session.get("admin", False)
    return {"admin": bool(is_admin)}


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"ok": True}
