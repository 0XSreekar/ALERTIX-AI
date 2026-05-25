/**
 * Cascading hazard graph — simple force-directed layout in SVG.
 *
 * Nodes are real events; edges link events that occurred within Δd km / Δt h
 * of each other AND form a plausible cascade (cyclone → flood, eq → landslide).
 * We seed positions from lat/lon then run a few iterations of repulsion +
 * spring forces. Lightweight: no D3 dependency.
 */
import { useEffect, useMemo, useState } from "react";
import type {
  SentinelCascadeEdge,
  SentinelCascadeGraph,
  SentinelCascadeNode,
} from "@/lib/types";

const HAZARD_COLOR: Record<string, string> = {
  earthquake: "#ef4444",
  flood: "#38bdf8",
  cyclone: "#a78bfa",
  wildfire: "#f97316",
  landslide: "#92400e",
};

interface PositionedNode extends SentinelCascadeNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

function project(
  nodes: SentinelCascadeNode[],
  width: number,
  height: number,
): PositionedNode[] {
  if (nodes.length === 0) return [];
  const minLat = 6,
    maxLat = 38,
    minLon = 67,
    maxLon = 98;
  return nodes.map((n) => ({
    ...n,
    x: ((n.lon - minLon) / (maxLon - minLon)) * width,
    y: height - ((n.lat - minLat) / (maxLat - minLat)) * height,
    vx: 0,
    vy: 0,
  }));
}

function runForces(
  nodes: PositionedNode[],
  edges: SentinelCascadeEdge[],
  width: number,
  height: number,
  iterations = 60,
) {
  const idx = new Map(nodes.map((n, i) => [n.id, i]));
  const REPULSION = 1800;
  const SPRING = 0.04;
  const REST_LEN = 90;
  const DAMP = 0.78;
  for (let iter = 0; iter < iterations; iter++) {
    // Pairwise repulsion (O(n²) is fine for <60 nodes)
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i];
        const b = nodes[j];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const distSq = dx * dx + dy * dy + 0.01;
        const force = REPULSION / distSq;
        const fx = (dx / Math.sqrt(distSq)) * force;
        const fy = (dy / Math.sqrt(distSq)) * force;
        a.vx -= fx;
        a.vy -= fy;
        b.vx += fx;
        b.vy += fy;
      }
    }
    // Springs along edges
    edges.forEach((e) => {
      const ai = idx.get(e.source);
      const bi = idx.get(e.target);
      if (ai == null || bi == null) return;
      const a = nodes[ai];
      const b = nodes[bi];
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
      const displacement = dist - REST_LEN;
      const f = SPRING * displacement * e.weight;
      a.vx += (dx / dist) * f;
      a.vy += (dy / dist) * f;
      b.vx -= (dx / dist) * f;
      b.vy -= (dy / dist) * f;
    });
    // Integrate + bounds
    nodes.forEach((n) => {
      n.vx *= DAMP;
      n.vy *= DAMP;
      n.x = Math.min(width - 20, Math.max(20, n.x + n.vx));
      n.y = Math.min(height - 20, Math.max(20, n.y + n.vy));
    });
  }
}

interface Props {
  graph: SentinelCascadeGraph | null;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export default function CascadeGraph({ graph, selectedId, onSelect }: Props) {
  const WIDTH = 560;
  const HEIGHT = 320;
  const [hoverEdge, setHoverEdge] = useState<string | null>(null);

  const positioned = useMemo(() => {
    if (!graph) return [];
    const p = project(graph.nodes, WIDTH, HEIGHT);
    runForces(p, graph.edges, WIDTH, HEIGHT);
    return p;
  }, [graph]);

  const nodeById = useMemo(
    () => new Map(positioned.map((n) => [n.id, n])),
    [positioned],
  );

  useEffect(() => {
    setHoverEdge(null);
  }, [graph]);

  if (!graph || positioned.length === 0) {
    return (
      <div className="flex h-[300px] items-center justify-center text-xs text-muted-foreground">
        No cascading hazards detected in the last 48 hours.
      </div>
    );
  }

  return (
    <div>
      <div className="mb-3 flex items-baseline justify-between">
        <p className="text-xs text-muted-foreground">
          When two hazards happen close together in space and time, they may
          cascade. Hover an edge for details, click a node to inspect.
        </p>
        <span className="font-mono text-[10px] text-muted-foreground">
          {positioned.length} events · {graph.edges.length} links
        </span>
      </div>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        preserveAspectRatio="xMidYMid meet"
        className="block h-[320px] w-full"
        role="img"
        aria-label="Cascading hazard graph"
      >
        {/* Edges */}
        <g>
          {graph.edges.map((e, i) => {
            const a = nodeById.get(e.source);
            const b = nodeById.get(e.target);
            if (!a || !b) return null;
            const key = `${e.source}->${e.target}-${i}`;
            const isHover = hoverEdge === key;
            return (
              <g key={key}>
                <line
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  stroke={isHover ? "#22d3ee" : "#475569"}
                  strokeWidth={1 + e.weight * 2.5}
                  strokeOpacity={isHover ? 0.95 : 0.45}
                  onMouseEnter={() => setHoverEdge(key)}
                  onMouseLeave={() => setHoverEdge(null)}
                />
                {isHover && (
                  <text
                    x={(a.x + b.x) / 2}
                    y={(a.y + b.y) / 2 - 6}
                    textAnchor="middle"
                    fontSize={10}
                    fill="#67e8f9"
                  >
                    {e.label} · {e.distance_km}km · +{e.delta_hours.toFixed(1)}h
                  </text>
                )}
              </g>
            );
          })}
        </g>
        {/* Nodes */}
        <g>
          {positioned.map((n) => {
            const color = HAZARD_COLOR[n.hazard_type] ?? "#94a3b8";
            const isSelected = n.id === selectedId;
            return (
              <g
                key={n.id}
                transform={`translate(${n.x}, ${n.y})`}
                style={{ cursor: "pointer" }}
                onClick={() => onSelect(n.id)}
              >
                <circle
                  r={isSelected ? 11 : 7}
                  fill={color}
                  fillOpacity={isSelected ? 1 : 0.85}
                  stroke={isSelected ? "#fff" : "rgba(255,255,255,0.3)"}
                  strokeWidth={isSelected ? 2 : 1}
                />
                <circle r={isSelected ? 18 : 12} fill={color} fillOpacity={0.18} />
                {isSelected && (
                  <text y={-14} textAnchor="middle" fontSize={10} fill="#e2e8f0">
                    {n.title}
                  </text>
                )}
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}
