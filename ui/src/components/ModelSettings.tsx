import React, { useEffect, useState } from "react";
import { useModelContext } from "../contexts/ModelContext";

type Server = {
  id: string;
  name: string;
  url: string;
  is_default: boolean;
  models_count: number;
};

type Model = {
  id: string;
  name: string;
  model_name: string;
  capabilities?: string[];
};

export default function ModelSettings(): JSX.Element {
  const { selection, setSelection } = useModelContext();
  const [servers, setServers] = useState<Server[]>([]);
  const [models, setModels] = useState<Model[]>([]);
  const [loadingServers, setLoadingServers] = useState(false);
  const [loadingModels, setLoadingModels] = useState(false);
  const [modelsVisible, setModelsVisible] = useState(false);
  const [editingModel, setEditingModel] = useState<Record<string, any>>({});
  const [checkingAvailability, setCheckingAvailability] = useState<Record<string, boolean>>({});
  const [editingServer, setEditingServer] = useState<Record<string, any>>({});
  const [newServerName, setNewServerName] = useState("");
  const [newServerUrl, setNewServerUrl] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadServers();
  }, []);

  useEffect(() => {
    if (!selection.serverId) {
      setModels([]);
      return;
    }
    loadModels(selection.serverId);
  }, [selection.serverId]);

  async function loadServers() {
    setLoadingServers(true);
    try {
      const res = await fetch("/api/servers/");
      if (!res.ok) throw new Error(`Failed to load servers: ${res.status}`);
      const data = await res.json();
      setServers(data);
      // If no selection, try to pick default server
      if (!selection.serverId && data.length > 0) {
        const def = data.find((s: any) => s.is_default) ?? data[0];
        setSelection({ serverId: def.id, modelName: null });
      }
    } catch (e: any) {
      console.error("Failed to load servers", e);
      // Provide a clearer diagnostic for network errors
      if (e && e.message && e.message.includes("Failed to fetch")) {
        setError("Failed to fetch /api/servers — backend may be unreachable or proxy misconfigured. Check that backend is running on http://localhost:8000 and Vite proxy is active.");
      } else {
        setError(String(e));
      }
    } finally {
      setLoadingServers(false);
    }
  }

  async function loadModels(serverId: string) {
    setLoadingModels(true);
    try {
      const res = await fetch(`/api/servers/${serverId}/models`);
      if (!res.ok) throw new Error(`Failed to load models: ${res.status}`);
      const data = await res.json();
      setModels(data);
      if (data.length > 0 && !selection.modelName) {
        setSelection({ serverId, modelName: data[0].model_name });
      }
      setModelsVisible(true);
    } catch (e: any) {
      console.error("Failed to load models", e);
      setError(String(e));
      setModels([]);
    } finally {
      setLoadingModels(false);
    }
  }

  async function createServer() {
    setError(null);
    if (!newServerName.trim() || !newServerUrl.trim()) {
      setError("Provide name and URL");
      return;
    }
    // Quick connectivity check before attempting POST to provide better error messages
    try {
      const ping = await fetch("/api/servers/", { method: "GET" });
      if (!ping.ok) {
        const text = await ping.text().catch(() => "");
        throw new Error(`Ping failed: ${ping.status} ${text || ping.statusText}`);
      }
    } catch (connectErr: any) {
      console.error("Connectivity check failed", connectErr);
      setError(
        connectErr && connectErr.message && connectErr.message.includes("Failed to fetch")
          ? "Cannot reach backend (/api). Ensure backend is running and VITE dev proxy is enabled."
          : String(connectErr)
      );
      return;
    }
    try {
      const payload = {
        name: newServerName.trim(),
        url: newServerUrl.trim(),
        api_version: "v1",
        is_default: false
      };
      const res = await fetch("/api/servers/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(`Server returned ${res.status}: ${txt || res.statusText}`);
      }
      const created = await res.json();
      setNewServerName("");
      setNewServerUrl("");
      await loadServers();
      // Try discovering models for created server
      try {
        await fetch(`/api/servers/${created.id}/discover`, { method: "POST" });
        // After discovery, load models and show them
        await loadModels(created.id);
      } catch {}
    } catch (e: any) {
      console.error("Create server failed", e);
      if (e && e.message && e.message.includes("Failed to fetch")) {
        setError("Network error: failed to reach backend when creating server. Ensure backend is reachable from UI (proxy) and try again.");
      } else {
        setError(String(e));
      }
    }
  }

  // Update model config (capabilities/is_active/priority/name)
  async function saveModelConfig(modelId: string) {
    const payload = editingModel[modelId] || {};
    try {
      const res = await fetch(`/api/models/${modelId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(txt || res.statusText);
      }
      // refresh models list
      if (selection.serverId) await loadModels(selection.serverId);
      setEditingModel((s) => {
        const next = { ...s };
        delete next[modelId];
        return next;
      });
    } catch (e: any) {
      setError(String(e));
    }
  }

  async function checkModelAvailability(modelId: string) {
    setCheckingAvailability((s) => ({ ...s, [modelId]: true }));
    try {
      const res = await fetch(`/api/models/${modelId}/check-availability`, { method: "POST" });
      const data = await res.json();
      // show result briefly in UI via error field (could be improved)
      if (data.is_available) {
        setError(`Model ${data.model_name} is available on ${data.server_url}`);
      } else {
        setError(`Model ${data.model_name} is NOT available: ${data.error ?? "not loaded"}`);
      }
    } catch (e: any) {
      setError(String(e));
    } finally {
      setCheckingAvailability((s) => ({ ...s, [modelId]: false }));
    }
  }

  async function refreshModelsFromServer(serverId: string) {
    try {
      setLoadingModels(true);
      const res = await fetch(`/api/servers/${serverId}/discover`, { method: "POST" });
      if (!res.ok) {
        // try to parse JSON error
        let body = "";
        try {
          const json = await res.json();
          body = json.detail ?? JSON.stringify(json);
        } catch {
          body = await res.text().catch(() => res.statusText);
        }
        // provide actionable suggestion for common discover error
        const suggestion = body && body.toLowerCase().includes("all connection attempts failed")
          ? "Connection attempts to the Ollama server failed — check the server URL, network, and that Ollama is running."
          : "";
        throw new Error((body ? body + ". " : "") + suggestion || `HTTP ${res.status}`);
      }
      // reload models from DB
      await loadModels(serverId);
    } catch (e: any) {
      console.error("Refresh models failed", e);
      setError(e && e.message ? `Error: ${e.message}` : String(e));
    } finally {
      setLoadingModels(false);
    }
  }

  async function deleteServer(serverId: string) {
    try {
      const res = await fetch(`/api/servers/${serverId}`, { method: "DELETE" });
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(txt || res.statusText);
      }
      // reload servers and clear selection
      await loadServers();
      setSelection({ serverId: null, modelName: null });
      setModels([]);
      setModelsVisible(false);
    } catch (e: any) {
      console.error("Delete server failed", e);
      setError(e && e.message ? String(e.message) : String(e));
    }
  }

  return (
    <div style={{ padding: 12 }}>
      <h4>Model Settings</h4>

      <div style={{ marginBottom: 8 }}>
        <div style={{ fontSize: 13, color: "#6b7280" }}>Server</div>
        {loadingServers ? (
          <div>Loading servers...</div>
        ) : (
          <select
            value={selection.serverId ?? ""}
            onChange={(e) => setSelection({ serverId: e.target.value || null, modelName: null })}
            style={{ width: "100%", padding: 8, marginTop: 6 }}
          >
            <option value="">— Select server —</option>
            {servers.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} {s.is_default ? "(default)" : ""} — {s.models_count} models
              </option>
            ))}
          </select>
        )}
      </div>

      <div style={{ marginBottom: 8 }}>
        <div style={{ fontSize: 13, color: "#6b7280" }}>Model</div>
        {loadingModels ? (
          <div>Loading models...</div>
        ) : models.length === 0 ? (
          <div style={{ color: "#9ca3af", marginTop: 6 }}>No models available for selected server</div>
        ) : (
          <select
            value={selection.modelName ?? ""}
            onChange={(e) => setSelection({ serverId: selection.serverId, modelName: e.target.value || null })}
            style={{ width: "100%", padding: 8, marginTop: 6 }}
          >
            <option value="">— Select model —</option>
            {models.map((m) => (
              <option key={m.id} value={m.model_name}>
                {m.name}
              </option>
            ))}
          </select>
        )}
      </div>

      <div style={{ marginTop: 12, marginBottom: 8 }}>
        <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 6 }}>Add Ollama server</div>
        <input placeholder="Display name" value={newServerName} onChange={(e) => setNewServerName(e.target.value)} style={{ width: "100%", marginBottom: 6, padding: 8 }} />
        <input placeholder="Base URL (http://...)" value={newServerUrl} onChange={(e) => setNewServerUrl(e.target.value)} style={{ width: "100%", marginBottom: 6, padding: 8 }} />
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={createServer}>Add server</button>
        </div>
      </div>

    <div style={{ marginTop: 8 }}>
      <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 6 }}>Known servers</div>
      {servers.length === 0 ? (
        <div style={{ color: "#9ca3af" }}>No servers in DB</div>
      ) : (
        servers.map((s) => {
          const isEditing = !!editingServer[s.id];
          return (
            <div key={s.id} style={{ border: "1px solid #eef2f7", padding: 8, borderRadius: 6, marginBottom: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  {!isEditing ? (
                    <>
                      <div style={{ fontWeight: 600 }}>{s.name}</div>
                      <div style={{ fontSize: 12, color: "#6b7280" }}>{s.url} — {s.models_count} models</div>
                    </>
                  ) : (
                    <>
                      <input value={editingServer[s.id].name} onChange={(e) => setEditingServer((st) => ({ ...st, [s.id]: { ...st[s.id], name: e.target.value } }))} style={{ fontWeight: 600, padding: 6 }} />
                      <input value={editingServer[s.id].url} onChange={(e) => setEditingServer((st) => ({ ...st, [s.id]: { ...st[s.id], url: e.target.value } }))} style={{ fontSize: 12, color: "#6b7280", padding: 6, marginTop: 6 }} />
                    </>
                  )}
                </div>

                <div style={{ display: "flex", gap: 8 }}>
                  {!isEditing ? <button onClick={() => { setSelection({ serverId: s.id, modelName: null }); loadModels(s.id); }}>Open</button> : null}
                  {!isEditing ? <button onClick={() => refreshModelsFromServer(s.id)}>Refresh</button> : null}
                  {!isEditing ? <button onClick={() => setEditingServer((st) => ({ ...st, [s.id]: { name: s.name, url: s.url } }))}>Edit</button> : null}
                  {isEditing ? <button onClick={async () => {
                    // Save server edits
                    try {
                      const payload = { name: editingServer[s.id].name, url: editingServer[s.id].url };
                      const res = await fetch(`/api/servers/${s.id}`, {
                        method: "PUT",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(payload)
                      });
                      if (!res.ok) {
                        const txt = await res.text().catch(() => "");
                        throw new Error(txt || res.statusText);
                      }
                      // reload servers and models
                      await loadServers();
                      if (selection.serverId === s.id) await loadModels(s.id);
                      setEditingServer((st) => { const n = { ...st }; delete n[s.id]; return n; });
                    } catch (e: any) {
                      setError(String(e));
                    }
                  }}>Save</button> : null}
                  {isEditing ? <button onClick={() => setEditingServer((st) => { const n = { ...st }; delete n[s.id]; return n; })}>Cancel</button> : null}
                  <button onClick={() => { if (!confirm(`Delete server ${s.name}?`)) return; deleteServer(s.id); }} style={{ background: "#ef4444", color: "white" }}>Delete</button>
                </div>
              </div>
            </div>
          );
        })
      )}
    </div>

      {error ? <div style={{ color: "red", marginTop: 8 }}>{error}</div> : null}
      {modelsVisible ? (
        <div style={{ marginTop: 10 }}>
          <h5>Models for selected server</h5>
          {loadingModels ? <div>Loading...</div> : null}
          {models.length === 0 ? <div style={{ color: "#9ca3af" }}>No models</div> : null}
          {models.map((m) => (
            <div key={m.id} style={{ borderTop: "1px solid #eef2f7", paddingTop: 8, marginTop: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontWeight: 600 }}>{m.name}</div>
                  <div style={{ fontSize: 12, color: "#6b7280" }}>{m.model_name}</div>
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  <button onClick={() => checkModelAvailability(m.id)} disabled={!!checkingAvailability[m.id]}>
                    {checkingAvailability[m.id] ? "Checking..." : "Check"}
                  </button>
                  <button onClick={() => setEditingModel((s) => ({ ...s, [m.id]: { name: m.name, capabilities: (m as any).capabilities ?? [], priority: (m as any).priority ?? 0, is_active: (m as any).is_active ?? true } }))}>
                    Edit
                  </button>
                </div>
              </div>
              {editingModel[m.id] ? (
                <div style={{ marginTop: 8 }}>
                  <div style={{ marginBottom: 6 }}>
                    <input
                      value={editingModel[m.id].name}
                      onChange={(e) => setEditingModel((s) => ({ ...s, [m.id]: { ...s[m.id], name: e.target.value } }))}
                      style={{ width: "100%", padding: 6 }}
                    />
                  </div>
                  <div style={{ marginBottom: 6 }}>
                    <div style={{ fontSize: 13, marginBottom: 6 }}>Capabilities</div>
                    {["chat", "coding", "reasoning", "planning", "embedding"].map((cap) => {
                      const checked = (editingModel[m.id].capabilities || []).includes(cap);
                      return (
                        <label key={cap} style={{ display: "inline-flex", alignItems: "center", gap: 6, marginRight: 8 }}>
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={(e) => {
                              setEditingModel((s) => {
                                const prev = s[m.id] || {};
                                const prevCaps: string[] = prev.capabilities || [];
                                const nextCaps = e.target.checked ? Array.from(new Set([...prevCaps, cap])) : prevCaps.filter((c) => c !== cap);
                                return { ...s, [m.id]: { ...prev, capabilities: nextCaps } };
                              });
                            }}
                          />
                          <span style={{ textTransform: "capitalize" }}>{cap}</span>
                        </label>
                      );
                    })}
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <label>
                      <input
                        type="checkbox"
                        checked={!!editingModel[m.id].is_active}
                        onChange={(e) => setEditingModel((s) => ({ ...s, [m.id]: { ...s[m.id], is_active: e.target.checked } }))}
                      />{" "}
                      Active
                    </label>
                    <input
                      type="number"
                      value={editingModel[m.id].priority ?? 0}
                      onChange={(e) => setEditingModel((s) => ({ ...s, [m.id]: { ...s[m.id], priority: parseInt(e.target.value || "0", 10) } }))}
                      style={{ width: 80 }}
                    />
                    <button onClick={() => saveModelConfig(m.id)}>Save</button>
                    <button onClick={() => setEditingModel((s) => { const n = { ...s }; delete n[m.id]; return n; })}>Cancel</button>
                  </div>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}


