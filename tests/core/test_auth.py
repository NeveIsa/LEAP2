"""Tests for leap.core.auth — password hashing, verification, credential management."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest import mock

import pytest

from leap.core import auth


class TestPasswordHashing:
    def test_hash_and_verify(self):
        cred = auth.hash_password("mysecret")
        assert auth.verify_password("mysecret", cred) is True
        assert auth.verify_password("wrong", cred) is False

    def test_hash_deterministic_with_salt(self):
        salt = b"\x00" * 32
        c1 = auth.hash_password("test", salt=salt)
        c2 = auth.hash_password("test", salt=salt)
        assert c1["password_hash"] == c2["password_hash"]

    def test_hash_different_salts(self):
        c1 = auth.hash_password("test")
        c2 = auth.hash_password("test")
        assert c1["salt"] != c2["salt"]
        assert c1["password_hash"] != c2["password_hash"]

    def test_credential_structure(self):
        cred = auth.hash_password("test")
        assert set(cred.keys()) == {"password_hash", "salt", "iterations", "algorithm"}
        assert cred["algorithm"] == "pbkdf2_sha256"
        assert cred["iterations"] == 240_000

    def test_hash_long_password(self):
        long_pw = "a" * 10000
        cred = auth.hash_password(long_pw)
        assert auth.verify_password(long_pw, cred) is True
        assert auth.verify_password(long_pw + "x", cred) is False

    def test_hash_unicode_password(self):
        pw = "pässwörd™🔑"
        cred = auth.hash_password(pw)
        assert auth.verify_password(pw, cred) is True
        assert auth.verify_password("password", cred) is False

    def test_hash_single_char_password(self):
        cred = auth.hash_password("x")
        assert auth.verify_password("x", cred) is True

    def test_verify_various_wrong_passwords(self):
        cred = auth.hash_password("correct")
        assert auth.verify_password("wrong", cred) is False
        assert auth.verify_password("c", cred) is False
        assert auth.verify_password("correctx", cred) is False
        assert auth.verify_password("Correct", cred) is False
        assert auth.verify_password("", cred) is False

    def test_hash_hex_output(self):
        cred = auth.hash_password("test")
        int(cred["password_hash"], 16)  # should not raise
        int(cred["salt"], 16)


class TestCredentialIO:
    def test_save_and_load(self, tmp_path: Path):
        cred = auth.hash_password("test")
        auth.save_credentials(cred, tmp_path)
        loaded = auth.load_credentials(tmp_path)
        assert loaded == cred

    def test_load_missing(self, tmp_path: Path):
        assert auth.load_credentials(tmp_path) is None

    def test_save_creates_config_dir(self, tmp_path: Path):
        cred = auth.hash_password("test")
        auth.save_credentials(cred, tmp_path)
        assert (tmp_path / "config" / "admin_credentials.json").exists()

    def test_save_overwrites(self, tmp_path: Path):
        cred1 = auth.hash_password("first")
        auth.save_credentials(cred1, tmp_path)

        cred2 = auth.hash_password("second")
        auth.save_credentials(cred2, tmp_path)

        loaded = auth.load_credentials(tmp_path)
        assert auth.verify_password("second", loaded) is True
        assert auth.verify_password("first", loaded) is False

    def test_saved_file_is_valid_json(self, tmp_path: Path):
        cred = auth.hash_password("test")
        auth.save_credentials(cred, tmp_path)
        path = tmp_path / "config" / "admin_credentials.json"
        data = json.loads(path.read_text())
        assert "password_hash" in data


class TestEnsureCredentials:
    def test_existing_credentials_noop(self, tmp_path: Path):
        cred = auth.hash_password("existing")
        auth.save_credentials(cred, tmp_path)
        auth.ensure_credentials(tmp_path)
        loaded = auth.load_credentials(tmp_path)
        assert auth.verify_password("existing", loaded) is True

    def test_env_password_creates_credentials(self, tmp_path: Path):
        with mock.patch.object(auth, "ADMIN_PASSWORD_ENV", "envpass"):
            auth.ensure_credentials(tmp_path)
        loaded = auth.load_credentials(tmp_path)
        assert auth.verify_password("envpass", loaded) is True

    def test_no_credentials_no_env_no_tty_fails(self, tmp_path: Path):
        with mock.patch.object(auth, "ADMIN_PASSWORD_ENV", ""):
            with mock.patch("os.isatty", return_value=False):
                with pytest.raises(SystemExit, match="set-password"):
                    auth.ensure_credentials(tmp_path)

    def test_env_mismatch_warns(self, tmp_path: Path, caplog):
        cred = auth.hash_password("original")
        auth.save_credentials(cred, tmp_path)
        with mock.patch.object(auth, "ADMIN_PASSWORD_ENV", "different"):
            import logging
            with caplog.at_level(logging.WARNING):
                auth.ensure_credentials(tmp_path)
            assert "does not match" in caplog.text
