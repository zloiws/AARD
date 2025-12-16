import React, { useState } from "react";
import DualFlowCanvas from "./components/DualFlowCanvas";
import ChatPanel from "./components/ChatPanel";
import ModelSettings from "./components/ModelSettings";
import PromptsPanel from "./components/PromptsPanel";
import { ModelProvider } from "./contexts/ModelContext";
import { SessionProvider } from "./contexts/SessionContext";
import RealtimeEventsPanel from "./components/RealtimeEventsPanel";

export default function App() {
  const [showModelSettings, setShowModelSettings] = useState<boolean>(false);

  return (
    <SessionProvider>
    <ModelProvider>
    <div style={{ height: "100vh", display: "flex", gap: 12 }}>
      <aside style={{ width: "300px", background: "#f5f7fb", padding: 12, display: "flex", flexDirection: "column" }}>
        <ChatPanel />
      </aside>

      <main style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        <header style={{ padding: 12, borderBottom: "1px solid #e6e9ef" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h2 style={{ margin: 0 }}>Dual Flow Canvas</h2>
            <div>
              <button onClick={() => setShowModelSettings((s) => !s)} style={{ padding: "6px 10px" }}>
                {showModelSettings ? "Hide Model Settings" : "Show Model Settings"}
              </button>
            </div>
          </div>
        </header>

        <section style={{ flex: 1, display: "flex", padding: 12 }}>
          <DualFlowCanvas />
        </section>
      </main>

      {showModelSettings ? (
        <>
          <div
            onClick={() => setShowModelSettings(false)}
            style={{
              position: "fixed",
              inset: 0,
              background: "rgba(0,0,0,0.4)",
              zIndex: 40,
            }}
          />
          <div
            role="dialog"
            aria-modal="true"
            style={{
              position: "fixed",
              left: "50%",
              top: "50%",
              transform: "translate(-50%, -50%)",
              background: "#fff",
              borderRadius: 8,
              boxShadow: "0 12px 48px rgba(0,0,0,0.2)",
              width: Math.min(900, window.innerWidth - 80),
              maxHeight: "80vh",
              overflow: "auto",
              padding: 16,
              zIndex: 50,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <h3 style={{ margin: 0 }}>Settings</h3>
              <div>
                <button onClick={() => setShowModelSettings(false)} style={{ padding: "6px 10px" }}>
                  Close
                </button>
              </div>
            </div>
            <div style={{ display: "flex", gap: 12 }}>
              <div style={{ flex: 1 }}>
                <ModelSettings />
              </div>
              <div style={{ width: 360, borderLeft: "1px solid #eef2f7", paddingLeft: 12 }}>
                <React.Suspense fallback={<div>Loading prompts...</div>}>
                  <PromptsPanel />
                </React.Suspense>
              </div>
            </div>
          </div>
        </>
      ) : null}
      <RealtimeEventsPanel />
    </div>
    </ModelProvider>
    </SessionProvider>
  );
}


