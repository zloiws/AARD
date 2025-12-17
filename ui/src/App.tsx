import React, { useState } from "react";
import ChatPanel from "./components/ChatPanel";
import ModelSettings from "./components/ModelSettings";
import PromptsPanel from "./components/PromptsPanel";
import { ModelProvider } from "./contexts/ModelContext";
import { SessionProvider } from "./contexts/SessionContext";
import TopBar from "./components/TopBar";
import Sidebar from "./components/Sidebar";
import Workspace from "./components/Workspace";
import StatusBar from "./components/StatusBar";

export default function App() {
  const [paused, setPaused] = useState<boolean>(false);
  const [mode, setMode] = useState<string>("Timeline");

  return (
    <SessionProvider>
    <ModelProvider>
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <TopBar
        onOpenSettings={() => setMode("Settings")}
        onOpenRegistry={() => setMode("Registry")}
        onOpenPrompts={() => setMode("Prompts")}
        onPauseToggle={() => setPaused((p) => !p)}
        paused={paused}
      />

      <div style={{ flex: 1, display: "flex", minHeight: 0 }}>
        <Sidebar mode={mode} onChangeMode={(m) => setMode(m)} />

        <main style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
          <div style={{ flex: 1, display: "flex", minHeight: 0 }}>
            <Workspace mode={mode} />
          </div>
          <StatusBar currentStage={paused ? "paused" : "idle"} activeComponent={mode} />
        </main>
      </div>
      {/* RealtimeEventsPanel intentionally not mounted by default per UI spec (use Timeline/StatusBar for observability) */}
    </div>
    </ModelProvider>
    </SessionProvider>
  );
}


