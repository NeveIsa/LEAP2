"""Phase 2 CLI tests: init, new, list, validate, config, doctor."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from leap.cli import app, init_project_fn, init_fn, new_experiment_fn, list_experiments_fn
from leap.cli import validate_experiment_fn, show_config_fn, doctor_fn, remove_experiment_fn
from leap.core.experiment import get_experiment_list, add_experiment_entry, remove_experiment_entry

runner = CliRunner()


# ── Shared function tests ──


class TestInitProjectFn:
    def test_creates_directories(self, tmp_path):
        results = init_project_fn(root=tmp_path)
        assert (tmp_path / "experiments").is_dir()
        assert (tmp_path / "config").is_dir()
        assert any("created" == v for v in results.values())

    def test_idempotent(self, tmp_path):
        init_project_fn(root=tmp_path)
        results2 = init_project_fn(root=tmp_path)
        assert all(v == "exists" for v in results2.values())


class TestNewExperimentFn:
    def test_creates_scaffold(self, tmp_root):
        path = new_experiment_fn(interactive=False, name="my-lab", root=tmp_root)
        assert path.is_dir()
        assert (path / "README.md").is_file()
        assert (path / "funcs" / "functions.py").is_file()
        assert (path / "ui" / "dashboard.html").is_file()
        assert (path / "db").is_dir()

    def test_readme_has_frontmatter(self, tmp_root):
        path = new_experiment_fn(interactive=False, name="test-exp", root=tmp_root)
        text = (path / "README.md").read_text()
        assert "---" in text
        assert "name: test-exp" in text
        assert "display_name:" in text

    def test_stub_function_file(self, tmp_root):
        path = new_experiment_fn(interactive=False, name="func-test", root=tmp_root)
        text = (path / "funcs" / "functions.py").read_text()
        assert "def hello" in text

    def test_rejects_invalid_name(self, tmp_root):
        import typer
        with pytest.raises(typer.BadParameter, match="Invalid"):
            new_experiment_fn(interactive=False, name="My Lab!", root=tmp_root)

    def test_rejects_uppercase(self, tmp_root):
        import typer
        with pytest.raises(typer.BadParameter, match="Invalid"):
            new_experiment_fn(interactive=False, name="MyLab", root=tmp_root)

    def test_rejects_duplicate(self, tmp_root):
        import typer
        new_experiment_fn(interactive=False, name="dup-test", root=tmp_root)
        with pytest.raises(typer.BadParameter, match="already exists"):
            new_experiment_fn(interactive=False, name="dup-test", root=tmp_root)

    def test_name_with_hyphens_underscores(self, tmp_root):
        path = new_experiment_fn(interactive=False, name="my-cool_lab2", root=tmp_root)
        assert path.is_dir()
        assert "my-cool_lab2" in path.name

    def test_readme_has_repository_field(self, tmp_root):
        path = new_experiment_fn(interactive=False, name="repo-test", root=tmp_root)
        text = (path / "README.md").read_text()
        assert "repository:" in text

    def test_dashboard_references_experiment(self, tmp_root):
        path = new_experiment_fn(interactive=False, name="viz-lab", root=tmp_root)
        html = (path / "ui" / "dashboard.html").read_text()
        assert "Viz Lab" in html


class TestListExperimentsFn:
    def test_lists_default(self, tmp_root):
        exps = list_experiments_fn(root=tmp_root)
        assert len(exps) >= 1
        names = [e["name"] for e in exps]
        assert "default" in names

    def test_experiment_metadata_shape(self, tmp_root):
        exps = list_experiments_fn(root=tmp_root)
        exp = exps[0]
        assert "name" in exp
        assert "display_name" in exp
        assert "functions" in exp
        assert "require_registration" in exp

    def test_includes_new_experiment(self, tmp_root):
        new_experiment_fn(interactive=False, name="extra-lab", root=tmp_root)
        exps = list_experiments_fn(root=tmp_root)
        names = [e["name"] for e in exps]
        assert "extra-lab" in names

    def test_empty_experiments(self, tmp_path):
        (tmp_path / "experiments").mkdir(parents=True)
        exps = list_experiments_fn(root=tmp_path)
        assert exps == []


class TestValidateExperimentFn:
    def test_valid_experiment_all_ok(self, tmp_root):
        results = validate_experiment_fn("default", root=tmp_root)
        statuses = [r["status"] for r in results]
        assert "error" not in statuses

    def test_invalid_name(self, tmp_root):
        results = validate_experiment_fn("Bad Name!", root=tmp_root)
        assert results[0]["status"] == "error"

    def test_nonexistent_experiment(self, tmp_root):
        results = validate_experiment_fn("nope", root=tmp_root)
        assert any(r["status"] == "error" for r in results)

    def test_missing_entry_point(self, tmp_root):
        exp_path = tmp_root / "experiments" / "no-ui"
        exp_path.mkdir(parents=True)
        (exp_path / "funcs").mkdir()
        (exp_path / "ui").mkdir()
        (exp_path / "README.md").write_text(
            "---\nname: no-ui\nentry_point: missing.html\n---\n"
        )
        results = validate_experiment_fn("no-ui", root=tmp_root)
        entry_check = [r for r in results if r["check"] == "entry_point"]
        assert entry_check[0]["status"] == "warning"

    def test_checks_readme_and_funcs(self, tmp_root):
        results = validate_experiment_fn("default", root=tmp_root)
        checks = [r["check"] for r in results]
        assert "readme" in checks
        assert "funcs" in checks

    def test_leap_version_check_passes(self, tmp_root):
        # Default experiment has leap_version: ">=1.0" which should pass
        (tmp_root / "experiments" / "default" / "README.md").write_text(
            "---\nname: default\nleap_version: '>=1.0'\n---\n"
        )
        results = validate_experiment_fn("default", root=tmp_root)
        ver_check = [r for r in results if r["check"] == "leap_version"]
        assert len(ver_check) == 1
        assert ver_check[0]["status"] == "ok"

    def test_leap_version_check_fails(self, tmp_root):
        (tmp_root / "experiments" / "default" / "README.md").write_text(
            "---\nname: default\nleap_version: '>=99.0'\n---\n"
        )
        results = validate_experiment_fn("default", root=tmp_root)
        ver_check = [r for r in results if r["check"] == "leap_version"]
        assert len(ver_check) == 1
        assert ver_check[0]["status"] == "error"


class TestShowConfigFn:
    def test_returns_dict(self, tmp_root):
        cfg = show_config_fn(root=tmp_root)
        assert isinstance(cfg, dict)
        assert "root" in cfg
        assert "experiments_dir" in cfg
        assert "experiment_count" in cfg

    def test_root_matches(self, tmp_root):
        cfg = show_config_fn(root=tmp_root)
        assert cfg["root"] == str(tmp_root)

    def test_experiment_count(self, tmp_root):
        cfg = show_config_fn(root=tmp_root)
        assert cfg["experiment_count"] >= 1

    def test_credentials_status(self, tmp_root):
        cfg = show_config_fn(root=tmp_root)
        assert "credentials_exist" in cfg


class TestDoctorFn:
    def test_all_ok_for_valid_setup(self, tmp_credentials):
        results = doctor_fn(root=tmp_credentials)
        assert all("hint" in r for r in results)
        statuses = [r["status"] for r in results]
        assert "error" not in statuses

    def test_checks_python_version(self, tmp_root):
        results = doctor_fn(root=tmp_root)
        assert all("hint" in r for r in results)
        python_check = [r for r in results if r["check"] == "python"]
        assert python_check[0]["status"] == "ok"

    def test_checks_packages(self, tmp_root):
        results = doctor_fn(root=tmp_root)
        assert all("hint" in r for r in results)
        pkg_checks = [r for r in results if r["check"].startswith("package:")]
        assert len(pkg_checks) >= 5
        assert all(r["status"] == "ok" for r in pkg_checks)

    def test_warns_on_missing_credentials(self, tmp_root):
        results = doctor_fn(root=tmp_root)
        assert all("hint" in r for r in results)
        cred_check = [r for r in results if r["check"] == "credentials"]
        assert cred_check[0]["status"] == "warning"
        assert "set-password" in cred_check[0]["hint"]

    def test_credentials_ok_when_admin_password_env_set(self, tmp_root, monkeypatch):
        monkeypatch.setenv("ADMIN_PASSWORD", "test-secret-for-doctor")
        results = doctor_fn(root=tmp_root)
        cred_check = [r for r in results if r["check"] == "credentials"]
        assert cred_check[0]["status"] == "ok"
        assert "ADMIN_PASSWORD" in cred_check[0]["message"]

    def test_warns_on_missing_experiments(self, tmp_path):
        (tmp_path / "experiments").mkdir(parents=True)
        results = doctor_fn(root=tmp_path)
        assert all("hint" in r for r in results)
        exp_check = [r for r in results if r["check"] == "experiments"]
        assert exp_check[0]["status"] == "warning"

    def test_root_readme_warns_for_unknown_type(self, tmp_path):
        (tmp_path / "experiments").mkdir()
        (tmp_path / "config").mkdir()
        (tmp_path / "README.md").write_text(
            "---\n"
            "name: my-course\n"
            "type: workspace\n"
            "display_name: My Course\n"
            "---\n\n"
            "# Course\n",
            encoding="utf-8",
        )
        results = doctor_fn(root=tmp_path)
        rr = [r for r in results if r["check"] == "root_readme"][0]
        assert rr["status"] == "warning"
        assert "Unknown type" in rr["message"]


class TestInitCommand:
    def test_init_creates_lab_no_readme(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = init_fn(skip_password=True, interactive=False)
        assert (tmp_path / "experiments").is_dir()
        assert (tmp_path / "config").is_dir()
        assert "type: lab" in (tmp_path / "README.md").read_text()
        assert result.get("password") == "skipped"

    def test_init_idempotent_on_existing_lab(self, tmp_path, monkeypatch):
        """init on an existing lab should succeed, not reject."""
        (tmp_path / "README.md").write_text(
            "---\nname: x\ntype: lab\nexperiments: []\n---\n",
            encoding="utf-8",
        )
        (tmp_path / "experiments").mkdir()
        monkeypatch.chdir(tmp_path)
        result = init_fn(skip_password=True)
        assert result["readme"] == "skipped"
        assert result["password"] == "skipped"

    def test_init_aborts_inside_experiments(self, tmp_path, monkeypatch):
        exp = tmp_path / "experiments" / "my-exp"
        exp.mkdir(parents=True)
        monkeypatch.chdir(exp)
        with pytest.raises(typer.BadParameter) as exc_info:
            init_fn(skip_password=True)
        assert "project root" in str(exc_info.value).lower()

    def test_cli_init(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["init", "--skip-password"])
        assert result.exit_code == 0
        assert "type: lab" in (tmp_path / "README.md").read_text()


# ── CLI command tests (via CliRunner) ──


class TestNewCommand:
    def test_new_experiment(self, tmp_root):
        result = runner.invoke(app, ["add", "my-test", "--root", str(tmp_root), "--no-prompt"])
        assert result.exit_code == 0
        assert "Created" in result.output or "created" in result.output.lower()
        assert (tmp_root / "experiments" / "my-test").is_dir()

    def test_new_invalid_name(self, tmp_root):
        result = runner.invoke(app, ["add", "BAD NAME", "--root", str(tmp_root), "--no-prompt"])
        assert result.exit_code == 1

    def test_new_duplicate(self, tmp_root):
        runner.invoke(app, ["add", "dup-exp", "--root", str(tmp_root), "--no-prompt"])
        result = runner.invoke(app, ["add", "dup-exp", "--root", str(tmp_root), "--no-prompt"])
        assert result.exit_code == 1

    def test_new_shows_next_steps(self, tmp_root):
        result = runner.invoke(app, ["add", "steps-test", "--root", str(tmp_root), "--no-prompt"])
        assert "Next steps" in result.output


class TestListCommand:
    def test_list_experiments(self, tmp_root):
        result = runner.invoke(app, ["list", "--root", str(tmp_root)])
        assert result.exit_code == 0
        assert "default" in result.output

    def test_list_empty(self, tmp_path):
        (tmp_path / "experiments").mkdir(parents=True)
        result = runner.invoke(app, ["list", "--root", str(tmp_path)])
        assert result.exit_code == 0
        assert "No experiments" in result.output

    def test_list_shows_multiple(self, tmp_root):
        new_experiment_fn(interactive=False, name="another-one", root=tmp_root)
        result = runner.invoke(app, ["list", "--root", str(tmp_root)])
        assert "default" in result.output
        assert "another-one" in result.output


class TestValidateCommand:
    def test_validate_default(self, tmp_root):
        result = runner.invoke(app, ["validate", "default", "--root", str(tmp_root)])
        assert result.exit_code == 0
        assert "passed" in result.output.lower()

    def test_validate_nonexistent(self, tmp_root):
        result = runner.invoke(app, ["validate", "nope", "--root", str(tmp_root)])
        assert result.exit_code == 1

    def test_validate_shows_checks(self, tmp_root):
        result = runner.invoke(app, ["validate", "default", "--root", str(tmp_root)])
        assert "name" in result.output.lower()
        assert "readme" in result.output.lower()


class TestConfigCommand:
    def test_config_output(self, tmp_root):
        result = runner.invoke(app, ["config", "--root", str(tmp_root)])
        assert result.exit_code == 0
        assert "Root:" in result.output
        assert str(tmp_root) in result.output

    def test_config_shows_experiment_count(self, tmp_root):
        result = runner.invoke(app, ["config", "--root", str(tmp_root)])
        assert "found" in result.output.lower()


class TestDoctorCommand:
    def test_doctor_passes(self, tmp_credentials):
        result = runner.invoke(app, ["doctor", "--root", str(tmp_credentials)])
        assert result.exit_code == 0
        assert "passed" in result.output.lower() or "ok" in result.output.lower()

    def test_doctor_warns_without_credentials(self, tmp_root):
        result = runner.invoke(app, ["doctor", "--root", str(tmp_root)])
        assert result.exit_code == 0
        assert "missing" in result.output.lower() or "warning" in result.output.lower()

    def test_doctor_checks_python(self, tmp_root):
        result = runner.invoke(app, ["doctor", "--root", str(tmp_root)])
        assert "python" in result.output.lower()


class TestImportStudentsCommand:
    def _write_csv(self, tmp_path, filename, content):
        p = tmp_path / filename
        p.write_text(content, encoding="utf-8")
        return p

    def test_import_basic(self, tmp_root):
        csv_path = self._write_csv(
            tmp_root, "students.csv",
            "student_id,name,email\ns001,Alice,alice@u.edu\ns002,Bob,\ns003,Charlie,charlie@u.edu\n",
        )
        result = runner.invoke(app, ["import-students", "default", str(csv_path), "--root", str(tmp_root)])
        assert result.exit_code == 0
        assert "Added: 3" in result.output

    def test_import_skips_duplicates(self, tmp_root):
        # Pre-add one student
        runner.invoke(app, ["add-student", "default", "s001", "--root", str(tmp_root)])
        csv_path = self._write_csv(
            tmp_root, "students.csv",
            "student_id,name\ns001,Alice\ns002,Bob\n",
        )
        result = runner.invoke(app, ["import-students", "default", str(csv_path), "--root", str(tmp_root)])
        assert result.exit_code == 0
        assert "Added: 1" in result.output
        assert "Skipped: 1" in result.output

    def test_import_missing_header(self, tmp_root):
        csv_path = self._write_csv(
            tmp_root, "bad.csv",
            "id,name\ns001,Alice\n",
        )
        result = runner.invoke(app, ["import-students", "default", str(csv_path), "--root", str(tmp_root)])
        assert result.exit_code == 1
        assert "student_id" in result.output

    def test_import_email_optional(self, tmp_root):
        csv_path = self._write_csv(
            tmp_root, "students.csv",
            "student_id,name\ns001,Alice\ns002,Bob\n",
        )
        result = runner.invoke(app, ["import-students", "default", str(csv_path), "--root", str(tmp_root)])
        assert result.exit_code == 0
        assert "Added: 2" in result.output


# ── Experiment list tracking helpers ──


def _make_lab_readme(root: Path, experiments=None):
    """Create a minimal lab README with optional experiments list."""
    exp_yaml = "experiments: []\n"
    if experiments:
        entry_lines = []
        for e in experiments:
            entry_lines.append(f"  - name: {e['name']}")
            if e.get("source"):
                entry_lines.append(f"    source: {e['source']}")
        exp_yaml = "experiments:\n" + "\n".join(entry_lines) + "\n"
    (root / "README.md").write_text(
        f"---\nname: test-lab\ntype: lab\n{exp_yaml}---\n\n# Test Lab\n",
        encoding="utf-8",
    )


class TestExperimentListHelpers:
    def test_get_empty(self, tmp_path):
        _make_lab_readme(tmp_path)
        assert get_experiment_list(tmp_path / "README.md") == []

    def test_add_entry(self, tmp_path):
        _make_lab_readme(tmp_path)
        readme = tmp_path / "README.md"
        assert add_experiment_entry(readme, "quiz") is True
        entries = get_experiment_list(readme)
        assert len(entries) == 1
        assert entries[0] == {"name": "quiz"}

    def test_add_idempotent(self, tmp_path):
        _make_lab_readme(tmp_path)
        readme = tmp_path / "README.md"
        add_experiment_entry(readme, "quiz")
        assert add_experiment_entry(readme, "quiz") is False

    def test_add_updates_source(self, tmp_path):
        _make_lab_readme(tmp_path)
        readme = tmp_path / "README.md"
        add_experiment_entry(readme, "quiz")
        add_experiment_entry(readme, "quiz", "https://github.com/user/quiz.git")
        entries = get_experiment_list(readme)
        assert entries[0]["source"] == "https://github.com/user/quiz.git"

    def test_remove_entry(self, tmp_path):
        _make_lab_readme(tmp_path, [{"name": "quiz"}])
        readme = tmp_path / "README.md"
        assert remove_experiment_entry(readme, "quiz") is True
        assert get_experiment_list(readme) == []

    def test_remove_nonexistent(self, tmp_path):
        _make_lab_readme(tmp_path)
        assert remove_experiment_entry(tmp_path / "README.md", "nope") is False

    def test_multiple_entries(self, tmp_path):
        _make_lab_readme(tmp_path)
        readme = tmp_path / "README.md"
        add_experiment_entry(readme, "alpha")
        add_experiment_entry(readme, "beta", "https://github.com/user/beta.git")
        entries = get_experiment_list(readme)
        assert len(entries) == 2
        names = [e["name"] for e in entries]
        assert "alpha" in names
        assert "beta" in names


class TestNewExperimentTracking:
    def test_new_adds_to_readme(self, tmp_root):
        _make_lab_readme(tmp_root)
        new_experiment_fn(interactive=False, name="tracked", root=tmp_root)
        entries = get_experiment_list(tmp_root / "README.md")
        assert any(e["name"] == "tracked" for e in entries)

    def test_new_without_readme_no_error(self, tmp_path):
        # No root README — should not crash
        (tmp_path / "experiments").mkdir()
        assert not (tmp_path / "README.md").exists()
        new_experiment_fn(interactive=False, name="no-readme", root=tmp_path)
        assert (tmp_path / "experiments" / "no-readme").is_dir()


class TestInitSyncsExperiments:
    def test_init_populates_experiment_list(self, tmp_path, monkeypatch):
        # Pre-create an experiment directory
        exp = tmp_path / "experiments" / "pre-existing"
        exp.mkdir(parents=True)
        (exp / "README.md").write_text("---\nname: pre-existing\ntype: experiment\n---\n")
        monkeypatch.chdir(tmp_path)
        init_fn(skip_password=True)
        entries = get_experiment_list(tmp_path / "README.md")
        assert any(e["name"] == "pre-existing" for e in entries)


class TestInitInstallsDeps:
    def test_installs_requirements(self, tmp_path, monkeypatch):
        """init should pip install requirements.txt for each experiment."""
        (tmp_path / "README.md").write_text(
            "---\nname: test\ntype: lab\nexperiments: []\n---\n",
            encoding="utf-8",
        )
        exp = tmp_path / "experiments" / "dep-exp"
        exp.mkdir(parents=True)
        (exp / "README.md").write_text("---\nname: dep-exp\ntype: experiment\n---\n")
        (exp / "requirements.txt").write_text("numpy>=1.20\n")
        monkeypatch.chdir(tmp_path)
        with patch("leap.cli.subprocess.run") as mock_run, \
             patch("leap.cli._get_git_remote", return_value=""):
            mock_run.return_value = MagicMock(returncode=0)
            result = init_fn(skip_password=True)
        assert "dep-exp" in result.get("deps_installed", "")
        pip_calls = [c for c in mock_run.call_args_list if "pip" in str(c)]
        assert len(pip_calls) >= 1

    def test_no_requirements_no_install(self, tmp_path, monkeypatch):
        """init should not call pip if no requirements.txt exists."""
        (tmp_path / "README.md").write_text(
            "---\nname: test\ntype: lab\nexperiments: []\n---\n",
            encoding="utf-8",
        )
        exp = tmp_path / "experiments" / "no-deps"
        exp.mkdir(parents=True)
        (exp / "README.md").write_text("---\nname: no-deps\ntype: experiment\n---\n")
        monkeypatch.chdir(tmp_path)
        with patch("leap.cli.subprocess.run") as mock_run, \
             patch("leap.cli._get_git_remote", return_value=""):
            mock_run.return_value = MagicMock(returncode=0)
            result = init_fn(skip_password=True)
        assert "deps_installed" not in result
        assert mock_run.call_count == 0


class TestInitReinstallsMissing:
    def test_reinstalls_missing_remote(self, tmp_path, monkeypatch):
        """init should offer to reinstall remote experiments missing from disk."""
        (tmp_path / "experiments").mkdir(parents=True)
        _make_lab_readme(tmp_path, [
            {"name": "remote-exp", "source": "https://github.com/user/remote-exp.git"},
        ])
        monkeypatch.chdir(tmp_path)
        with patch("leap.cli.subprocess.run") as mock_run, \
             patch("leap.cli._get_git_remote", return_value=""), \
             patch("leap.cli.typer.confirm", return_value=True):
            mock_run.return_value = MagicMock(returncode=0)
            result = init_fn(skip_password=True)
        assert "remote-exp" in result.get("experiments_reinstalled", "")

    def test_skips_local_missing(self, tmp_path, monkeypatch):
        """init should not try to reinstall local experiments."""
        (tmp_path / "experiments").mkdir(parents=True)
        _make_lab_readme(tmp_path, [
            {"name": "local-gone"},
        ])
        monkeypatch.chdir(tmp_path)
        with patch("leap.cli.subprocess.run") as mock_run, \
             patch("leap.cli._get_git_remote", return_value=""):
            mock_run.return_value = MagicMock(returncode=0)
            result = init_fn(skip_password=True)
        assert "experiments_reinstalled" not in result


class TestDoctorExperimentsList:
    def test_warns_unlisted_on_disk(self, tmp_root):
        _make_lab_readme(tmp_root)  # no experiments listed, but 'default' exists on disk
        results = doctor_fn(root=tmp_root)
        exp_list_checks = [r for r in results if r["check"] == "experiments_list"]
        assert any("default" in r["message"] for r in exp_list_checks)
        assert any(r["status"] == "warning" for r in exp_list_checks)

    def test_warns_missing_remote_dir(self, tmp_root):
        _make_lab_readme(tmp_root, [
            {"name": "default"},
            {"name": "ghost", "source": "https://github.com/user/ghost.git"},
        ])
        results = doctor_fn(root=tmp_root)
        exp_list_checks = [r for r in results if r["check"] == "experiments_list"]
        assert any("ghost" in r["message"] and "reinstall" in r["message"] for r in exp_list_checks)

    def test_warns_missing_local_dir(self, tmp_root):
        _make_lab_readme(tmp_root, [
            {"name": "default"},
            {"name": "gone"},
        ])
        results = doctor_fn(root=tmp_root)
        exp_list_checks = [r for r in results if r["check"] == "experiments_list"]
        assert any("gone" in r["message"] for r in exp_list_checks)

    def test_ok_when_synced(self, tmp_root):
        _make_lab_readme(tmp_root, [{"name": "default"}])
        results = doctor_fn(root=tmp_root)
        exp_list_checks = [r for r in results if r["check"] == "experiments_list"]
        assert any(r["status"] == "ok" for r in exp_list_checks)


class TestRemoveExperimentFn:
    def test_removes_directory(self, tmp_root):
        new_experiment_fn(interactive=False, name="to-remove", root=tmp_root)
        assert (tmp_root / "experiments" / "to-remove").is_dir()
        remove_experiment_fn("to-remove", root=tmp_root)
        assert not (tmp_root / "experiments" / "to-remove").exists()

    def test_removes_readme_entry(self, tmp_root):
        _make_lab_readme(tmp_root)
        new_experiment_fn(interactive=False, name="tracked-rm", root=tmp_root)
        entries = get_experiment_list(tmp_root / "README.md")
        assert any(e["name"] == "tracked-rm" for e in entries)
        remove_experiment_fn("tracked-rm", root=tmp_root)
        entries = get_experiment_list(tmp_root / "README.md")
        assert not any(e["name"] == "tracked-rm" for e in entries)

    def test_rejects_nonexistent(self, tmp_root):
        with pytest.raises(typer.BadParameter, match="not found"):
            remove_experiment_fn("nope", root=tmp_root)

    def test_rejects_invalid_name(self, tmp_root):
        with pytest.raises(typer.BadParameter):
            remove_experiment_fn("BAD NAME!", root=tmp_root)


class TestRemoveCommand:
    def test_remove_with_yes_flag(self, tmp_root):
        new_experiment_fn(interactive=False, name="cli-rm", root=tmp_root)
        result = runner.invoke(app, ["remove", "cli-rm", "--yes", "--root", str(tmp_root)])
        assert result.exit_code == 0
        assert "Removed" in result.output
        assert not (tmp_root / "experiments" / "cli-rm").exists()

    def test_remove_nonexistent(self, tmp_root):
        result = runner.invoke(app, ["remove", "nope", "--yes", "--root", str(tmp_root)])
        assert result.exit_code == 1

    def test_remove_prompts_by_default(self, tmp_root):
        new_experiment_fn(interactive=False, name="prompt-rm", root=tmp_root)
        result = runner.invoke(app, ["remove", "prompt-rm", "--root", str(tmp_root)], input="y\n")
        assert result.exit_code == 0
        assert not (tmp_root / "experiments" / "prompt-rm").exists()
