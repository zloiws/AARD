import React, { useEffect, useRef, useState } from "react";

type RawNode = {
  id: string;
  label: string;
  type?: string;
  metadata?: any;
};

type RawEdge = {
  source: string;
  target: string;
  label?: string;
  reason_code?: string;
  timestamp?: string;
};

type Props = {
  width?: number;
  height?: number;
  onSelectNode?: (nodeId: string) => void;
};

type SimNode = RawNode & {
  x: number;
  y: number;
  vx: number;
  vy: number;
  fx?: number | null;
  fy?: number | null;
};

export default function GraphCanvas({ width = 800, height = 600, onSelectNode }: Props) {
  const [nodes, setNodes] = useState<SimNode[]>([]);
  const [edges, setEdges] = useState<RawEdge[]>([]);
  const animRef = useRef<number | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const draggingNodeRef = useRef<SimNode | null>(null);
  const [tx, setTx] = useState(0);
  const [ty, setTy] = useState(0);
  const [scale, setScale] = useState(1);
  const panRef = useRef<{ sx: number; sy: number } | null>(null);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const res = await fetch("/api/events/graph");
        if (!res.ok) return;
        const data = await res.json();
        if (!mounted) return;
        const rawNodes: RawNode[] = data.nodes || [];
        const rawEdges: RawEdge[] = data.edges || [];
        // initialize positions
        const simNodes: SimNode[] = rawNodes.map((n, i) => ({
          ...n,
          x: width / 2 + (Math.random() - 0.5) * 200,
          y: height / 2 + (Math.random() - 0.5) * 200,
          vx: 0,
          vy: 0,
          fx: null,
          fy: null
        }));
        setNodes(simNodes);
        setEdges(rawEdges);
      } catch (e) {
        console.warn("GraphCanvas load failed", e);
      }
    }
    load();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    // simple force simulation loop
    const tick = () => {
      setNodes((prev) => {
        if (prev.length === 0) return prev;
        const newNodes = prev.map((n) => ({ ...n }));
        const kRepel = 4000;
        const kSpring = 0.06;
        const damping = 0.85;
        // repulsion
        for (let i = 0; i < newNodes.length; i++) {
          for (let j = i + 1; j < newNodes.length; j++) {
            const a = newNodes[i];
            const b = newNodes[j];
            let dx = a.x - b.x;
            let dy = a.y - b.y;
            let dist2 = dx * dx + dy * dy + 0.01;
            const force = kRepel / dist2;
            const dist = Math.sqrt(dist2);
            dx /= dist;
            dy /= dist;
            a.vx += dx * force;
            a.vy += dy * force;
            b.vx -= dx * force;
            b.vy -= dy * force;
          }
        }
        // springs for edges
        for (const e of edges) {
          const source = newNodes.find((n) => n.id === e.source);
          const target = newNodes.find((n) => n.id === e.target);
          if (!source || !target) continue;
          let dx = target.x - source.x;
          let dy = target.y - source.y;
          const dist = Math.sqrt(dx * dx + dy * dy) + 0.01;
          const desired = 120;
          const diff = dist - desired;
          const fx = (dx / dist) * diff * kSpring;
          const fy = (dy / dist) * diff * kSpring;
          source.vx += fx;
          source.vy += fy;
          target.vx -= fx;
          target.vy -= fy;
        }
        // integrate
        for (const n of newNodes) {
          if (n.fx != null) {
            n.x = n.fx;
            n.vx = 0;
          } else {
            n.vx *= damping;
            n.x += n.vx * 0.02;
          }
          if (n.fy != null) {
            n.y = n.fy;
            n.vy = 0;
          } else {
            n.vy *= damping;
            n.y += n.vy * 0.02;
          }
          // keep in bounds
          n.x = Math.max(20, Math.min(width - 20, n.x));
          n.y = Math.max(20, Math.min(height - 20, n.y));
        }
        return newNodes;
      });
      animRef.current = requestAnimationFrame(tick);
    };
    animRef.current = requestAnimationFrame(tick);
    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [edges, width, height]);

  // mouse handlers for dragging nodes
  function onMouseDownNode(e: React.MouseEvent, nodeId: string) {
    e.stopPropagation();
    const svg = svgRef.current;
    if (!svg) return;
    const pt = svg.createSVGPoint();
    pt.x = e.clientX;
    pt.y = e.clientY;
    const cursor = pt;
    setNodes((prev) => {
      const idx = prev.findIndex((n) => n.id === nodeId);
      if (idx === -1) return prev;
      const copy = prev.map((n) => ({ ...n }));
      copy[idx].fx = cursor.x - svg.getBoundingClientRect().left;
      copy[idx].fy = cursor.y - svg.getBoundingClientRect().top;
      draggingNodeRef.current = copy[idx];
      return copy;
    });
    window.addEventListener("mousemove", onWindowMouseMove);
    window.addEventListener("mouseup", onWindowMouseUp);
  }

  // pan handlers
  function onBackgroundMouseDown(e: React.MouseEvent) {
    const svg = svgRef.current;
    if (!svg) return;
    panRef.current = { sx: e.clientX - tx, sy: e.clientY - ty };
    window.addEventListener("mousemove", onPanMove);
    window.addEventListener("mouseup", onPanUp);
  }

  function onPanMove(ev: MouseEvent) {
    if (!panRef.current) return;
    setTx(ev.clientX - panRef.current.sx);
    setTy(ev.clientY - panRef.current.sy);
  }

  function onPanUp() {
    panRef.current = null;
    window.removeEventListener("mousemove", onPanMove);
    window.removeEventListener("mouseup", onPanUp);
  }

  function onWheel(e: React.WheelEvent) {
    e.preventDefault();
    const delta = -e.deltaY;
    const factor = delta > 0 ? 1.08 : 0.92;
    setScale((s) => Math.max(0.2, Math.min(3, s * factor)));
  }

  function onWindowMouseMove(ev: MouseEvent) {
    const svg = svgRef.current;
    if (!svg) return;
    const n = draggingNodeRef.current;
    if (!n) return;
    const rect = svg.getBoundingClientRect();
    const x = ev.clientX - rect.left;
    const y = ev.clientY - rect.top;
    setNodes((prev) => prev.map((pn) => (pn.id === n.id ? { ...pn, fx: x, fy: y, x, y } : pn)));
  }

  function onWindowMouseUp() {
    const n = draggingNodeRef.current;
    if (n) {
      setNodes((prev) => prev.map((pn) => (pn.id === n.id ? { ...pn, fx: null, fy: null } : pn)));
      draggingNodeRef.current = null;
    }
    window.removeEventListener("mousemove", onWindowMouseMove);
    window.removeEventListener("mouseup", onWindowMouseUp);
  }

  function handleClickNode(nodeId: string) {
    if (onSelectNode) onSelectNode(nodeId);
    // dispatch global event for Timeline cross-highlight
    try {
      const ev = new CustomEvent("graph-node-select", { detail: { nodeId } });
      window.dispatchEvent(ev);
    } catch {}
  }

  const colorForType = (t?: string) => {
    if (!t) return "#2563eb";
    if (t.toLowerCase() === "user") return "#10b981";
    if (t.toLowerCase() === "agent") return "#8844ff";
    if (t.toLowerCase() === "tool") return "#f59e0b";
    return "#2563eb";
  };

  return (
    <div style={{ width, height, border: "1px solid #eef2f7", borderRadius: 6, background: "#fff", userSelect: "none" }}>
      <svg ref={svgRef} width={width} height={height} style={{ display: "block" }} onWheel={onWheel} onMouseDown={onBackgroundMouseDown}>
        <defs>
          <filter id="soft" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2" />
          </filter>
        </defs>
        <g transform={`translate(${tx},${ty}) scale(${scale})`}>
          {edges.map((ed, i) => {
            const s = nodes.find((n) => n.id === ed.source);
            const t = nodes.find((n) => n.id === ed.target);
            if (!s || !t) return null;
            return (
              <line key={i} x1={s.x} y1={s.y} x2={t.x} y2={t.y} stroke="#e6edf8" strokeWidth={2} />
            );
          })}
        </g>
        <g transform={`translate(${tx},${ty}) scale(${scale})`}>
          {nodes.map((n) => (
            <g key={n.id} transform={`translate(${n.x},${n.y})`} style={{ cursor: "pointer" }}>
              <circle
                r={14}
                fill={colorForType(n.type)}
                stroke="#fff"
                strokeWidth={2}
                onMouseDown={(e) => onMouseDownNode(e, n.id)}
                onClick={() => handleClickNode(n.id)}
              />
              <text x={20} y={6} fontSize={12} fill="#1f2937">{n.label}</text>
            </g>
          ))}
        </g>
      </svg>
    </div>
  );
}


