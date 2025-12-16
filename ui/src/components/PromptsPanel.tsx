import React, { useEffect, useState } from "react";
import { useModelContext } from "../contexts/ModelContext";

type Prompt = {
  id: string;
  name: string;
  prompt_text: string;
  prompt_type: string;
  version: number;
};

export default function PromptsPanel(): JSX.Element {
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [versions, setVersions] = useState<Prompt[]>([]);
  const { selection } = useModelContext();
  const [assigning, setAssigning] = useState(false);
  const [taskType, setTaskType] = useState<string>("");

  useEffect(() => {
    loadPrompts();
  }, []);

  async function loadPrompts() {
    try {
      const res = await fetch("/api/prompts/");
      if (!res.ok) throw new Error(`Failed to load prompts: ${res.status}`);
      const data = await res.json();
      setPrompts(data);
    } catch (e) {
      console.error("Failed to load prompts", e);
    }
  }

  async function loadVersions(promptId: string) {
    try {
      const res = await fetch(`/api/prompts/${promptId}/versions`);
      if (!res.ok) throw new Error(`Failed to load versions: ${res.status}`);
      const data = await res.json();
      setVersions(data);
    } catch (e) {
      console.error("Failed to load versions", e);
    }
  }

  async function assignPrompt(promptId: string) {
    setAssigning(true);
    try {
      const payload = {
        model_id: selection.serverId ? null : null, // placeholder: leave server/model selection to user for now
        server_id: selection.serverId,
        task_type: taskType || null
      };
      const res = await fetch(`/api/prompts/${promptId}/assign`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(txt || res.statusText);
      }
      // refresh assignments not shown here; just feedback
      alert("Assigned");
    } catch (e: any) {
      console.error("Assign failed", e);
      alert("Assign failed: " + String(e));
    } finally {
      setAssigning(false);
    }
  }

  return (
    <div>
      <h4>Prompts</h4>
      <div style={{ display: "flex", gap: 12 }}>
        <div style={{ width: 200 }}>
          {prompts.map((p) => (
            <div key={p.id} style={{ padding: 8, borderBottom: "1px solid #eef2f7", cursor: "pointer" }} onClick={() => { setSelected(p.id); loadVersions(p.id); }}>
              <div style={{ fontWeight: 600 }}>{p.name} <small style={{ color: "#6b7280" }}>v{p.version}</small></div>
              <div style={{ fontSize: 12, color: "#9ca3af" }}>{p.prompt_type}</div>
            </div>
          ))}
        </div>
        <div style={{ flex: 1 }}>
          {selected ? (
            <>
              <h5>Versions</h5>
              {versions.map((v) => (
                <div key={v.id} style={{ border: "1px solid #eef2f7", padding: 8, borderRadius: 6, marginBottom: 8 }}>
                  <div style={{ fontWeight: 600 }}>v{v.version} — {v.name}</div>
                  <pre style={{ whiteSpace: "pre-wrap", marginTop: 6 }}>{v.prompt_text}</pre>
                </div>
              ))}
              <div style={{ marginTop: 8 }}>
                <div style={{ fontSize: 13, marginBottom: 6 }}>Assign selected prompt</div>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <input placeholder="task type (e.g., planning)" value={taskType} onChange={(e) => setTaskType(e.target.value)} style={{ padding: 8, flex: 1 }} />
                  <button onClick={() => assignPrompt(selected)} disabled={assigning}>{assigning ? "Assigning..." : "Assign"}</button>
                </div>
              </div>
            </>
          ) : <div style={{ color: "#9ca3af" }}>Select a prompt to view versions and assign</div>}
        </div>
      </div>
    </div>
  );
}


