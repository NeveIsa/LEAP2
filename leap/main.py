"""FastAPI application assembly and startup."""

from __future__ import annotations

import logging
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles

from leap import __version__
from leap.config import get_root, ui_dir, SESSION_SECRET_KEY, DEFAULT_EXPERIMENT
from leap.core.auth import ensure_credentials
from leap.core.experiment import discover_experiments
from leap.api import call, logs, admin, experiments

logger = logging.getLogger(__name__)


def create_app(root=None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        resolved_root = root or get_root()
        app.state.root = resolved_root
        logger.info("LEAP2 root: %s", resolved_root)

        ensure_credentials(resolved_root)

        exps = discover_experiments(resolved_root)
        app.state.experiments = exps
        logger.info("Loaded %d experiment(s): %s", len(exps), ", ".join(exps.keys()) or "(none)")

        ui_root = ui_dir(resolved_root)

        shared_dir = ui_root / "shared"
        if shared_dir.is_dir():
            app.mount("/static", StaticFiles(directory=str(shared_dir)), name="static-assets")
            logger.info("Mounted /static -> %s", shared_dir)

        for exp_name, exp_info in exps.items():
            if exp_info.ui_dir.is_dir():
                mount_path = f"/exp/{exp_name}/ui"
                app.mount(mount_path, StaticFiles(directory=str(exp_info.ui_dir)), name=f"ui-{exp_name}")
                logger.info("Mounted %s -> %s", mount_path, exp_info.ui_dir)

        app.state.ui_root = ui_root
        yield

    app = FastAPI(title="LEAP2", version=__version__, lifespan=lifespan)

    secret = SESSION_SECRET_KEY or secrets.token_hex(32)
    app.add_middleware(SessionMiddleware, secret_key=secret)

    cors_origins = os.environ.get("CORS_ORIGINS", "")
    if cors_origins:
        origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(call.router)
    app.include_router(logs.router)
    app.include_router(admin.router)
    app.include_router(experiments.router)

    @app.get("/", include_in_schema=False)
    async def landing(request: Request):
        exps = getattr(request.app.state, "experiments", {})
        if DEFAULT_EXPERIMENT and DEFAULT_EXPERIMENT in exps:
            entry = exps[DEFAULT_EXPERIMENT].entry_point
            return RedirectResponse(
                url=f"/exp/{DEFAULT_EXPERIMENT}/ui/{entry}",
                status_code=307,
            )

        landing_file = getattr(request.app.state, "ui_root", Path()) / "landing" / "index.html"
        if landing_file.is_file():
            return FileResponse(str(landing_file), media_type="text/html")
        return {"message": "LEAP2 is running. No landing page found at ui/landing/index.html."}

    @app.get("/login", include_in_schema=False)
    async def login_page(request: Request):
        login_file = getattr(request.app.state, "ui_root", Path()) / "login" / "index.html"
        if login_file.is_file():
            return FileResponse(str(login_file), media_type="text/html")
        return {"message": "No login page found at ui/login/index.html."}

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: StarletteHTTPException):
        if request.url.path.startswith("/api/") or (request.url.path.startswith("/exp/") and "/ui/" not in request.url.path):
            return HTMLResponse(
                content='{"detail":"Not found"}',
                status_code=404,
                media_type="application/json",
            )
        page_404 = getattr(request.app.state, "ui_root", Path()) / "404.html"
        if page_404.is_file():
            return FileResponse(str(page_404), status_code=404, media_type="text/html")
        return HTMLResponse("<h1>404 — Not Found</h1>", status_code=404)

    return app


app = create_app()
