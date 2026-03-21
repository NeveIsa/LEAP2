"""Tests for the graph-search experiment — graph loading, neighbors, get_graph."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# graph-search has a hyphen — not a valid Python package name, so import manually.
_mod_path = Path(__file__).resolve().parents[2] / "experiments" / "graph-search" / "funcs" / "graph.py"
_spec = importlib.util.spec_from_file_location("graph_search_funcs", _mod_path)
gs = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = gs
_spec.loader.exec_module(gs)


class TestLoadGraph:
    def test_load_existing_graph(self):
        g = gs._load_graph("binary-tree")
        assert g["name"] == "binary-tree"
        assert g["start"] == "1"

    def test_load_grid(self):
        g = gs._load_graph("grid-3x3")
        assert g["type"] == "grid"
        assert g["rows"] == 3
        assert g["cols"] == 3

    def test_load_nonexistent_raises(self):
        with pytest.raises(ValueError, match="Graph not found"):
            gs._load_graph("does-not-exist")

    def test_error_lists_available(self):
        with pytest.raises(ValueError, match="binary-tree"):
            gs._load_graph("nope")


class TestGetNeighbors:
    def test_grid_center(self):
        g = gs._load_graph("grid-3x3")
        nbrs = gs._get_neighbors(g, "1,1")
        assert set(nbrs) == {"1,2", "1,0", "2,1", "0,1"}

    def test_grid_corner(self):
        g = gs._load_graph("grid-3x3")
        nbrs = gs._get_neighbors(g, "0,0")
        assert set(nbrs) == {"0,1", "1,0"}

    def test_adjacency_graph(self):
        g = gs._load_graph("binary-tree")
        nbrs = gs._get_neighbors(g, "1")
        assert set(nbrs) == {"2", "3"}

    def test_adjacency_leaf(self):
        g = gs._load_graph("binary-tree")
        nbrs = gs._get_neighbors(g, "4")
        assert nbrs == ["2"]

    def test_unknown_node_raises(self):
        g = gs._load_graph("binary-tree")
        with pytest.raises(ValueError, match="not found"):
            gs._get_neighbors(g, "999")


class TestGridToFull:
    def test_node_count(self):
        g = gs._load_graph("grid-3x3")
        full = gs._grid_to_full(g)
        assert len(full["nodes"]) == 9

    def test_all_nodes_have_positions(self):
        g = gs._load_graph("grid-5x5")
        full = gs._grid_to_full(g)
        assert len(full["positions"]) == 25
        for nid in full["nodes"]:
            assert nid in full["positions"]
            assert len(full["positions"][nid]) == 2

    def test_edges_symmetric(self):
        g = gs._load_graph("grid-3x3")
        full = gs._grid_to_full(g)
        for nid, nbrs in full["edges"].items():
            for nbr in nbrs:
                assert nid in full["edges"][nbr], f"{nid} in {nbr}'s neighbors but not reverse"


class TestCircularLayout:
    def test_all_nodes_get_positions(self):
        nodes = ["A", "B", "C", "D"]
        pos = gs._circular_layout(nodes)
        assert set(pos.keys()) == set(nodes)

    def test_positions_are_pairs(self):
        pos = gs._circular_layout(["X", "Y", "Z"])
        for p in pos.values():
            assert len(p) == 2


class TestListGraphs:
    def test_returns_list(self):
        result = gs.list_graphs()
        assert isinstance(result, list)
        assert len(result) >= 5  # shipped with 5 graphs

    def test_has_required_fields(self):
        for g in gs.list_graphs():
            assert "name" in g
            assert "display_name" in g
            assert "type" in g

    def test_contains_known_graphs(self):
        names = {g["name"] for g in gs.list_graphs()}
        assert "grid-3x3" in names
        assert "binary-tree" in names
        assert "petersen" in names


class TestGetGraph:
    def test_returns_full_structure(self):
        result = gs.get_graph("binary-tree")
        assert "nodes" in result
        assert "edges" in result
        assert "positions" in result
        assert "start" in result
        assert result["start"] == "1"

    def test_grid_expansion(self):
        result = gs.get_graph("grid-3x3")
        assert len(result["nodes"]) == 9
        assert "0,0" in result["nodes"]
        assert "2,2" in result["nodes"]

    def test_petersen_graph(self):
        result = gs.get_graph("petersen")
        assert len(result["nodes"]) == 10
        # Petersen graph is 3-regular (each node has 3 neighbors)
        for nid in result["nodes"]:
            assert len(result["edges"][nid]) == 3

    def test_positions_present_for_all_nodes(self):
        for name in ["binary-tree", "grid-3x3", "cycle-6", "petersen"]:
            result = gs.get_graph(name)
            for nid in result["nodes"]:
                assert nid in result["positions"], f"Missing position for {nid} in {name}"

    def test_adjacency_without_positions_gets_circular(self):
        """Graphs without explicit positions fall back to circular layout."""
        g = gs._load_graph("cycle-6")
        # Remove positions to test fallback
        g_copy = {k: v for k, v in g.items() if k != "positions"}
        g_copy["type"] = "adjacency"
        nodes = list(g_copy["edges"].keys())
        pos = gs._circular_layout(nodes)
        assert len(pos) == 6
