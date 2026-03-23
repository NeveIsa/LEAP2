"""Shared test fixtures."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

# Disable rate limiting during tests
os.environ.setdefault("LEAP_RATE_LIMIT", "0")


@pytest.fixture
def tmp_root(tmp_path: Path) -> Path:
    """Create a temporary LEAP2 project root with a default experiment."""
    exp_dir = tmp_path / "experiments" / "default"
    funcs_dir = exp_dir / "funcs"
    funcs_dir.mkdir(parents=True)
    (exp_dir / "db").mkdir()
    (exp_dir / "ui").mkdir()

    (exp_dir / "README.md").write_text(
        "---\n"
        "name: default\n"
        "type: experiment\n"
        "display_name: Test Lab\n"
        "description: Test experiment\n"
        "entry_point: readme\n"
        "require_registration: true\n"
        "---\n\n# Test\n"
    )

    (funcs_dir / "math_funcs.py").write_text(
        "def square(x):\n"
        '    """Return x squared."""\n'
        "    return x * x\n\n"
        "def add(a, b):\n"
        '    """Return a + b."""\n'
        "    return a + b\n\n"
        "def cubic(x):\n"
        '    """Return x cubed."""\n'
        "    return x * x * x\n"
    )

    (funcs_dir / "open_funcs.py").write_text(
        "from leap import noregcheck\n\n"
        "@noregcheck\n"
        "def echo(x):\n"
        '    """Return input unchanged. No registration needed."""\n'
        "    return x\n\n"
        "@noregcheck\n"
        "def ping():\n"
        '    """Health check. No registration needed."""\n'
        "    return 'pong'\n"
    )

    (funcs_dir / "simulation.py").write_text(
        "from leap import nolog\n\n"
        "@nolog\n"
        "def fast_step(dx):\n"
        '    """High-frequency call — not logged."""\n'
        "    return dx * 2\n\n"
        "def logged_reset():\n"
        '    """Infrequent reset — logged."""\n'
        "    return 'reset'\n"
    )

    (funcs_dir / "admin_funcs.py").write_text(
        "from leap import adminonly\n\n"
        "@adminonly\n"
        "def wipe_data():\n"
        '    """Admin-only function."""\n'
        "    return 'wiped'\n"
    )

    # Landing page (customizable per-lab, so lives in project root)
    ui_landing = tmp_path / "ui" / "landing"
    ui_landing.mkdir(parents=True)
    (ui_landing / "index.html").write_text(
        "<!DOCTYPE html><html><head><title>LEAP2</title></head>"
        "<body><h1>LEAP2</h1><div id=\"experiments\"></div></body></html>\n"
    )

    # Experiment UI placeholder
    (exp_dir / "ui" / "dashboard.html").write_text(
        "<!DOCTYPE html><html><head><title>Default Lab</title></head>"
        "<body><h1>Default Lab</h1></body></html>\n"
    )

    # Root README with lab type
    (tmp_path / "README.md").write_text(
        "---\n"
        "name: test-lab\n"
        "type: lab\n"
        "experiments:\n"
        "  - name: default\n"
        "---\n\n# Test Lab\n"
    )

    config_dir = tmp_path / "config"
    config_dir.mkdir()

    return tmp_path


@pytest.fixture
def tmp_credentials(tmp_root: Path) -> Path:
    """Create test admin credentials (password: 'testpass')."""
    from leap.core.auth import hash_password

    cred = hash_password("testpass")
    cred_path = tmp_root / "config" / "admin_credentials.json"
    cred_path.write_text(json.dumps(cred))
    return tmp_root
