"""Gradient descent 2D — objective function and analytic gradient."""

from __future__ import annotations
from leap import ratelimit

@ratelimit(False)
def f(x: float, y: float) -> float:
    """Evaluate the objective function at (x, y).

    f(x, y) = ((x-20)^2 + 10*(y-20)^2) * (5*(x+20)^2 + (y+20)^2) / 100

    Has two local minima near (20, 20) and (-20, -20).
    """
    A = (x - 20) ** 2 + 10 * (y - 20) ** 2
    B = 5 * (x + 20) ** 2 + (y + 20) ** 2
    return A * B / 100

@ratelimit(False)
def df(x: float, y: float) -> tuple[float, float]:
    """Return the gradient (df/dx, df/dy) at (x, y)."""
    A = (x - 20) ** 2 + 10 * (y - 20) ** 2
    B = 5 * (x + 20) ** 2 + (y + 20) ** 2
    dA_dx = 2 * (x - 20)
    dA_dy = 20 * (y - 20)
    dB_dx = 10 * (x + 20)
    dB_dy = 2 * (y + 20)
    df_dx = (dA_dx * B + A * dB_dx) / 100
    df_dy = (dA_dy * B + A * dB_dy) / 100
    return (df_dx, df_dy)
