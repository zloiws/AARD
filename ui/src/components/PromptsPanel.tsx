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
  const [componentRole, setComponentRole] = useState<string>("");
  const [stageField, setStageField] = useState<string>("");
  const [scopeField, setScopeField] = useState<string>("global");
  const [agentIdField, setAgentIdField] = useState<string>("");
  const [experimentIdField, setExperimentIdField] = useState<string>("");

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

  async function loadAssignments(promptId: string) {
    try {
      const res = await fetch(`/api/prompts/${promptId}/assignments`);
      if (!res.ok) throw new Error(`Failed to load assignments: ${res.status}`);
      const data = await res.json();
      // expect array of assignments
      setAssignments(data);
    } catch (e) {
      console.error("Failed to load assignments", e);
    }
  }

  const [assignments, setAssignments] = useState<any[]>([]);

  async function assignPrompt(promptId: string) {
    setAssigning(true);
    try {
      if (!componentRole || !stageField) {
        alert("Please provide component role and stage before assigning.");
        setAssigning(false);
        return;
      }
      const payload = {
        model_id: selection.serverId ? null : null, // placeholder: leave server/model selection to user for now
        server_id: selection.serverId,
        task_type: taskType || null,
        component_role: componentRole || null,
        stage: stageField || null,
        scope: scopeField || null,
        agent_id: agentIdField || null,
        experiment_id: experimentIdField || null
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
      // refresh assignments
      await loadAssignments(promptId);
      alert("Assigned");
    } catch (e: any) {
      console.error("Assign failed", e);
      alert("Assign failed: " + String(e));
    } finally {
      setAssigning(false);
    }
  }

  async function unassignAssignment(assignmentId: string) {
    try {
      const res = await fetch(`/api/prompts/assignments/${assignmentId}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to unassign");
      // refresh
      if (selected) await loadAssignments(selected);
      alert("Unassigned");
    } catch (e) {
      console.error("Failed to unassign", e);
      alert("Unassign failed");
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
                <h5>Assignments</h5>
                <div style={{ fontSize: 12, color: "#9ca3af", marginBottom: 8 }}>Inline editing of prompt content is disabled by policy. Create new versions or assign existing versions only.</div>
                {assignments.length === 0 ? <div style={{ color: "#9ca3af" }}>No assignments</div> : null}
                {assignments.map((a) => (
                  <div key={a.id} style={{ padding: 8, borderBottom: "1px solid #eef2f7", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div>
                      <div style={{ fontWeight: 600 }}>{a.component_role} / {a.stage}</div>
                      <div style={{ fontSize: 12, color: "#9ca3af" }}>{a.scope} {a.agent_id ? `— agent: ${a.agent_id}` : ""} {a.experiment_id ? `— exp: ${a.experiment_id}` : ""}</div>
                    </div>
                    <div>
                      <button onClick={() => unassignAssignment(a.id)} style={{ padding: "6px 10px" }}>Unassign</button>
                    </div>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 8 }}>
                <div style={{ fontSize: 13, marginBottom: 6 }}>Assign selected prompt</div>
                <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
                  <input placeholder="task type (e.g., planning)" value={taskType} onChange={(e) => setTaskType(e.target.value)} style={{ padding: 8, flex: 1 }} />
                  <input placeholder="component role (e.g., interpretation)" value={componentRole} onChange={(e) => setComponentRole(e.target.value)} style={{ padding: 8, width: 220 }} />
                </div>
                <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
                  <input placeholder="stage (e.g., planning)" value={stageField} onChange={(e) => setStageField(e.target.value)} style={{ padding: 8, width: 220 }} />
                  <select value={scopeField} onChange={(e) => setScopeField(e.target.value)} style={{ padding: 8 }}>
                    <option value="global">global</option>
                    <option value="agent">agent</option>
                    <option value="experiment">experiment</option>
                  </select>
                  <input placeholder="agent_id (optional)" value={agentIdField} onChange={(e) => setAgentIdField(e.target.value)} style={{ padding: 8, width: 220 }} />
                </div>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <input placeholder="experiment_id (optional)" value={experimentIdField} onChange={(e) => setExperimentIdField(e.target.value)} style={{ padding: 8, width: 320 }} />
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


