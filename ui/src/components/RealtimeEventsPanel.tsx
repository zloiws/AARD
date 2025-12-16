import React, { useEffect, useRef, useState } from "react";
import { useSessionContext } from "../contexts/SessionContext";

type EventItem = {
  id?: string;
  type?: string;
  timestamp?: string;
  message?: string;
  data?: any;
};

export default function RealtimeEventsPanel(): JSX.Element {
  const [events, setEvents] = useState<EventItem[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const [collapsed, setCollapsed] = useState<boolean>(true);
  const { sessionId } = (() => {
    try {
      // lazy load to avoid circular HMR issues
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      const ctx = require("../contexts/SessionContext");
      return ctx.useSessionContext();
    } catch {
      return { sessionId: null, setSessionId: () => {} };
    }
  })();

  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    // If session exists, subscribe to execution workflow for that session
    const workflowPath = sessionId ? `/api/ws/events/execution:${sessionId}` : `/api/ws/events`;
    const wsUrl = `${protocol}//${host}${workflowPath}`;
    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      ws.onopen = () => console.log("RealtimeEvents WS connected", wsUrl);
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          const item: EventItem = {
            id: msg.id ?? msg.event_id ?? undefined,
            type: msg.type ?? msg.event_type ?? "event",
            timestamp: msg.timestamp ?? new Date().toISOString(),
            message: msg.message ?? JSON.stringify(msg.data ?? msg),
            data: msg.data ?? msg
          };
          setEvents((prev) => [item, ...prev].slice(0, 200));
        } catch (e) {
          console.warn("Failed to parse event", e);
        }
      };
      ws.onerror = (e) => console.error("RealtimeEvents WS error", e);
      ws.onclose = () => console.log("RealtimeEvents WS closed");
      return () => {
        ws.close();
      };
    } catch (e) {
      console.error("Failed to create RealtimeEvents WS", e);
    }
  }, []);

  // Increase width by 20% (420 -> 504) and provide color-coded badges per event type
  const expandedWidth = 504;
  return (
    <div style={{ position: "fixed", right: 12, bottom: 12, width: collapsed ? 160 : expandedWidth, maxHeight: "45vh", overflow: "auto", background: "white", border: "1px solid #e6e9ef", borderRadius: 8, padding: 8, boxShadow: "0 8px 24px rgba(0,0,0,0.08)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <strong>Realtime Events</strong>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <small style={{ color: "#6b7280" }}>{events.length} recent</small>
          <button onClick={() => setCollapsed((s) => !s)} style={{ fontSize: 12 }}>
            {collapsed ? "Expand" : "Collapse"}
          </button>
        </div>
      </div>
      {!collapsed ? (
        <div>
          {events.map((e, i) => {
            const type = (e.type || "").toLowerCase();
            const colorMap: Record<string, string> = {
              execution_event: "#2563eb",
              execution: "#2563eb",
              chat_event: "#059669",
              chat: "#059669",
              error: "#dc2626",
              event: "#6b7280"
            };
            const badgeColor = colorMap[type] || "#6b7280";
            return (
              <div key={e.id ?? i} style={{ borderTop: i === 0 ? "none" : "1px solid #f1f5f9", paddingTop: 8, paddingBottom: 8, display: "flex", gap: 10, alignItems: "flex-start" }}>
                <div style={{ width: 8, height: 32, borderRadius: 4, background: badgeColor, flex: "0 0 auto" }} />
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: badgeColor }}>{e.type}</div>
                    <div style={{ fontSize: 11, color: "#9ca3af" }}>{e.timestamp}</div>
                  </div>
                  <div style={{ fontSize: 12, color: "#374151", whiteSpace: "pre-wrap", marginTop: 6 }}>{e.message}</div>
                </div>
              </div>
            );
          })}
          {events.length === 0 ? <div style={{ color: "#9ca3af" }}>No events yet</div> : null}
        </div>
      ) : (
        <div style={{ fontSize: 12, color: "#6b7280" }}>Collapsed — expand to view events</div>
      )}
    </div>
  );
}


