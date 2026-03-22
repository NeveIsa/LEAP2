---
name: monte-carlo
display_name: Monte Carlo Pi
description: Estimate pi by sampling random points and checking if they fall inside the unit circle.
author: "Sampad Mohanty"
organization: "University of Southern California"
tags: [probability, statistics, monte-carlo, sampling, pi]
version: "1.0.0"
entry_point: dashboard.html
leap_version: ">=1.0"
require_registration: true
---

# Monte Carlo Pi Estimation

Estimate the value of pi using the Monte Carlo method: sample random points in the square [-1, 1] x [-1, 1] and count how many fall inside the unit circle. The ratio of inside points to total points approximates pi/4.

## Functions

- **`random_point_square()`** — Returns a random (x, y) point in [-1, 1]^2.
- **`is_inside_unit_circle(x, y)`** — Returns `True` if (x, y) is inside the unit circle.
- **`estimate_pi(samples=10000)`** — Runs the full estimation: samples N points, returns `4 * inside / total`.

Browse all functions with signatures and docs at `/static/functions.html?exp=monte-carlo`.

## Student Workflow

1. Open the [dashboard](dashboard.html) — enter your student ID and a trial name.
2. Click **Sample** to generate one random point via RPC — the point is plotted on the canvas and the pi estimate updates live.
3. Click **Sample N** to generate a batch of points (up to 200 are plotted individually; larger batches use `estimate_pi` directly).
4. Watch the estimate converge toward pi as you add more points.
5. View your call history at `/static/logs.html?exp=monte-carlo`.

## Python Client

```python
from leap.client import Client

c = Client("http://localhost:9000", student_id="s001", experiment="monte-carlo")

# Sample a single point
x, y = c.random_point_square()
print(f"Point: ({x:.4f}, {y:.4f})")
print(f"Inside circle: {c.is_inside_unit_circle(x, y)}")

# Estimate pi with 10,000 samples
pi_est = c.estimate_pi(10000)
print(f"Pi estimate: {pi_est:.6f}")
```

## JavaScript Client (Browser)

```javascript
import { RPCClient } from "/static/rpcclient.js";

const rpc = RPCClient.fromCurrentPage({ studentId: "s001" });

const [x, y] = await rpc.random_point_square();
const inside = await rpc.is_inside_unit_circle(x, y);
const piEst = await rpc.estimate_pi(5000);
```
