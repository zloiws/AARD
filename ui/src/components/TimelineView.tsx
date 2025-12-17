import React, { useEffect, useState } from "react";

type EventItem = {
  id?: string;
  timestamp?: string;
  component_role?: string;
  prompt?: string;
  message?: string;
  decision_source?: string;
};

export default function TimelineView(): JSX.Element {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [highlightNode, setHighlightNode] = useState<string | null>(null);

  useEffect(() => {
    // fetch recent events (mock for now)
    async function load() {
      try {
        const res = await fetch("/api/events/recent");
        if (!res.ok) return;
        const data = await res.json();
        setEvents(data);
      } catch {
        // ignore
      }
    }
    load();
  }, []);

  useEffect(() => {
    function onGraphSelect(e: Event) {
      try {
        // @ts-ignore
        const nodeId = (e as CustomEvent).detail.nodeId;
        if (!nodeId) return;
        setHighlightNode(nodeId);
        // clear highlight after 6s
        window.setTimeout(() => setHighlightNode(null), 6000);
      } catch {}
    }
    window.addEventListener("graph-node-select", onGraphSelect as EventListener);
    return () => window.removeEventListener("graph-node-select", onGraphSelect as EventListener);
  }, []);

  return (
    <div style={{ padding: 12 }}>
      <h4>Timeline</h4>
      {events.length === 0 ? <div style={{ color: "#9ca3af" }}>No events</div> : null}
      {events.map((e, i) => (
        <div
          key={e.id ?? i}
          style={{
            borderBottom: "1px solid #eef2f7",
            padding: 8,
            background: highlightNode && (e.component_role === highlightNode || e.id === highlightNode) ? "#fff8e6" : "transparent",
            transition: "background 0.12s ease"
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <div style={{ fontWeight: 600 }}>{e.component_role}</div>
            <div style={{ color: "#9ca3af", fontSize: 12 }}>{e.timestamp}</div>
          </div>
          <div style={{ marginTop: 6, whiteSpace: "pre-wrap" }}>{e.message}</div>
          <div style={{ marginTop: 6, color: "#6b7280", fontSize: 12 }}>
            {e.prompt ? <span><strong>prompt:</strong> {e.prompt} </span> : null}
            {e.decision_source ? <span style={{ marginLeft: 12 }}><strong>decision:</strong> {e.decision_source}</span> : null}
          </div>
        </div>
      ))}
    </div>
  );
}


