"""Core math functions — all logged, registration required."""


def square(x: float) -> float:
    """Return x squared."""
    return x * x


def cubic(x: float) -> float:
    """Return x cubed."""
    return x * x * x


def add(a: float, b: float) -> float:
    """Return a + b."""
    return a + b


def rosenbrock(x: float, y: float) -> float:
    """Evaluate the Rosenbrock function: (1-x)^2 + 100*(y-x^2)^2."""
    return (1 - x) ** 2 + 100 * (y - x**2) ** 2


def bisect(f_left: float, f_right: float, target: float = 0.0) -> float:
    """Return the midpoint of an interval — one step of bisection method."""
    return (f_left + f_right) / 2.0


def gradient_step(x: float, grad: float, lr: float = 0.01) -> float:
    """One gradient descent step: x - lr * grad."""
    return x - lr * grad
