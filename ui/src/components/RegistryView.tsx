import React, { useEffect, useState } from "react";

type AgentInfo = {
  agent_id: string;
  role: string;
  prompt_version?: string;
  created_by?: string;
};

export default function RegistryView(): JSX.Element {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [tools, setTools] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [tab, setTab] = useState<"Agents" | "Tools" | "History">("Agents");

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch("/api/registry/agents");
        if (!res.ok) return;
        const data = await res.json();
        setAgents(data);
      } catch {
        // ignore
      }
    }
    load();
  }, []);

  return (
    <div style={{ padding: 12 }}>
      <h4>Registry</h4>
      <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
        <button onClick={() => setTab("Agents")} style={{ padding: "6px 10px", background: tab === "Agents" ? "#eef2ff" : "transparent" }}>Agents</button>
        <button onClick={() => setTab("Tools")} style={{ padding: "6px 10px", background: tab === "Tools" ? "#eef2ff" : "transparent" }}>Tools</button>
        <button onClick={() => setTab("History")} style={{ padding: "6px 10px", background: tab === "History" ? "#eef2ff" : "transparent" }}>Capabilities History</button>
      </div>

      {tab === "Agents" && (
        <>
          {agents.length === 0 ? <div style={{ color: "#9ca3af" }}>No agents</div> : null}
          {agents.map((a) => (
            <div key={a.agent_id} style={{ borderBottom: "1px solid #eef2f7", padding: 8 }}>
              <div style={{ fontWeight: 600 }}>{a.role}</div>
              <div style={{ color: "#9ca3af", fontSize: 12 }}>{a.agent_id}</div>
              <div style={{ marginTop: 6, color: "#6b7280", fontSize: 12 }}>v{a.prompt_version ?? "?"} — created by {a.created_by ?? "?"}</div>
              <div style={{ marginTop: 8 }}>
                <button style={{ padding: "6px 10px", marginRight: 8 }} disabled>Propose Update</button>
                <button style={{ padding: "6px 10px" }} disabled>Deprecate</button>
                <div style={{ fontSize: 12, color: "#9ca3af", marginTop: 6 }}>Read-only view — propose/deperecate actions require backend confirmation via Registry API.</div>
              </div>
            </div>
          ))}
        </>
      )}

      {tab === "Tools" && (
        <>
          {tools.length === 0 ? <div style={{ color: "#9ca3af" }}>No tools</div> : null}
          {tools.map((t, i) => (
            <div key={i} style={{ borderBottom: "1px solid #eef2f7", padding: 8 }}>
              <div style={{ fontWeight: 600 }}>{t.name ?? "tool"}</div>
              <div style={{ color: "#9ca3af", fontSize: 12 }}>{t.id ?? "—"}</div>
            </div>
          ))}
        </>
      )}

      {tab === "History" && (
        <>
          {history.length === 0 ? <div style={{ color: "#9ca3af" }}>No history</div> : null}
          {history.map((h, i) => (
            <div key={i} style={{ borderBottom: "1px solid #eef2f7", padding: 8 }}>
              <div style={{ fontWeight: 600 }}>{h.name ?? "capability"}</div>
              <div style={{ color: "#9ca3af", fontSize: 12 }}>{h.id ?? "—"}</div>
              <div style={{ marginTop: 6, color: "#6b7280", fontSize: 12 }}>{h.note ?? ""}</div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}


