"""Tests for function discovery filtering — imports should not be exposed as RPC functions."""

from __future__ import annotations

from pathlib import Path

from leap.core.experiment import load_functions


class TestImportFiltering:
    def test_leap_imports_not_exposed(self, tmp_path: Path):
        """Importing leap decorators should not expose them as RPC functions."""
        funcs_dir = tmp_path / "funcs"
        funcs_dir.mkdir()
        (funcs_dir / "myfuncs.py").write_text(
            "from leap import nolog, noregcheck, withctx, ctx\n\n"
            "@nolog\n"
            "def fast(): return 'fast'\n\n"
            "@withctx\n"
            "def contextual(): return 'ctx'\n\n"
            "def plain(): return 'plain'\n"
        )
        functions = load_functions(funcs_dir)
        # Real functions are loaded
        assert "fast" in functions
        assert "contextual" in functions
        assert "plain" in functions
        # Imports are NOT exposed
        assert "nolog" not in functions
        assert "noregcheck" not in functions
        assert "withctx" not in functions
        assert "ctx" not in functions

    def test_stdlib_imports_not_exposed(self, tmp_path: Path):
        """Importing stdlib functions should not expose them."""
        funcs_dir = tmp_path / "funcs"
        funcs_dir.mkdir()
        (funcs_dir / "funcs.py").write_text(
            "from math import sqrt, floor\n"
            "import json\n\n"
            "def hypotenuse(a, b): return sqrt(a**2 + b**2)\n"
        )
        functions = load_functions(funcs_dir)
        assert "hypotenuse" in functions
        assert "sqrt" not in functions
        assert "floor" not in functions
        assert "json" not in functions

    def test_all_overrides_module_check(self, tmp_path: Path):
        """__all__ still works as explicit override."""
        funcs_dir = tmp_path / "funcs"
        funcs_dir.mkdir()
        (funcs_dir / "explicit.py").write_text(
            "from math import sqrt\n\n"
            "__all__ = ['sqrt', 'myfunc']\n\n"
            "def myfunc(): return 1\n"
            "def hidden(): return 2\n"
        )
        functions = load_functions(funcs_dir)
        assert "sqrt" in functions  # explicitly exported via __all__
        assert "myfunc" in functions
        assert "hidden" not in functions

    def test_locally_defined_functions_always_loaded(self, tmp_path: Path):
        """Functions defined in the module are always loaded (no __all__ needed)."""
        funcs_dir = tmp_path / "funcs"
        funcs_dir.mkdir()
        (funcs_dir / "local.py").write_text(
            "def alpha(): return 'a'\n"
            "def beta(): return 'b'\n"
            "def _private(): return 'hidden'\n"
        )
        functions = load_functions(funcs_dir)
        assert "alpha" in functions
        assert "beta" in functions
        assert "_private" not in functions  # underscore prefix still skipped
