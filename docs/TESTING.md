# Testing

## LEAP2 Test Suite

```bash
pip install -e ".[dev]"
pytest tests/
```

### Test Structure

```
tests/
├── conftest.py               # Shared fixtures (tmp_root, tmp_credentials)
├── core/                     # storage, auth, experiment, rpc, withctx (212 tests)
│   ├── test_withctx.py       # @withctx decorator + ctx proxy injection (10 tests)
│   └── test_function_discovery.py  # Import filtering in function loading (4 tests)
├── api/
│   ├── test_api.py           # Full API integration (89 tests)
│   ├── test_ui_serving.py    # Static mounts, landing, login (22 tests)
│   └── test_phase4.py        # Shared pages, CORS, function flags (16 tests)
├── client/
│   ├── test_rpcclient.py     # RPCClient: call, dispatch, help, is_registered, fetch_logs, exceptions (42 tests)
│   └── test_logclient.py     # Python LogClient (23 tests)
└── cli/
    ├── test_cli_phase2.py    # init, new, list, validate, config, doctor (83 tests)
    ├── test_cli_phase3.py    # install, copy, gitignore, pip deps (41 tests)
    ├── test_cli_phase4.py    # export (14 tests)
    └── test_cli_phase5.py    # discover, publish (19 tests)
```

All tests use isolated temp directories with per-test DuckDB instances. No shared state.

## Testing Experiments in Your Lab

Experiment-specific tests live in the **lab repo**, not in LEAP2. Create a `tests/` directory in your lab root:

```
my-lab/
├── experiments/
│   ├── gradient-descent/
│   │   └── funcs/
│   │       └── optimize.py
│   └── graph-search/
│       └── funcs/
│           └── graph.py
└── tests/
    ├── test_gradient_descent.py
    └── test_graph_search.py
```

Since experiment names can contain hyphens (not valid Python identifiers), import the module manually:

```python
import importlib.util, sys
from pathlib import Path

_mod_path = Path(__file__).parent.parent / "experiments" / "graph-search" / "funcs" / "graph.py"
_spec = importlib.util.spec_from_file_location("graph_funcs", _mod_path)
mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = mod
_spec.loader.exec_module(mod)

def test_something():
    assert mod.get_graph("grid-3x3")["start"] == "0,0"
```

Run with `pytest tests/` from the lab root. Install `pytest` in your lab's environment (`pip install pytest`).
