import React, { useState } from "react";
import DualFlowCanvas from "./components/DualFlowCanvas";
import ChatPanel from "./components/ChatPanel";
import ModelSettings from "./components/ModelSettings";
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
        <aside style={{ width: "260px", background: "#fafafa", padding: 12 }}>
          <ModelSettings />
        </aside>
      ) : null}
      <RealtimeEventsPanel />
    </div>
    </ModelProvider>
    </SessionProvider>
  );
}


