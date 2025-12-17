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
        // Server may attach metadata; Chat UI intentionally does not display plan lifecycle UI.
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

  // Plan lifecycle and approval UI are intentionally not part of Chat per UI spec.

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

  // Chat UI is a black box; execution observability is handled in Timeline/Graph per UI spec.


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
          {/* debug controls removed per UI spec */}
        </div>
      </div>

      <div ref={(el) => (containerRef.current = el)} style={{ flex: 1, overflow: "auto", padding: 8, border: "1px solid #e6e9ef", borderRadius: 8, background: "#fff" }}>
        {messages.length === 0 ? <div style={{ color: "#6b7280" }}>No messages yet</div> : null}
        {messages.map((m, idx) => (
          <div key={idx} style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 12, color: "#374151", fontWeight: 600 }}>
              {m.role === "user" ? "User" : m.role === "system" ? "System" : "Result"}
            </div>
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

      {/* Plan lifecycle handled in Timeline/Plan UI per spec; Chat does not display plan controls */}

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


