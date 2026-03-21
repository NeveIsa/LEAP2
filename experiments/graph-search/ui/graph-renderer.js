/**
 * graph-renderer.js — shared graph visualization module.
 *
 * Usage:
 *   import { GraphRenderer } from "./graph-renderer.js";
 *   const renderer = new GraphRenderer(svgElement);
 *   renderer.setGraph(graphData);            // from get_graph()
 *   renderer.setState({ visited, current, start });
 *   renderer.onNodeClick = (nodeId) => { ... };
 */

export class GraphRenderer {
  /**
   * @param {SVGSVGElement} svg — the <svg> element to render into
   * @param {object} [opts]
   * @param {boolean} [opts.interactive=false] — enable click handlers
   */
  constructor(svg, opts = {}) {
    this.svg = svg;
    this.interactive = opts.interactive || false;
    this.graph = null;
    this.state = { visited: new Set(), current: null, start: null };
    this.onNodeClick = null;

    // Colors (read from CSS variables or fallback)
    this._colors = {
      unvisited:   "#d6d3d1",
      visited:     "#1a6b5a",
      current:     "#c4653a",
      start:       "#e09550",
      edge:        "#a8a29e",
      edgeVisited: "#1a6b5a",
      text:        "#1c1917",
      textLight:   "#fafaf9",
    };
  }

  /** Load graph data (output of get_graph()). */
  setGraph(graphData) {
    this.graph = graphData;
    this._render();
  }

  /** Update traversal state and re-render. */
  setState(state) {
    this.state = {
      visited: state.visited || new Set(),
      current: state.current || null,
      start:   state.start || (this.graph && this.graph.start) || null,
    };
    this._render();
  }

  /** Full re-render. */
  _render() {
    if (!this.graph) return;
    var g = this.graph;
    var pos = g.positions;
    var nodes = g.nodes;
    var edges = g.edges;
    var state = this.state;

    // Compute SVG viewBox from positions
    var xs = nodes.map(function(n) { return pos[n][0]; });
    var ys = nodes.map(function(n) { return pos[n][1]; });
    var pad = 50;
    var minX = Math.min.apply(null, xs) - pad;
    var minY = Math.min.apply(null, ys) - pad;
    var maxX = Math.max.apply(null, xs) + pad;
    var maxY = Math.max.apply(null, ys) + pad;
    this.svg.setAttribute("viewBox", minX + " " + minY + " " + (maxX - minX) + " " + (maxY - minY));

    // Clear
    this.svg.innerHTML = "";

    // Defs for pulse animation
    var defs = this._el("defs");
    defs.innerHTML =
      '<style>' +
      '@keyframes gr-pulse { 0%,100%{r:22} 50%{r:27} }' +
      '.gr-current-circle { animation: gr-pulse 1.2s ease-in-out infinite; }' +
      '</style>';
    this.svg.appendChild(defs);

    // Draw edges first (below nodes)
    var edgeGroup = this._el("g", { class: "gr-edges" });
    var drawnEdges = {};
    var self = this;
    nodes.forEach(function(nid) {
      var nbrs = edges[nid] || [];
      nbrs.forEach(function(nbr) {
        var key = [nid, nbr].sort().join("--");
        if (drawnEdges[key]) return;
        drawnEdges[key] = true;
        var bothVisited = state.visited.has(nid) && state.visited.has(nbr);
        var stroke = bothVisited ? self._colors.edgeVisited : self._colors.edge;
        var opacity = bothVisited ? 0.7 : 0.3;
        var line = self._el("line", {
          x1: pos[nid][0], y1: pos[nid][1],
          x2: pos[nbr][0], y2: pos[nbr][1],
          stroke: stroke,
          "stroke-width": bothVisited ? 2.5 : 1.5,
          "stroke-opacity": opacity,
        });
        edgeGroup.appendChild(line);
      });
    });
    this.svg.appendChild(edgeGroup);

    // Draw nodes
    var nodeGroup = this._el("g", { class: "gr-nodes" });
    nodes.forEach(function(nid) {
      var x = pos[nid][0];
      var y = pos[nid][1];
      var isCurrent = nid === state.current;
      var isVisited = state.visited.has(nid);
      var isStart = nid === state.start;

      var fill = self._colors.unvisited;
      var textFill = self._colors.text;
      if (isCurrent) {
        fill = self._colors.current;
        textFill = self._colors.textLight;
      } else if (isVisited) {
        fill = self._colors.visited;
        textFill = self._colors.textLight;
      }

      var gNode = self._el("g", { class: "gr-node", "data-node": nid });

      // Start node ring
      if (isStart) {
        var ring = self._el("circle", {
          cx: x, cy: y, r: 28,
          fill: "none",
          stroke: self._colors.start,
          "stroke-width": 3,
          "stroke-dasharray": "5,3",
        });
        gNode.appendChild(ring);
      }

      // Node circle
      var circle = self._el("circle", {
        cx: x, cy: y, r: 22,
        fill: fill,
        stroke: isCurrent ? self._colors.current : (isVisited ? self._colors.visited : "#78716c"),
        "stroke-width": isCurrent ? 3 : 1.5,
      });
      if (isCurrent) circle.setAttribute("class", "gr-current-circle");
      gNode.appendChild(circle);

      // Label
      var label = self._el("text", {
        x: x, y: y,
        "text-anchor": "middle",
        "dominant-baseline": "central",
        fill: textFill,
        "font-size": nid.length > 3 ? "10" : "12",
        "font-weight": "600",
        "font-family": "system-ui, sans-serif",
        "pointer-events": "none",
      });
      label.textContent = nid;
      gNode.appendChild(label);

      // Click handler
      if (self.interactive && self.onNodeClick) {
        gNode.style.cursor = "pointer";
        gNode.addEventListener("click", function() { self.onNodeClick(nid); });
      }

      nodeGroup.appendChild(gNode);
    });
    this.svg.appendChild(nodeGroup);
  }

  /** Create an SVG element with attributes. */
  _el(tag, attrs) {
    var el = document.createElementNS("http://www.w3.org/2000/svg", tag);
    if (attrs) {
      Object.keys(attrs).forEach(function(k) {
        el.setAttribute(k, attrs[k]);
      });
    }
    return el;
  }
}
