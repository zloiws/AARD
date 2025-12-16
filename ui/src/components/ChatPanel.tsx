import React, { useEffect, useState } from "react";
import { useSessionContext } from "../contexts/SessionContext";

type Message = {
  id?: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp?: string;
};

// Use relative paths so Vite dev-server proxy (if enabled) forwards requests to backend
const API_BASE = "";

export default function ChatPanel(): JSX.Element {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const { sessionId, setSessionId } = useSessionContext();
  const [error, setError] = useState<string | null>(null);
  const [streamMode, setStreamMode] = useState<boolean>(false);
  const [streamInProgress, setStreamInProgress] = useState<boolean>(false);
  const [clarificationQuestions, setClarificationQuestions] = useState<string[]>([]);
  const [planId, setPlanId] = useState<string | null>(null);
  const [planStatus, setPlanStatus] = useState<string | null>(null);
  const [userRole, setUserRole] = useState<string | null>(null);
  const readerRef = React.useRef<any>(null);
  const controllerRef = React.useRef<AbortController | null>(null);
  const containerRef = React.useRef<HTMLDivElement | null>(null);
  // Read selected model/server from context
  const { selection } = (() => {
    try {
      // lazy require to avoid circular import in tests
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      const ctx = require("../contexts/ModelContext");
      const useModelContext = ctx.useModelContext;
      return useModelContext();
    } catch {
      return { selection: { serverId: null, modelName: null } };
    }
  })();

  useEffect(() => {
    // If sessionId exists, load messages
    if (!sessionId) return;
    fetch(`/api/chat/session/${sessionId}`)
      .then((r) => {
        if (!r.ok) throw new Error(`Failed to load session: ${r.status}`);
        return r.json();
      })
      .then((data) => {
        const msgs = (data.messages ?? []).map((m: any) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          timestamp: m.timestamp
        }));
        setMessages(msgs);
      })
      .catch((e) => {
        console.error("Failed to load chat session", e);
      });
  }, [sessionId]);

  async function sendMessage(overrideText?: string) {
    if (!input.trim()) return;
    setSending(true);
    setError(null);

    const textToSend = overrideText !== undefined ? overrideText : input;
    if (!textToSend || !textToSend.trim()) {
      setSending(false);
      return;
    }

    // Optimistic UI: add user message immediately
    const userMsg: Message = { role: "user", content: textToSend };
    setMessages((m) => [...m, userMsg]);
    const payload: any = {
      message: textToSend,
      stream: false,
      session_id: sessionId
    };
    if (selection && selection.modelName) {
      payload.model = selection.modelName;
    }
    if (selection && selection.serverId) {
      payload.server_id = selection.serverId;
    }

    try {
      payload.stream = streamMode;

      if (!streamMode) {
        const res = await fetch(`/api/chat/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        if (!res.ok) {
          const text = await res.text().catch(() => "");
          throw new Error(`API error ${res.status}: ${text || res.statusText}`);
        }
        const data = await res.json();
        // Server returns ChatResponse with response, session_id and optional metadata
        const assistant: Message = { role: "assistant", content: data.response, timestamp: new Date().toISOString() };
        setMessages((m) => [...m.filter((x) => x !== userMsg), userMsg, assistant]);
        if (data.session_id) setSessionId(data.session_id);
        // Handle clarification questions if provided by server
        if (data.metadata && data.metadata.clarification_required) {
          const qs = data.metadata.questions || data.metadata.clarification_questions || [];
          setClarificationQuestions(Array.isArray(qs) ? qs : [String(qs)]);
        } else {
          setClarificationQuestions([]);
        }
        // If server attached a plan_id, fetch plan status
        if (data.metadata && data.metadata.plan_id) {
          setPlanId(String(data.metadata.plan_id));
          fetchPlanStatus(String(data.metadata.plan_id));
        }
      } else {
        setStreamInProgress(true);
        controllerRef.current = new AbortController();
        const res = await fetch(`/api/chat/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          signal: controllerRef.current.signal
        });
        if (!res.ok) {
          const text = await res.text().catch(() => "");
          setStreamInProgress(false);
          throw new Error(`API error ${res.status}: ${text || res.statusText}`);
        }

        // add assistant placeholder
        let assistantIndex = -1;
        setMessages((prev) => {
          assistantIndex = prev.length;
          return [...prev, { role: "assistant", content: "" }];
        });

        const reader = res.body?.getReader();
        readerRef.current = reader;
        if (!reader) {
          setStreamInProgress(false);
          throw new Error("Streaming not supported by response");
        }
        const decoder = new TextDecoder();
        let buffer = "";
        let streamDone = false;
        while (!streamDone) {
          const { value, done: readerDone } = await reader.read();
          if (value) {
            buffer += decoder.decode(value, { stream: true });
            const parts = buffer.split("\n\n");
            buffer = parts.pop() || "";
            for (const part of parts) {
              const line = part.trim();
              if (!line) continue;
              const dataLine = line.startsWith("data:") ? line.replace(/^data:\s*/, "") : line;
              try {
                const json = JSON.parse(dataLine);
                const chunkContent = json.content ?? json.response ?? "";
                const isDone = json.done === true;
                setMessages((prev) => {
                  const next = [...prev];
                  const existing = next[assistantIndex] || { role: "assistant", content: "" };
                  existing.content = (existing.content || "") + chunkContent;
                  existing.timestamp = new Date().toISOString();
                  next[assistantIndex] = existing;
                  return next;
                });
                if (json.session_id) setSessionId(json.session_id);
                if (isDone) streamDone = true;
              } catch (e) {
                // ignore parse errors
              }
            }
          }
          if (readerDone) break;
        }
        if (buffer.trim()) {
          try {
            const json = JSON.parse(buffer.trim().replace(/^data:\s*/, ""));
            const chunkContent = json.content ?? json.response ?? "";
            setMessages((prev) => {
              const next = [...prev];
              const existing = next[assistantIndex] || { role: "assistant", content: "" };
              existing.content = (existing.content || "") + chunkContent;
              existing.timestamp = new Date().toISOString();
              next[assistantIndex] = existing;
              return next;
            });
            if (json.session_id) setSessionId(json.session_id);
          } catch {}
        }
        // cleanup
        readerRef.current = null;
        controllerRef.current = null;
        setStreamInProgress(false);
      }
    } catch (e: any) {
      console.error("Chat send failed", e);
      setError(e.message || String(e));
      // Remove optimistic user message if failed
      setMessages((m) => m.filter((x) => x !== userMsg));
    } finally {
      setInput("");
      setSending(false);
    }
  }

  async function closeSessionOnServer(id: string | null) {
    if (!id) return;
    try {
      await fetch(`/api/chat/session/${id}`, { method: "DELETE" });
    } catch (e) {
      console.warn("Failed to close session on server", e);
    }
  }

  async function fetchPlanStatus(id: string) {
    try {
      const r = await fetch(`/api/plans/${id}`);
      if (!r.ok) {
        setPlanStatus(null);
        return;
      }
      const p = await r.json();
      setPlanStatus(p.status || null);
    } catch (e) {
      console.warn("Failed to fetch plan status", e);
      setPlanStatus(null);
    }
  }

  // Poll plan status every 5s while a plan is active
  useEffect(() => {
    if (!planId) return;
    const t = setInterval(() => {
      fetchPlanStatus(planId);
    }, 5000);
    // initial fetch
    fetchPlanStatus(planId);
    return () => clearInterval(t);
  }, [planId]);

  // Fetch current user info to decide about showing Approve button
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const r = await fetch("/api/auth/me");
        if (!r.ok) return;
        const u = await r.json();
        if (mounted) setUserRole(u.role || null);
      } catch {}
    })();
    return () => {
      mounted = false;
    };
  }, []);

  // WebSocket for execution / workflow events (subscribe per sessionId)
  useEffect(() => {
    if (!sessionId) return;
    let ws: WebSocket | null = null;
    let reconnectTimeout: number | null = null;

    const connect = () => {
      try {
        const protocol = window.location.protocol === "https:" ? "wss" : "ws";
        const host = window.location.hostname || "localhost";
        const port = 8000; // backend API port
        const wsUrl = `${protocol}://${host}:${port}/api/ws/ws/execution/${sessionId}`;
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          console.debug("WS connected to", wsUrl);
        };

        ws.onmessage = (ev) => {
          try {
            const msg = JSON.parse(ev.data);
            // Handle execution events
            if (msg?.type === "execution_event" || msg?.type === "event") {
              const data = msg.data || msg?.data || {};
              // If event contains a plan_id/status, update plan status
              const pId = data.plan_id || data.planId || data.get?.("plan_id");
              const status = data.status || data.plan_status || data.state;
              if (pId && planId && String(pId) === String(planId) && status) {
                setPlanStatus(status);
              } else {
                // fallback: refresh plan status if any execution event touches this session
                fetchPlanStatus(planId);
              }
            } else if (msg?.type === "connected") {
              // ignore
            } else if (msg?.type === "chat_event") {
              // Optionally handle chat events
            }
          } catch (e) {
            console.warn("WS message parse error", e);
          }
        };

        ws.onclose = (ev) => {
          console.debug("WS closed", ev.code, ev.reason);
          // Attempt reconnect
          if (reconnectTimeout) window.clearTimeout(reconnectTimeout);
          reconnectTimeout = window.setTimeout(connect, 2000);
        };

        ws.onerror = (e) => {
          console.warn("WS error", e);
          try {
            ws?.close();
          } catch {}
        };
      } catch (e) {
        console.warn("WS connect failed", e);
        reconnectTimeout = window.setTimeout(connect, 2000);
      }
    };

    connect();

    return () => {
      try {
        if (ws && ws.readyState === WebSocket.OPEN) ws.close();
      } catch {}
      if (reconnectTimeout) window.clearTimeout(reconnectTimeout);
    };
  }, [sessionId, planId]);

  async function approvePlan(id: string) {
    try {
      const r = await fetch(`/api/plans/${id}/approve`, { method: "POST" });
      if (!r.ok) {
        throw new Error(`Failed to approve: ${r.status}`);
      }
      const p = await r.json();
      setPlanStatus(p.status || null);
    } catch (e) {
      console.warn("Approve failed", e);
    }
  }

  // auto-scroll to bottom when messages change or during streaming
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    // small timeout to allow DOM update
    const t = setTimeout(() => {
      try {
        el.scrollTop = el.scrollHeight;
      } catch {}
    }, 20);
    return () => clearTimeout(t);
  }, [messages, streamInProgress]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ paddingBottom: 8, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
        <div>
          <strong>Chat</strong>
          <div style={{ fontSize: 12, color: "#6b7280" }}>{sessionId ? `Session: ${sessionId}` : "No session yet — messages will create one"}</div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <input type="checkbox" checked={streamMode} onChange={(e) => setStreamMode(e.target.checked)} /> Stream
          </label>
          {/* Dev debug toggle to force admin role for testing Approve button */}
          <label style={{ display: "flex", alignItems: "center", gap: 6, marginLeft: 8, fontSize: 12 }}>
            <input
              type="checkbox"
              checked={Boolean(localStorage.getItem("aard_debug_admin"))}
              onChange={(e) => {
                try {
                  if (e.target.checked) {
                    localStorage.setItem("aard_debug_admin", "1");
                    setUserRole("admin");
                  } else {
                    localStorage.removeItem("aard_debug_admin");
                    // revert to server-provided role by refetching
                    setUserRole(null);
                    fetch("/api/auth/me")
                      .then((r) => (r.ok ? r.json() : null))
                      .then((u) => {
                        if (u && u.role) setUserRole(u.role);
                      })
                      .catch(() => {});
                  }
                } catch {}
              }}
              title="Force admin role locally (debug)"
            />{" "}
            DebugAdmin
          </label>
        </div>
      </div>

      <div ref={(el) => (containerRef.current = el)} style={{ flex: 1, overflow: "auto", padding: 8, border: "1px solid #e6e9ef", borderRadius: 8, background: "#fff" }}>
        {messages.length === 0 ? <div style={{ color: "#6b7280" }}>No messages yet</div> : null}
        {messages.map((m, idx) => (
          <div key={idx} style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 12, color: "#374151", fontWeight: 600 }}>{m.role === "user" ? "You" : m.role === "assistant" ? "Assistant" : "System"}</div>
            <div style={{ whiteSpace: "pre-wrap", marginTop: 4 }}>{m.content}</div>
            {m.timestamp ? <div style={{ fontSize: 11, color: "#9ca3af" }}>{m.timestamp}</div> : null}
          </div>
        ))}
        {streamInProgress ? <div style={{ fontStyle: "italic", color: "#6b7280" }}>Assistant is typing...</div> : null}
      </div>

      {/* Clarification UI */}
      {clarificationQuestions.length > 0 ? (
        <div style={{ padding: 8, borderTop: "1px dashed #e6e9ef", background: "#fff9f0" }}>
          <div style={{ fontWeight: 700, marginBottom: 6 }}>Clarification required</div>
          {clarificationQuestions.map((q, i) => (
            <div key={i} style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 13 }}>{q}</div>
              <div style={{ marginTop: 6, display: "flex", gap: 8 }}>
                <button
                  onClick={() => {
                    // send answer immediately using override
                    sendMessage(q);
                  }}
                >
                  Answer
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {/* Plan status panel */}
      {planId ? (
        <div style={{ paddingTop: 8 }}>
          <div style={{ fontSize: 13, fontWeight: 700 }}>Plan</div>
          <div style={{ fontSize: 13 }}>ID: {planId}</div>
          <div style={{ fontSize: 13 }}>Status: {planStatus ?? "loading..."}</div>
          <div style={{ marginTop: 6 }}>
            <button onClick={() => fetchPlanStatus(planId)}>Refresh</button>
            {userRole === "admin" ? (
              <button onClick={() => approvePlan(planId)} style={{ marginLeft: 8 }}>
                Approve
              </button>
            ) : (
              <button disabled style={{ marginLeft: 8 }} title="Requires admin">
                Approve
              </button>
            )}
          </div>
        </div>
      ) : null}

      {/* Debug admin: allow entering a plan id to approve when no planId exists */}
      {!planId && Boolean(localStorage.getItem("aard_debug_admin")) ? (
        <div style={{ paddingTop: 8 }}>
          <div style={{ fontSize: 13, fontWeight: 700 }}>Dev Approve (debug)</div>
          <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
            <input
              placeholder="Paste plan id..."
              style={{ flex: 1, padding: 8, borderRadius: 6, border: "1px solid #d1d5db" }}
              onChange={(e) => {
                try {
                  setPlanId(e.target.value || null);
                } catch {}
              }}
            />
            <button
              onClick={async () => {
                if (!planId) return;
                await approvePlan(planId);
              }}
            >
              Approve
            </button>
          </div>
        </div>
      ) : null}

      <div style={{ marginTop: 8, display: "flex", gap: 8, alignItems: "center" }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              sendMessage();
            }
          }}
          placeholder="Type a message..."
          style={{ flex: 1, padding: 8, borderRadius: 6, border: "1px solid #d1d5db" }}
          disabled={sending}
        />
        <button onClick={sendMessage} disabled={sending || !input.trim()} style={{ padding: "8px 12px", borderRadius: 6 }}>
          Send
        </button>
        {streamInProgress ? (
          <button
            onClick={() => {
              try {
                controllerRef.current?.abort();
                if (readerRef.current && typeof readerRef.current.cancel === "function") {
                  readerRef.current.cancel();
                }
              } catch (e) {
                console.warn("Cancel failed", e);
              } finally {
                readerRef.current = null;
                controllerRef.current = null;
                setStreamInProgress(false);
              }
            }}
            style={{ padding: "8px 12px", borderRadius: 6, background: "#f97316", color: "white" }}
          >
            Cancel
          </button>
        ) : null}
        <button
          onClick={async () => {
            // close old session on server if exists
            if (sessionId) {
              await closeSessionOnServer(sessionId);
            }
            setSessionId(null);
            setMessages([]);
          }}
          title="New session"
        >
          New
        </button>
      </div>

      {error ? <div style={{ color: "red", marginTop: 8 }}>{error}</div> : null}
    </div>
  );
}


