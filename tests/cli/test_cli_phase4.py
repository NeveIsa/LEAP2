"""Phase 4 CLI tests: leap export command."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from leap.cli import app, export_logs_fn
from leap.core import storage
from leap.core.experiment import ExperimentInfo


runner = CliRunner()


def _seed_logs(tmp_root: Path, count: int = 5):
    """Add a student and some logs to the default experiment."""
    exp_path = tmp_root / "experiments" / "default"
    exp_info = ExperimentInfo("default", exp_path)
    session = storage.get_session("default", exp_info.db_path)
    try:
        storage.add_student(session, "s001", "Alice")
        for i in range(count):
            storage.add_log(
                session,
                student_id="s001",
                experiment="default",
                func_name="square",
                args=[i],
                result=i * i,
                trial=f"run-{i % 2}",
            )
    finally:
        session.close()


class TestExportLogsFn:
    def test_export_jsonlines(self, tmp_root):
        _seed_logs(tmp_root, 5)
        out_file = tmp_root / "export.jsonl"
        count = export_logs_fn("default", "jsonlines", out_file, root=tmp_root)
        storage.close_all_engines()
        assert count == 5
        lines = out_file.read_text().strip().split("\n")
        assert len(lines) == 5
        entry = json.loads(lines[0])
        assert "id" in entry
        assert "student_id" in entry
        assert "func_name" in entry

    def test_export_csv(self, tmp_root):
        _seed_logs(tmp_root, 3)
        out_file = tmp_root / "export.csv"
        count = export_logs_fn("default", "csv", out_file, root=tmp_root)
        storage.close_all_engines()
        assert count == 3
        text = out_file.read_text()
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        assert len(rows) == 3
        assert "id" in rows[0]
        assert "student_id" in rows[0]
        assert "func_name" in rows[0]

    def test_export_csv_columns(self, tmp_root):
        _seed_logs(tmp_root, 1)
        out_file = tmp_root / "export.csv"
        export_logs_fn("default", "csv", out_file, root=tmp_root)
        storage.close_all_engines()
        text = out_file.read_text()
        header = text.split("\n")[0]
        for col in ["id", "ts", "student_id", "experiment", "trial", "func_name", "args", "result", "error"]:
            assert col in header

    def test_export_empty_experiment(self, tmp_root):
        count = export_logs_fn("default", "jsonlines", tmp_root / "empty.jsonl", root=tmp_root)
        storage.close_all_engines()
        assert count == 0

    def test_export_nonexistent_experiment(self, tmp_root):
        import typer
        with pytest.raises(typer.BadParameter, match="not found"):
            export_logs_fn("nonexistent", "jsonlines", root=tmp_root)

    def test_export_jsonlines_entry_shape(self, tmp_root):
        _seed_logs(tmp_root, 1)
        out_file = tmp_root / "shape.jsonl"
        export_logs_fn("default", "jsonlines", out_file, root=tmp_root)
        storage.close_all_engines()
        entry = json.loads(out_file.read_text().strip())
        assert entry["student_id"] == "s001"
        assert entry["func_name"] == "square"
        assert entry["experiment"] == "default"

    def test_export_pagination(self, tmp_root):
        """Ensure export handles more logs than a single page."""
        _seed_logs(tmp_root, 20)
        out_file = tmp_root / "big.jsonl"
        count = export_logs_fn("default", "jsonlines", out_file, root=tmp_root)
        storage.close_all_engines()
        assert count == 20
        lines = out_file.read_text().strip().split("\n")
        assert len(lines) == 20

    def test_export_csv_args_are_json(self, tmp_root):
        _seed_logs(tmp_root, 1)
        out_file = tmp_root / "args.csv"
        export_logs_fn("default", "csv", out_file, root=tmp_root)
        storage.close_all_engines()
        reader = csv.DictReader(open(out_file))
        row = next(reader)
        parsed = json.loads(row["args"])
        assert isinstance(parsed, list)


class TestExportCommand:
    def test_export_to_file(self, tmp_root):
        _seed_logs(tmp_root, 3)
        out_file = tmp_root / "cli_out.jsonl"
        result = runner.invoke(app, [
            "export", "default",
            "--format", "jsonlines",
            "--output", str(out_file),
            "--root", str(tmp_root),
        ])
        storage.close_all_engines()
        assert result.exit_code == 0
        assert "3 log" in result.output

    def test_export_csv_to_file(self, tmp_root):
        _seed_logs(tmp_root, 2)
        out_file = tmp_root / "cli_out.csv"
        result = runner.invoke(app, [
            "export", "default",
            "--format", "csv",
            "--output", str(out_file),
            "--root", str(tmp_root),
        ])
        storage.close_all_engines()
        assert result.exit_code == 0
        assert "2 log" in result.output
        assert out_file.is_file()

    def test_export_nonexistent(self, tmp_root):
        result = runner.invoke(app, [
            "export", "nope",
            "--root", str(tmp_root),
        ])
        assert result.exit_code == 1

    def test_export_bad_format(self, tmp_root):
        result = runner.invoke(app, [
            "export", "default",
            "--format", "xml",
            "--root", str(tmp_root),
        ])
        assert result.exit_code == 1

    def test_export_default_filename_jsonl(self, tmp_root, monkeypatch):
        _seed_logs(tmp_root, 2)
        monkeypatch.chdir(tmp_root)
        result = runner.invoke(app, [
            "export", "default",
            "--format", "jsonlines",
            "--root", str(tmp_root),
        ])
        storage.close_all_engines()
        assert result.exit_code == 0
        assert "default.jsonl" in result.output
        assert (tmp_root / "default.jsonl").is_file()
        lines = (tmp_root / "default.jsonl").read_text().strip().split("\n")
        assert len(lines) == 2

    def test_export_default_filename_csv(self, tmp_root, monkeypatch):
        _seed_logs(tmp_root, 2)
        monkeypatch.chdir(tmp_root)
        result = runner.invoke(app, [
            "export", "default",
            "--format", "csv",
            "--root", str(tmp_root),
        ])
        storage.close_all_engines()
        assert result.exit_code == 0
        assert "default.csv" in result.output
        assert (tmp_root / "default.csv").is_file()
