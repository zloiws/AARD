import React, { useEffect, useState } from "react";

type EventItem = {
  id?: string;
  timestamp?: string;
  component_role?: string;
  prompt?: string;
  message?: string;
  decision_source?: string;
  prompt_id?: string;
  prompt_version?: string | number;
  input_summary?: string;
  output_summary?: string;
  reason_code?: string;
};

export default function TimelineView(): JSX.Element {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [highlightNode, setHighlightNode] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

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
      {events.map((e, i) => {
        const key = e.id ?? String(i);
        const isHighlighted = Boolean(highlightNode && (e.component_role === highlightNode || e.id === highlightNode));
        const isExpanded = Boolean(expanded[key]);
        return (
          <div
            key={key}
            style={{
              borderBottom: "1px solid #eef2f7",
              padding: 8,
              background: isHighlighted ? "#fff8e6" : "transparent",
              transition: "background 0.12s ease",
              cursor: "pointer",
            }}
            onClick={() => {
              // toggle expand and notify graph selection
              setExpanded((prev) => ({ ...prev, [key]: !prev[key] }));
              try {
                const ev = new CustomEvent("timeline-event-select", { detail: { eventId: e.id, component_role: e.component_role } });
                window.dispatchEvent(ev);
              } catch {}
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                <div style={{ fontWeight: 600 }}>{e.component_role}</div>
                {e.prompt_id ? <div style={{ fontSize: 12, color: "#9ca3af" }}>prompt: {e.prompt_id}{e.prompt_version ? `@${e.prompt_version}` : ""}</div> : null}
                {e.decision_source ? <div style={{ fontSize: 12, color: "#6b7280" }}>source: {e.decision_source}</div> : null}
              </div>
              <div style={{ color: "#9ca3af", fontSize: 12 }}>{e.timestamp}</div>
            </div>
            <div style={{ marginTop: 6, whiteSpace: "pre-wrap" }}>{e.message}</div>
            {isExpanded ? (
              <div style={{ marginTop: 8, padding: 8, background: "#f8fafc", borderRadius: 6 }}>
                {e.input_summary ? <div><strong>Input:</strong> <div style={{ whiteSpace: "pre-wrap" }}>{e.input_summary}</div></div> : null}
                {e.output_summary ? <div style={{ marginTop: 8 }}><strong>Output:</strong> <div style={{ whiteSpace: "pre-wrap" }}>{e.output_summary}</div></div> : null}
                {e.reason_code ? <div style={{ marginTop: 8, color: "#6b7280" }}><strong>Reason:</strong> {e.reason_code}</div> : null}
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}


