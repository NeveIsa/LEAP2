"""Live demo — audience picks a starting point for gradient descent."""

from leap import adminonly, nolog, noregcheck

_current_slide = 1


@adminonly
@nolog
@noregcheck
def set_slide(n: int) -> dict:
    """Set the current slide number (presenter only)."""
    global _current_slide
    _current_slide = n
    return {"slide": n}


@nolog
@noregcheck
def get_slide() -> dict:
    """Get the current slide number."""
    return {"slide": _current_slide}


@noregcheck
def pick_start(x: float, y: float) -> dict:
    """Pick your starting point for gradient descent."""
    return {"x": x, "y": y, "message": "Point recorded!"}
