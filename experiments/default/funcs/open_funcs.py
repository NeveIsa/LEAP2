"""Open utility functions — @noregcheck skips registration check."""

from leap import noregcheck


@noregcheck
def echo(x):
    """Return input unchanged. Open to all — no registration required. Still logged."""
    return x


@noregcheck
def ping() -> str:
    """Health check callable by anyone. Still logged."""
    return "pong"


@noregcheck
def server_time() -> str:
    """Return current server UTC time. Open to all."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat() + "Z"
