"""High-frequency simulation functions — @nolog to prevent DB flooding."""

from leap import nolog

_state: dict[str, float] = {}


@nolog
def step(student_id: str, dx: float = 0.0, dy: float = 0.0) -> dict:
    """Move the agent by (dx, dy). Called at high frequency by UI — NOT logged."""
    key = student_id
    if key not in _state:
        _state[key] = {"x": 0.0, "y": 0.0}
    _state[key]["x"] += dx
    _state[key]["y"] += dy
    return dict(_state[key])


@nolog
def get_position(student_id: str) -> dict:
    """Return current agent position. Polled frequently — NOT logged."""
    return dict(_state.get(student_id, {"x": 0.0, "y": 0.0}))


def reset(student_id: str) -> dict:
    """Reset agent to origin. Infrequent — LOGGED."""
    _state[student_id] = {"x": 0.0, "y": 0.0}
    return dict(_state[student_id])
