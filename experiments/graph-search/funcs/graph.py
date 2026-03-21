"""Graph search — explore graphs using BFS or DFS via neighbor discovery."""

from __future__ import annotations

import math
from pathlib import Path

import yaml

from leap import ctx, nolog, noregcheck, withctx


def _graphs_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "graphs"


def _load_graph(name: str) -> dict:
    """Load a graph definition by name."""
    path = _graphs_dir() / f"{name}.yaml"
    if not path.exists():
        available = [f.stem for f in sorted(_graphs_dir().glob("*.yaml"))]
        raise ValueError(
            f"Graph not found: '{name}'. Available: {', '.join(available)}"
        )
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _get_neighbors(graph: dict, node: str) -> list[str]:
    """Return neighbors for a node given a graph definition."""
    node = str(node)
    gtype = graph.get("type", "adjacency")
    if gtype == "grid":
        parts = node.split(",")
        x, y = int(parts[0]), int(parts[1])
        rows, cols = graph["rows"], graph["cols"]
        neighbors = []
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < cols and 0 <= ny < rows:
                neighbors.append(f"{nx},{ny}")
        return neighbors
    else:
        edges = graph.get("edges", {})
        if node not in edges:
            raise ValueError(f"Node '{node}' not found in graph '{graph['name']}'")
        return list(edges[node])


def _grid_to_full(graph: dict) -> dict:
    """Expand a grid definition into full nodes/edges/positions."""
    rows, cols = graph["rows"], graph["cols"]
    nodes = []
    edges = {}
    positions = {}
    spacing = 80
    for y in range(rows):
        for x in range(cols):
            nid = f"{x},{y}"
            nodes.append(nid)
            positions[nid] = [x * spacing + 40, y * spacing + 40]
            nbrs = []
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < cols and 0 <= ny < rows:
                    nbrs.append(f"{nx},{ny}")
            edges[nid] = nbrs
    return {"nodes": nodes, "edges": edges, "positions": positions}


def _circular_layout(nodes: list[str], radius: int = 200, cx: int = 300, cy: int = 300) -> dict:
    """Compute a circular layout for nodes without explicit positions."""
    n = len(nodes)
    positions = {}
    for i, nid in enumerate(nodes):
        angle = 2 * math.pi * i / n - math.pi / 2
        positions[nid] = [round(cx + radius * math.cos(angle)), round(cy + radius * math.sin(angle))]
    return positions


@nolog
@noregcheck
def list_graphs() -> list:
    """List available graphs with their metadata."""
    graphs = []
    for f in sorted(_graphs_dir().glob("*.yaml")):
        g = yaml.safe_load(f.read_text(encoding="utf-8"))
        info = {
            "name": g["name"],
            "display_name": g.get("display_name", g["name"]),
            "description": g.get("description", ""),
            "type": g.get("type", "adjacency"),
        }
        if g.get("type") == "grid":
            info["rows"] = g["rows"]
            info["cols"] = g["cols"]
        else:
            info["node_count"] = len(g.get("edges", {}))
        graphs.append(info)
    return graphs


@withctx
def start() -> dict:
    """Get the start node and graph info. Set your client's trial_name to the graph name."""
    graph = _load_graph(ctx.trial)
    info = {
        "start": graph["start"],
        "display_name": graph.get("display_name", ctx.trial),
        "description": graph.get("description", ""),
        "type": graph.get("type", "adjacency"),
    }
    if graph.get("type") == "grid":
        info["rows"] = graph["rows"]
        info["cols"] = graph["cols"]
    else:
        info["node_count"] = len(graph.get("edges", {}))
    return info


@withctx
def neighbor(node: str) -> list:
    """Get the neighbors of a node in the current graph (set by trial name)."""
    graph = _load_graph(ctx.trial)
    return _get_neighbors(graph, node)


@nolog
@noregcheck
def get_graph(graph_name: str) -> dict:
    """Return the full graph structure for visualization: nodes, edges, positions, start."""
    graph = _load_graph(graph_name)
    if graph.get("type") == "grid":
        full = _grid_to_full(graph)
        nodes = full["nodes"]
        edges = full["edges"]
        positions = full["positions"]
    else:
        nodes = list(graph.get("edges", {}).keys())
        edges = graph.get("edges", {})
        positions = graph.get("positions", _circular_layout(nodes))
    return {
        "name": graph["name"],
        "display_name": graph.get("display_name", graph["name"]),
        "type": graph.get("type", "adjacency"),
        "start": graph["start"],
        "nodes": nodes,
        "edges": edges,
        "positions": positions,
    }
