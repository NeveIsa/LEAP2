---
name: gradient-descent-2d
display_name: Gradient Descent 2D
description: Optimize a 2D function with two local minima using gradient descent.
author: "Sampad Mohanty"
organization: "University of Southern California"
tags: [optimization, calculus, gradient-descent, numerical-methods]
version: "1.0.0"
entry_point: dashboard.html
leap_version: ">=1.0"
require_registration: true
---

# Gradient Descent 2D

Minimize a non-convex 2D function using gradient descent. The objective function has two local minima — where your optimizer converges depends on the starting point and learning rate.

## Objective Function

```
f(x, y) = ((x-20)² + 10·(y-20)²) · (5·(x+20)² + (y+20)²) / 100
```

Two local minima near **(20, 20)** and **(-20, -20)**.

## Functions

- **`f(x, y)`** — Evaluate the objective function. Returns a float.
- **`df(x, y)`** — Gradient of the objective function. Returns `(∂f/∂x, ∂f/∂y)`.

Browse all functions with signatures and docs at `/static/functions.html?exp=gradient-descent-2d`.

## Student Workflow

1. Write a gradient descent loop in Python that calls `f()` and `df()` via RPC.
2. Experiment with different starting points, learning rates, and iteration counts.
3. Open the [dashboard](dashboard.html) and click **Load Trial** to visualize your optimization path on the function landscape.
4. View your call history at `/static/logs.html?exp=gradient-descent-2d`.

## Python Client

```python
from leap.client import Client

c = Client("http://localhost:9000", student_id="s001",
           experiment="gradient-descent-2d", trial_name="run-1")

# Evaluate the function and gradient at a point
print(c.f(10, 5))        # function value
print(c.df(10, 5))       # (df/dx, df/dy)

# Use df() to implement your gradient descent algorithm!
```

## JavaScript Client (Browser)

```javascript
import { RPCClient } from "/static/rpcclient.js";

const rpc = RPCClient.fromCurrentPage({ studentId: "s001" });

const fVal = await rpc.f(10, 5);
const [gx, gy] = await rpc.df(10, 5);
```
