---
name: graph-search
display_name: Graph Search
description: Explore graphs using BFS or DFS — grids, trees, and custom graphs.
author: "Sampad Mohanty"
organization: "University of Southern California"
tags: [algorithms, graphs, BFS, DFS, CS2]
version: "1.0.0"
entry_point: dashboard.html
leap_version: ">=1.0"
require_registration: true
pages:
  - {name: "Visualize", file: "visualization.html", admin: true}
---

# Graph Search

Explore graphs by discovering neighbors one node at a time. Implement breadth-first search (BFS) or depth-first search (DFS) using the RPC functions, then visualize your traversal path.

## Available Graphs

| Name | Type | Description |
|------|------|-------------|
| `grid-3x3` | Grid | A small 3×3 grid graph (9 nodes) |
| `grid-5x5` | Grid | A 5×5 grid graph (25 nodes) |
| `binary-tree` | Tree | A complete binary tree of depth 3 (7 nodes) |
| `petersen` | Graph | The Petersen graph — 10 nodes, 15 edges, 3-regular |
| `cycle-6` | Cycle | A simple cycle with 6 nodes |

Instructors can add new graphs by placing a YAML file in the `graphs/` directory.

## Functions

- **`list_graphs()`** — List all available graphs with metadata.
- **`start()`** — Get the start node and graph info. The graph is determined by your client's `trial_name`.
- **`neighbor(node)`** — Get the neighbors of a node in the current graph.
- **`get_graph(graph_name)`** — Get the full graph structure (nodes, edges, positions) for visualization.

Browse all functions with signatures and docs at `/static/functions.html?exp=graph-search`.

## Student Workflow

1. Choose a graph from the list above.
2. Set your client's `trial_name` to the graph name.
3. Call `start()` to get the starting node.
4. Implement BFS or DFS by calling `neighbor(node)` to discover adjacent nodes.
5. Open the dashboard to see the graph structure interactively.

## Python Client

```python
from leap.client import Client

c = Client("http://localhost:9000", student_id="s001",
           experiment="graph-search", trial_name="binary-tree")

# See available graphs
print(c.list_graphs())

# Get starting info
info = c.start()
print(info)  # {"start": "1", "node_count": 7, ...}

# Explore neighbors
print(c.neighbor("1"))    # ["2", "3"]
print(c.neighbor("2"))    # ["1", "4", "5"]

# Implement BFS
from collections import deque

start = info["start"]
visited = set()
queue = deque([start])
order = []

while queue:
    node = queue.popleft()
    if node in visited:
        continue
    visited.add(node)
    order.append(node)
    for nbr in c.neighbor(node):
        if nbr not in visited:
            queue.append(nbr)

print("BFS order:", order)
```

## JavaScript Client (Browser)

```javascript
import { RPCClient } from "/static/rpcclient.js";

const rpc = RPCClient.fromCurrentPage({
    studentId: "s001",
    trial: "binary-tree"
});

const info = await rpc.start();
const neighbors = await rpc.neighbor("1");
```

## Adding Custom Graphs

Create a YAML file in the `graphs/` directory:

### Grid graph

```yaml
name: my-grid
type: grid
display_name: "My Grid"
description: "A custom grid graph."
rows: 4
cols: 6
start: "0,0"
```

### Adjacency list graph

```yaml
name: my-graph
type: adjacency
display_name: "My Graph"
description: "A custom graph."
start: "A"
edges:
  "A": ["B", "C"]
  "B": ["A", "D"]
  "C": ["A", "D"]
  "D": ["B", "C"]
positions:          # optional — for visualization layout (x, y)
  "A": [100, 100]
  "B": [300, 100]
  "C": [100, 300]
  "D": [300, 300]
```
