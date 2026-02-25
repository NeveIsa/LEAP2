"""Tests for leap.core.experiment — discovery, frontmatter, function loading, function info."""

from __future__ import annotations

from pathlib import Path

import pytest

from leap.core.experiment import (
    validate_experiment_name,
    parse_frontmatter,
    load_functions,
    get_function_info,
    ExperimentInfo,
    discover_experiments,
)


# ── Name Validation ──


class TestNameValidation:
    @pytest.mark.parametrize("name", [
        "default", "lab-1", "cs101_lab2", "a", "0test", "abc", "a-b-c", "x_y_z",
    ])
    def test_valid_names(self, name):
        assert validate_experiment_name(name) is True

    @pytest.mark.parametrize("name", [
        "", "Default", "my lab", "lab.1", "../evil", "-start", "_start",
        "UPPER", "has space", "a/b", "a\\b", "name!", "a..b",
    ])
    def test_invalid_names(self, name):
        assert validate_experiment_name(name) is False


# ── Frontmatter Parsing ──


class TestFrontmatter:
    def test_parse_valid(self, tmp_path: Path):
        readme = tmp_path / "README.md"
        readme.write_text(
            "---\nname: test\ndisplay_name: Test Lab\n"
            "require_registration: false\n---\n# Hello\n"
        )
        fm = parse_frontmatter(readme)
        assert fm["name"] == "test"
        assert fm["display_name"] == "Test Lab"
        assert fm["require_registration"] is False

    def test_parse_all_fields(self, tmp_path: Path):
        readme = tmp_path / "README.md"
        readme.write_text(
            "---\n"
            "name: mylab\n"
            "display_name: My Lab\n"
            "description: A test lab.\n"
            "entry_point: index.html\n"
            'leap_version: ">=1.0"\n'
            "require_registration: false\n"
            "---\n# Body\n"
        )
        fm = parse_frontmatter(readme)
        assert fm["name"] == "mylab"
        assert fm["display_name"] == "My Lab"
        assert fm["description"] == "A test lab."
        assert fm["entry_point"] == "index.html"
        assert fm["leap_version"] == ">=1.0"
        assert fm["require_registration"] is False

    def test_parse_missing_file(self, tmp_path: Path):
        fm = parse_frontmatter(tmp_path / "nope.md")
        assert fm["entry_point"] == "dashboard.html"
        assert fm["require_registration"] is True
        assert fm["display_name"] == ""
        assert fm["description"] == ""

    def test_parse_no_frontmatter(self, tmp_path: Path):
        readme = tmp_path / "README.md"
        readme.write_text("# Just markdown\nNo frontmatter here.")
        fm = parse_frontmatter(readme)
        assert fm["require_registration"] is True

    def test_parse_bad_yaml(self, tmp_path: Path):
        readme = tmp_path / "README.md"
        readme.write_text("---\n: [invalid yaml\n---\n")
        fm = parse_frontmatter(readme)
        assert fm["require_registration"] is True

    def test_parse_empty_frontmatter(self, tmp_path: Path):
        readme = tmp_path / "README.md"
        readme.write_text("---\n---\n# Nothing\n")
        fm = parse_frontmatter(readme)
        assert fm["entry_point"] == "dashboard.html"
        assert fm["require_registration"] is True

    def test_parse_extra_unknown_fields(self, tmp_path: Path):
        readme = tmp_path / "README.md"
        readme.write_text("---\nname: test\ncustom_field: hello\n---\n")
        fm = parse_frontmatter(readme)
        assert fm["name"] == "test"
        assert fm["custom_field"] == "hello"

    def test_parse_partial_frontmatter(self, tmp_path: Path):
        readme = tmp_path / "README.md"
        readme.write_text("---\nname: partial\n---\n")
        fm = parse_frontmatter(readme)
        assert fm["name"] == "partial"
        assert fm["entry_point"] == "dashboard.html"
        assert fm["require_registration"] is True

    def test_parse_unclosed_frontmatter(self, tmp_path: Path):
        readme = tmp_path / "README.md"
        readme.write_text("---\nname: test\nno closing delimiter\n")
        fm = parse_frontmatter(readme)
        assert fm["require_registration"] is True
        assert "name" not in fm  # defaults only


# ── Function Loading ──


class TestFunctionLoading:
    def test_load_functions(self, tmp_path: Path):
        funcs_dir = tmp_path / "funcs"
        funcs_dir.mkdir()
        (funcs_dir / "math.py").write_text(
            "def square(x): return x * x\n"
            "def _private(): pass\n"
        )
        functions = load_functions(funcs_dir)
        assert "square" in functions
        assert "_private" not in functions
        assert functions["square"](5) == 25

    def test_load_empty_dir(self, tmp_path: Path):
        funcs_dir = tmp_path / "funcs"
        funcs_dir.mkdir()
        assert load_functions(funcs_dir) == {}

    def test_load_missing_dir(self, tmp_path: Path):
        assert load_functions(tmp_path / "nope") == {}

    def test_load_skips_broken(self, tmp_path: Path):
        funcs_dir = tmp_path / "funcs"
        funcs_dir.mkdir()
        (funcs_dir / "good.py").write_text("def ok(): return 1\n")
        (funcs_dir / "bad.py").write_text("raise RuntimeError('broken')\n")
        functions = load_functions(funcs_dir)
        assert "ok" in functions
        assert functions["ok"]() == 1

    def test_load_multiple_files(self, tmp_path: Path):
        funcs_dir = tmp_path / "funcs"
        funcs_dir.mkdir()
        (funcs_dir / "a_math.py").write_text("def square(x): return x * x\n")
        (funcs_dir / "b_utils.py").write_text("def echo(x): return x\n")
        functions = load_functions(funcs_dir)
        assert "square" in functions
        assert "echo" in functions

    def test_load_skips_classes_and_modules(self, tmp_path: Path):
        funcs_dir = tmp_path / "funcs"
        funcs_dir.mkdir()
        (funcs_dir / "mixed.py").write_text(
            "import os\n"
            "class Foo: pass\n"
            "MY_CONST = 42\n"
            "def real_func(): return 1\n"
        )
        functions = load_functions(funcs_dir)
        assert "real_func" in functions
        assert "Foo" not in functions
        assert "os" not in functions
        assert "MY_CONST" not in functions  # not callable

    def test_load_functions_with_decorators(self, tmp_path: Path):
        funcs_dir = tmp_path / "funcs"
        funcs_dir.mkdir()
        (funcs_dir / "decorated.py").write_text(
            "def _marker(f):\n"
            "    f._marked = True\n"
            "    return f\n\n"
            "@_marker\n"
            "def tagged(): return 'yes'\n"
        )
        functions = load_functions(funcs_dir)
        assert "tagged" in functions
        assert functions["tagged"]() == "yes"
        assert getattr(functions["tagged"], "_marked", False) is True

    def test_load_duplicate_name_across_files(self, tmp_path: Path):
        funcs_dir = tmp_path / "funcs"
        funcs_dir.mkdir()
        (funcs_dir / "a_first.py").write_text("def dup(): return 'first'\n")
        (funcs_dir / "b_second.py").write_text("def dup(): return 'second'\n")
        functions = load_functions(funcs_dir)
        assert "dup" in functions
        # alphabetical order: b_second.py loaded after a_first.py, overwrites
        assert functions["dup"]() == "second"


# ── get_function_info ──


class TestGetFunctionInfo:
    def test_basic_function(self):
        def square(x: float) -> float:
            """Return x squared."""
            return x * x
        info = get_function_info(square)
        assert "x" in info["signature"]
        assert info["doc"] == "Return x squared."

    def test_function_no_doc(self):
        def nodoc(a, b): pass
        info = get_function_info(nodoc)
        assert info["doc"] == ""
        assert "a" in info["signature"]

    def test_function_no_annotations(self):
        def plain(x, y): pass
        info = get_function_info(plain)
        assert "x" in info["signature"]
        assert "y" in info["signature"]

    def test_function_with_defaults(self):
        def with_defaults(x, n=10, flag=True):
            """Has defaults."""
            pass
        info = get_function_info(with_defaults)
        assert "n=10" in info["signature"] or "n = 10" in info["signature"]
        assert info["doc"] == "Has defaults."

    def test_builtin_callable(self):
        info = get_function_info(len)
        assert "signature" in info
        assert "doc" in info


# ── ExperimentInfo ──


class TestExperimentInfo:
    def test_load(self, tmp_root: Path):
        exp = ExperimentInfo("default", tmp_root / "experiments" / "default")
        assert exp.display_name == "Test Lab"
        assert exp.require_registration is True
        assert "square" in exp.functions
        assert "add" in exp.functions
        assert exp.functions["square"](5) == 25

    def test_reload_functions(self, tmp_root: Path):
        exp = ExperimentInfo("default", tmp_root / "experiments" / "default")
        assert "square" in exp.functions
        (tmp_root / "experiments" / "default" / "funcs" / "extra.py").write_text(
            "def triple(x): return x * 3\n"
        )
        count = exp.reload_functions()
        assert "triple" in exp.functions
        assert count >= 3  # square, add, triple

    def test_metadata(self, tmp_root: Path):
        exp = ExperimentInfo("default", tmp_root / "experiments" / "default")
        meta = exp.to_metadata()
        assert meta["name"] == "default"
        assert meta["display_name"] == "Test Lab"
        assert "description" in meta
        assert "entry_point" in meta

    def test_get_functions_info(self, tmp_root: Path):
        exp = ExperimentInfo("default", tmp_root / "experiments" / "default")
        info = exp.get_functions_info()
        assert "square" in info
        assert "signature" in info["square"]
        assert "doc" in info["square"]

    def test_missing_readme_uses_defaults(self, tmp_path: Path):
        exp_dir = tmp_path / "experiments" / "noreadme"
        (exp_dir / "funcs").mkdir(parents=True)
        (exp_dir / "db").mkdir()
        exp = ExperimentInfo("noreadme", exp_dir)
        assert exp.display_name == "noreadme"  # fallback to folder name
        assert exp.require_registration is True
        assert exp.entry_point == "dashboard.html"

    def test_missing_funcs_dir(self, tmp_path: Path):
        exp_dir = tmp_path / "experiments" / "nofuncs"
        exp_dir.mkdir(parents=True)
        (exp_dir / "db").mkdir()
        exp = ExperimentInfo("nofuncs", exp_dir)
        assert exp.functions == {}

    def test_db_path(self, tmp_root: Path):
        exp = ExperimentInfo("default", tmp_root / "experiments" / "default")
        assert exp.db_path == tmp_root / "experiments" / "default" / "db" / "experiment.db"


# ── Discovery ──


class TestDiscovery:
    def test_discover(self, tmp_root: Path):
        exps = discover_experiments(tmp_root)
        assert "default" in exps
        assert exps["default"].display_name == "Test Lab"

    def test_discover_skips_invalid(self, tmp_root: Path):
        (tmp_root / "experiments" / "Bad Name").mkdir()
        exps = discover_experiments(tmp_root)
        assert "Bad Name" not in exps
        assert "default" in exps

    def test_discover_empty(self, tmp_path: Path):
        (tmp_path / "experiments").mkdir()
        exps = discover_experiments(tmp_path)
        assert len(exps) == 0

    def test_discover_multiple(self, tmp_root: Path):
        lab2 = tmp_root / "experiments" / "lab2"
        (lab2 / "funcs").mkdir(parents=True)
        (lab2 / "db").mkdir()
        (lab2 / "README.md").write_text(
            "---\nname: lab2\ndisplay_name: Lab 2\n---\n"
        )
        exps = discover_experiments(tmp_root)
        assert "default" in exps
        assert "lab2" in exps
        assert exps["lab2"].display_name == "Lab 2"

    def test_discover_skips_files(self, tmp_root: Path):
        (tmp_root / "experiments" / "not_a_dir.txt").write_text("file")
        exps = discover_experiments(tmp_root)
        assert "not_a_dir.txt" not in exps

    def test_discover_missing_experiments_dir(self, tmp_path: Path):
        exps = discover_experiments(tmp_path)
        assert len(exps) == 0

    def test_discover_sorted(self, tmp_root: Path):
        for name in ["zebra", "alpha", "middle"]:
            d = tmp_root / "experiments" / name
            (d / "funcs").mkdir(parents=True)
            (d / "db").mkdir()
        exps = discover_experiments(tmp_root)
        names = list(exps.keys())
        assert names == sorted(names)
