import React, { useCallback, useEffect, useRef, useState } from "react";
import { useSessionContext } from "../contexts/SessionContext";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  Connection,
  Edge,
  EdgeChange,
  Node,
  NodeChange
} from "reactflow";

type BackendNode = {
  id?: string | number;
  node_id?: string | number;
  name?: string;
  label?: string;
  x?: number;
  y?: number;
  position?: { x: number; y: number };
};

type BackendEdge = {
  id?: string | number;
  source?: string | number;
  target?: string | number;
  type?: string;
};

function mapBackendNode(n: BackendNode): Node {
  const id = String(n.id ?? n.node_id ?? n.name ?? Math.random());
  const position = n.position ?? { x: n.x ?? 0, y: n.y ?? 0 };
  const label = n.label ?? n.name ?? id;
  return {
    id,
    position,
    data: { label }
  };
}

function mapBackendEdge(e: BackendEdge): Edge {
  const id = String(e.id ?? `${e.source}-${e.target}-${Math.random()}`);
  return {
    id,
    source: String(e.source),
    target: String(e.target),
    type: e.type as any
  };
}

export default function DualFlowCanvas(): JSX.Element {
  const params = new URLSearchParams(window.location.search);
  const initialSession = params.get("session_id") ?? "";
  const [localSessionId, setLocalSessionId] = useState<string>(initialSession);
  const [inputSession, setInputSession] = useState<string>(initialSession);
  // session from context (set by ChatPanel)
  const { sessionId, setSessionId } = useSessionContext();
  // allow local override if context doesn't have session
  const effectiveSessionId = sessionId ?? localSessionId;
  // Use relative API paths so Vite dev proxy forwards requests to backend
  const API_BASE = "";
  // WebSocket URL via current host + relative path (proxy will forward)
  const wsUrl = effectiveSessionId ? `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}/api/ws/ws/execution/${effectiveSessionId}` : null;

  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const [showDebug, setShowDebug] = useState<boolean>(false);
  const [sessionsList, setSessionsList] = useState<Array<{ id: string; title?: string }>>([]);
  const [selectedSession, setSelectedSession] = useState<string>(inputSession || "");
  const highlightTimers = useRef<Record<string, number>>({});

  function highlightNode(nodeId: string | number) {
    const id = String(nodeId);
    if (!id) return;
    // clear existing timer
    if (highlightTimers.current[id]) {
      clearTimeout(highlightTimers.current[id]);
      delete highlightTimers.current[id];
    }
    setNodes((nds) =>
      nds.map((n) =>
        n.id === id
          ? {
              ...n,
              style: { ...(n.style || {}), border: "2px solid #34d399", boxShadow: "0 0 8px rgba(52,211,153,0.5)" }
            }
          : n
      )
    );
    const t = window.setTimeout(() => {
      setNodes((nds) => nds.map((n) => (n.id === id ? { ...n, style: { ...(n.style || {}), border: undefined, boxShadow: undefined } } : n)));
      delete highlightTimers.current[id];
    }, 1200);
    highlightTimers.current[id] = t;
  }

  // Load graph when sessionId is set
  useEffect(() => {
    // Clear current graph whenever the effective session id changes
    setNodes([]);
    setEdges([]);
    if (!effectiveSessionId) return;
    let mounted = true;
    const url = `/api/execution/session/${effectiveSessionId}/graph_full`;
    fetch(url)
      .then((r) => {
        if (!r.ok) {
          // treat 404 or other as missing graph
          throw r;
        }
        return r.json();
      })
      .then((data) => {
        if (!mounted) return;
        const backendNodes = (data.graph && data.graph.nodes) ?? [];
        const backendEdges = (data.graph && data.graph.edges) ?? [];
        const mappedNodes = backendNodes.map(mapBackendNode);
        const mappedEdges = backendEdges.map(mapBackendEdge);
        if (mappedNodes.length === 0) {
          // fallback: build nodes from chat messages
          fetch(`/api/chat/session/${effectiveSessionId}`)
            .then((r2) => r2.ok ? r2.json() : Promise.reject(r2))
            .then((sess) => {
              const msgs = sess.messages ?? [];
              const fallbackNodes: Node[] = (msgs as any[]).map((m: any, i: number) => ({
                id: String(m.id || `msg-${i}`),
                data: { label: `${m.role === "user" ? "User" : "Assistant"}: ${String(m.content).slice(0, 120)}` },
                position: { x: 100 + (i % 3) * 220, y: 80 + Math.floor(i / 3) * 140 }
              }));
              setNodes(fallbackNodes);
              console.debug("DualFlowCanvas: fallbackNodes", fallbackNodes);
              setEdges([]);
            })
            .catch(() => {
              // no chat messages or failed - leave empty
            });
        } else {
          setNodes(mappedNodes);
          setEdges(mappedEdges);
        }
      })
      .catch((err) => {
        console.warn("Execution graph missing or failed to load; attempting fallback to chat messages", err);
        // fallback: build nodes from chat messages
        fetch(`/api/chat/session/${effectiveSessionId}`)
          .then((r2) => r2.ok ? r2.json() : Promise.reject(r2))
          .then((sess) => {
            const msgs = sess.messages ?? [];
            const fallbackNodes: Node[] = (msgs as any[]).map((m: any, i: number) => ({
              id: String(m.id || `msg-${i}`),
              data: { label: `${m.role === "user" ? "User" : "Assistant"}: ${String(m.content).slice(0, 120)}` },
              position: { x: 100 + (i % 3) * 220, y: 80 + Math.floor(i / 3) * 140 }
            }));
            setNodes(fallbackNodes);
            setEdges([]);
          })
        .catch((e) => {
            console.error("Failed to load execution graph or fallback messages:", e);
          });
      });
    return () => {
      mounted = false;
    };
  }, [API_BASE, sessionId]);

  // Fetch list of recent chat sessions for dropdown (if backend supports it)
  const fetchSessions = useCallback(() => {
    fetch("/api/chat/sessions")
      .then((r) => {
        if (!r.ok) return Promise.reject(r);
        return r.json();
      })
      .then((data) => {
        // Expecting array of sessions with id and optional title
        setSessionsList(Array.isArray(data) ? data : []);
      })
      .catch(() => {
        // ignore failure; backend may not expose sessions list
        setSessionsList([]);
      });
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  useEffect(() => {
    console.debug("DualFlowCanvas nodes updated", nodes);
  }, [nodes]);

  // WebSocket for real-time updates (backend-only events)
  useEffect(() => {
    if (!wsUrl) return;
    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      ws.onopen = () => console.log("WS connected:", wsUrl);
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          // Expecting events from backend describing graph updates
          if (msg.type === "graph_update" && msg.nodes && msg.edges) {
            setNodes((_) => (msg.nodes as BackendNode[]).map(mapBackendNode));
            setEdges((_) => (msg.edges as BackendEdge[]).map(mapBackendEdge));
            return;
          }

          if (msg.type === "node_added" && msg.node) {
            const mapped = mapBackendNode(msg.node);
            setNodes((nds) => {
              if (nds.find((n) => n.id === mapped.id)) return nds;
              const next = [...nds, mapped];
              return next;
            });
            // highlight new node
            highlightNode(msg.node.id ?? msg.node.node_id ?? msg.node.name);
            return;
          }

          if (msg.type === "edge_added" && msg.edge) {
            const mapped = mapBackendEdge(msg.edge);
            setEdges((eds) => {
              if (eds.find((e) => e.id === mapped.id)) return eds;
              const next = [...eds, mapped];
              return next;
            });
            // highlight connected nodes
            highlightNode(msg.edge.source ?? msg.edge.from_node);
            highlightNode(msg.edge.target ?? msg.edge.to_node);
            return;
          }

          if (msg.type === "node_updated" && msg.node) {
            const mapped = mapBackendNode(msg.node);
            setNodes((nds) => nds.map((n) => (n.id === mapped.id ? { ...n, data: { ...n.data, ...mapped.data }, position: mapped.position } : n)));
            highlightNode(msg.node.id ?? msg.node.node_id ?? mapped.id);
            return;
          }
        } catch (e) {
          console.error("Failed to handle WS message", e);
        }
      };
      ws.onerror = (e) => console.error("WS error", e);
      ws.onclose = () => console.log("WS closed:", wsUrl);
      return () => {
        // clear highlight timers
        Object.values(highlightTimers.current).forEach((t) => clearTimeout(t));
        highlightTimers.current = {};
        ws.close();
      };
    } catch (e) {
      console.error("Failed to create WebSocket", e);
    }
  }, [wsUrl]);

  const onNodesChange = useCallback((changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)), []);
  const onEdgesChange = useCallback((changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)), []);
  const onConnect = useCallback((connection: Connection) => setEdges((eds) => addEdge(connection, eds)), []);

  return (
    <div style={{ flex: 1, display: "flex", gap: 12 }}>
      <div style={{ flex: 1, border: "1px solid #e2e8f0", borderRadius: 8, padding: 8 }}>
        <h4>Execution Graph</h4>
        <div style={{ marginBottom: 8 }}>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <select value={selectedSession} onChange={(e) => setSelectedSession(e.target.value)} style={{ minWidth: 260 }}>
              <option value="">{sessionsList.length ? "Select session..." : "Enter session id or refresh"}</option>
              {sessionsList.map((s) => (
                <option key={s.id} value={s.id}>{s.title ? `${s.title} — ${s.id}` : s.id}</option>
              ))}
            </select>
            <input value={inputSession} onChange={(e) => { setInputSession(e.target.value); setSelectedSession(e.target.value); }} placeholder="Or paste session_id" style={{ minWidth: 220 }} />
            <button onClick={() => {
              const sid = selectedSession || inputSession;
              if (!sid) return;
              setSessionId(sid);
            }}>Load</button>
            <button onClick={() => {
              // force build from chat messages for provided session id
              const sid = selectedSession || inputSession;
              if (!sid) return;
              fetch(`/api/chat/session/${sid}`)
                .then((r) => r.ok ? r.json() : Promise.reject(r))
                .then((sess) => {
                  const msgs = sess.messages ?? [];
                  const fallbackNodes: Node[] = (msgs as any[]).map((m: any, i: number) => ({
                    id: String(m.id || `msg-${i}`),
                    data: { label: `${m.role === "user" ? "User" : "Assistant"}: ${String(m.content).slice(0, 120)}` },
                    position: { x: 100 + (i % 3) * 220, y: 80 + Math.floor(i / 3) * 140 }
                  }));
                  setNodes(fallbackNodes);
                  setEdges([]);
                })
                .catch((e) => {
                  console.warn("Failed to build fallback nodes:", e);
                });
            }}>Build from messages</button>
            <button onClick={() => setShowDebug((s) => !s)} style={{ marginLeft: 8 }}>{showDebug ? "Hide debug" : "Show debug"}</button>
            <button onClick={() => fetchSessions()} style={{ marginLeft: 8 }}>Refresh sessions</button>
            {sessionId ? <button onClick={() => { setSessionId(""); setNodes([]); setEdges([]); }} style={{ marginLeft: 8 }}>Detach</button> : null}
          </div>
          {sessionId ? <div style={{ marginTop: 6, fontSize: 13, color: "#374151" }}>Attached Session: {sessionId}</div> : null}
        </div>
        <div style={{ height: "100%", minHeight: 400 }}>
          <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={onConnect} fitView>
            <Background />
            <Controls />
            <MiniMap />
          </ReactFlow>
        </div>
      </div>

      <div style={{ width: 360, border: "1px solid #e2e8f0", borderRadius: 8, padding: 8 }}>
        <h4>Evolution Graph</h4>
        <div style={{ height: "100%", minHeight: 400 }}>
          <div style={{ padding: 12, color: "#6b7280" }}>
            Evolution graph will render here. (Will connect to `/api/meta/...` and `/ws/meta` in next step)
          </div>
        </div>
      </div>
      {showDebug ? (
        <aside style={{ position: "absolute", left: 12, top: 12, width: 480, maxHeight: "60vh", overflow: "auto", background: "rgba(255,255,255,0.95)", border: "1px solid #eee", padding: 8 }}>
          <h5>Debug: nodes / edges</h5>
          <pre style={{ fontSize: 11 }}>{JSON.stringify({ nodes, edges }, null, 2)}</pre>
        </aside>
      ) : null}
    </div>
  );
}


