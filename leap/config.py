"""Project root resolution and configuration constants."""

from __future__ import annotations

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, _LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def get_root() -> Path:
    """Resolve project root: LEAP_ROOT env > cwd > parent of leap package."""
    if env := os.environ.get("LEAP_ROOT"):
        return Path(env).resolve()
    cwd = Path.cwd()
    if (cwd / "experiments").is_dir() or (cwd / "pyproject.toml").is_file():
        return cwd
    pkg_parent = Path(__file__).resolve().parent.parent
    if (pkg_parent / "experiments").is_dir():
        return pkg_parent
    return cwd


def experiments_dir(root: Path | None = None) -> Path:
    return (root or get_root()) / "experiments"


def config_dir(root: Path | None = None) -> Path:
    return (root or get_root()) / "config"


def credentials_path(root: Path | None = None) -> Path:
    return config_dir(root) / "admin_credentials.json"


def ui_dir(root: Path | None = None) -> Path:
    return (root or get_root()) / "ui"


SESSION_SECRET_KEY = os.environ.get("SESSION_SECRET_KEY", "")
DEFAULT_EXPERIMENT = os.environ.get("DEFAULT_EXPERIMENT", "")
ADMIN_PASSWORD_ENV = os.environ.get("ADMIN_PASSWORD", "")
