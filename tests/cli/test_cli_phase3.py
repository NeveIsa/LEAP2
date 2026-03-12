"""Phase 3 CLI tests: leap install command."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from leap.cli import app, install_experiment_fn

runner = CliRunner()


class TestInstallExperimentFn:
    def test_derives_name_from_url(self, tmp_root):
        with patch("leap.cli.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            name, path = install_experiment_fn(
                "https://github.com/user/my-experiment.git",
                root=tmp_root,
            )
        assert name == "my-experiment"
        assert "experiments/my-experiment" in str(path)

    def test_derives_name_strips_git_suffix(self, tmp_root):
        with patch("leap.cli.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            name, _ = install_experiment_fn(
                "https://github.com/user/cool-lab.git",
                root=tmp_root,
            )
        assert name == "cool-lab"

    def test_derives_name_without_git_suffix(self, tmp_root):
        with patch("leap.cli.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            name, _ = install_experiment_fn(
                "https://github.com/user/my-lab",
                root=tmp_root,
            )
        assert name == "my-lab"

    def test_name_override(self, tmp_root):
        with patch("leap.cli.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            name, path = install_experiment_fn(
                "https://github.com/user/whatever.git",
                name="custom-name",
                root=tmp_root,
            )
        assert name == "custom-name"
        assert "experiments/custom-name" in str(path)

    def test_rejects_invalid_derived_name(self, tmp_root):
        import typer
        with pytest.raises(typer.BadParameter, match="invalid"):
            install_experiment_fn(
                "https://github.com/user/My_Bad_Name!.git",
                root=tmp_root,
            )

    def test_rejects_duplicate_experiment(self, tmp_root):
        import typer
        with pytest.raises(typer.BadParameter, match="already exists"):
            install_experiment_fn(
                "https://github.com/user/default.git",
                root=tmp_root,
            )

    def test_git_not_found(self, tmp_root):
        import typer
        with patch("leap.cli.subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(typer.BadParameter, match="git is not installed"):
                install_experiment_fn(
                    "https://github.com/user/new-lab.git",
                    root=tmp_root,
                )

    def test_git_clone_failure(self, tmp_root):
        import typer
        err = subprocess.CalledProcessError(128, "git", stderr="fatal: repo not found")
        with patch("leap.cli.subprocess.run", side_effect=err):
            with pytest.raises(typer.BadParameter, match="git clone failed"):
                install_experiment_fn(
                    "https://github.com/user/new-lab.git",
                    root=tmp_root,
                )

    def test_creates_experiments_dir_if_missing(self, tmp_path):
        """If experiments/ doesn't exist yet, install should create it."""
        import typer
        with patch("leap.cli.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            name, path = install_experiment_fn(
                "https://github.com/user/fresh-lab.git",
                root=tmp_path,
            )
        assert (tmp_path / "experiments").is_dir()

    def test_calls_git_with_correct_args(self, tmp_root):
        with patch("leap.cli.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            install_experiment_fn(
                "https://github.com/user/test-lab.git",
                root=tmp_root,
            )
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert cmd[0] == "git"
        assert cmd[1] == "clone"
        assert cmd[2] == "https://github.com/user/test-lab.git"
        assert "test-lab" in cmd[3]

    def test_lowercases_name(self, tmp_root):
        with patch("leap.cli.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            name, _ = install_experiment_fn(
                "https://github.com/user/MyRepo.git",
                root=tmp_root,
            )
        assert name == "myrepo"

    def test_trailing_slash_in_url(self, tmp_root):
        with patch("leap.cli.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            name, _ = install_experiment_fn(
                "https://github.com/user/trail-lab/",
                root=tmp_root,
            )
        assert name == "trail-lab"


    def test_pip_install_when_requirements_exist(self, tmp_root):
        with patch("leap.cli.subprocess.run") as mock_run:
            def side_effect(cmd, **kwargs):
                if cmd[0] == "git":
                    dest = Path(cmd[3])
                    dest.mkdir(parents=True, exist_ok=True)
                    (dest / "requirements.txt").write_text("numpy>=1.20\nscipy\n")
                return MagicMock(returncode=0)

            mock_run.side_effect = side_effect
            install_experiment_fn(
                "https://github.com/user/dep-lab.git",
                root=tmp_root,
            )
        assert mock_run.call_count == 2
        pip_call = mock_run.call_args_list[1]
        pip_cmd = pip_call[0][0]
        assert pip_cmd[1:4] == ["-m", "pip", "install"]
        assert pip_cmd[4] == "-r"
        assert "requirements.txt" in pip_cmd[5]

    def test_no_pip_install_without_requirements(self, tmp_root):
        with patch("leap.cli.subprocess.run") as mock_run:
            def side_effect(cmd, **kwargs):
                if cmd[0] == "git":
                    dest = Path(cmd[3])
                    dest.mkdir(parents=True, exist_ok=True)
                return MagicMock(returncode=0)

            mock_run.side_effect = side_effect
            install_experiment_fn(
                "https://github.com/user/no-deps.git",
                root=tmp_root,
            )
        mock_run.assert_called_once()

    def test_pip_install_failure_does_not_abort(self, tmp_root):
        call_count = 0

        def side_effect(cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            if cmd[0] == "git":
                dest = Path(cmd[3])
                dest.mkdir(parents=True, exist_ok=True)
                (dest / "requirements.txt").write_text("nonexistent-pkg-xyz\n")
                return MagicMock(returncode=0)
            raise subprocess.CalledProcessError(1, "pip", stderr="No matching distribution")

        with patch("leap.cli.subprocess.run", side_effect=side_effect):
            name, path = install_experiment_fn(
                "https://github.com/user/bad-deps.git",
                root=tmp_root,
            )
        assert name == "bad-deps"
        assert path.is_dir()
        assert call_count == 2


class TestInstallCommand:
    def test_install_success(self, tmp_root):
        with patch("leap.cli.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            # Pre-create the directory since mock won't actually clone
            exp_path = tmp_root / "experiments" / "test-repo"
            # Need to handle that install_fn creates nothing (mocked git)
            # but validate_experiment_fn will run — create minimal structure
            def side_effect(cmd, **kwargs):
                dest = Path(cmd[3])
                dest.mkdir(parents=True, exist_ok=True)
                (dest / "README.md").write_text("---\nname: test-repo\n---\n")
                (dest / "funcs").mkdir()
                (dest / "ui").mkdir()
                return MagicMock(returncode=0)

            mock_run.side_effect = side_effect
            result = runner.invoke(app, [
                "install", "https://github.com/user/test-repo.git",
                "--root", str(tmp_root),
            ])
        assert result.exit_code == 0
        assert "Installed" in result.output or "installed" in result.output.lower()

    def test_install_with_name_override(self, tmp_root):
        with patch("leap.cli.subprocess.run") as mock_run:
            def side_effect(cmd, **kwargs):
                dest = Path(cmd[3])
                dest.mkdir(parents=True, exist_ok=True)
                (dest / "README.md").write_text("---\nname: custom\n---\n")
                (dest / "funcs").mkdir()
                (dest / "ui").mkdir()
                return MagicMock(returncode=0)

            mock_run.side_effect = side_effect
            result = runner.invoke(app, [
                "install", "https://github.com/user/whatever.git",
                "--name", "custom",
                "--root", str(tmp_root),
            ])
        assert result.exit_code == 0
        assert "custom" in result.output

    def test_install_duplicate(self, tmp_root):
        result = runner.invoke(app, [
            "install", "https://github.com/user/default.git",
            "--root", str(tmp_root),
        ])
        assert result.exit_code == 1

    def test_install_shows_validation(self, tmp_root):
        with patch("leap.cli.subprocess.run") as mock_run:
            def side_effect(cmd, **kwargs):
                dest = Path(cmd[3])
                dest.mkdir(parents=True, exist_ok=True)
                (dest / "README.md").write_text("---\nname: validated\n---\n")
                (dest / "funcs").mkdir()
                (dest / "ui").mkdir()
                return MagicMock(returncode=0)

            mock_run.side_effect = side_effect
            result = runner.invoke(app, [
                "install", "https://github.com/user/validated.git",
                "--root", str(tmp_root),
            ])
        assert "name" in result.output.lower()
        assert "Restart" in result.output
