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

  return (
    <div style={{ position: "fixed", right: 12, bottom: 12, width: 420, maxHeight: "45vh", overflow: "auto", background: "white", border: "1px solid #e6e9ef", borderRadius: 8, padding: 8, boxShadow: "0 8px 24px rgba(0,0,0,0.08)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <strong>Realtime Events</strong>
        <small style={{ color: "#6b7280" }}>{events.length} recent</small>
      </div>
      <div>
        {events.map((e, i) => (
          <div key={e.id ?? i} style={{ borderTop: i === 0 ? "none" : "1px solid #f1f5f9", paddingTop: 8, paddingBottom: 8 }}>
            <div style={{ fontSize: 12, fontWeight: 600 }}>{e.type}</div>
            <div style={{ fontSize: 12, color: "#374151", whiteSpace: "pre-wrap" }}>{e.message}</div>
            <div style={{ fontSize: 11, color: "#9ca3af" }}>{e.timestamp}</div>
          </div>
        ))}
        {events.length === 0 ? <div style={{ color: "#9ca3af" }}>No events yet</div> : null}
      </div>
    </div>
  );
}


