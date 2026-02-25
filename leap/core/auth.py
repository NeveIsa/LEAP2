"""Admin authentication: PBKDF2 password hashing and verification."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
from pathlib import Path

from leap.config import credentials_path, config_dir, ADMIN_PASSWORD_ENV

logger = logging.getLogger(__name__)

ITERATIONS = 240_000
ALGORITHM = "pbkdf2_sha256"


def hash_password(password: str, salt: bytes | None = None) -> dict:
    if salt is None:
        salt = secrets.token_bytes(32)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return {
        "password_hash": dk.hex(),
        "salt": salt.hex(),
        "iterations": ITERATIONS,
        "algorithm": ALGORITHM,
    }


def verify_password(password: str, cred: dict) -> bool:
    salt = bytes.fromhex(cred["salt"])
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, cred.get("iterations", ITERATIONS)
    )
    return secrets.compare_digest(dk.hex(), cred["password_hash"])


def load_credentials(root: Path | None = None) -> dict | None:
    path = credentials_path(root)
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def save_credentials(cred: dict, root: Path | None = None) -> None:
    path = credentials_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(cred, f, indent=2)
    logger.info("Credentials saved to %s", path)


def ensure_credentials(root: Path | None = None) -> None:
    """Ensure admin credentials exist. Create from env or prompt if missing."""
    cred = load_credentials(root)
    if cred:
        if ADMIN_PASSWORD_ENV:
            if not verify_password(ADMIN_PASSWORD_ENV, cred):
                logger.warning("ADMIN_PASSWORD env does not match stored credentials")
        return

    if ADMIN_PASSWORD_ENV:
        cred = hash_password(ADMIN_PASSWORD_ENV)
        save_credentials(cred, root)
        logger.info("Created admin credentials from ADMIN_PASSWORD env")
        return

    if os.isatty(0):
        import getpass
        pw = getpass.getpass("Set admin password: ")
        if not pw:
            raise SystemExit("Password cannot be empty")
        pw2 = getpass.getpass("Confirm admin password: ")
        if pw != pw2:
            raise SystemExit("Passwords do not match")
        cred = hash_password(pw)
        save_credentials(cred, root)
        logger.info("Created admin credentials interactively")
        return

    raise SystemExit(
        "No admin credentials found. Run 'leap set-password' or set ADMIN_PASSWORD env."
    )
