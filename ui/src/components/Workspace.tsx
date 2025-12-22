import React from "react";
import ChatPanel from "./ChatPanel";
import TimelineView from "./TimelineView";
import GraphView from "./GraphView";
import RegistryView from "./RegistryView";
import PromptsPanel from "./PromptsPanel";
import ModelSettings from "./ModelSettings";

type Props = {
  mode: string;
};

export default function Workspace({ mode }: Props) {
  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
      {mode === "Chat" ? <ChatPanel /> : null}
      {mode === "Timeline" ? <TimelineView /> : null}
      {mode === "Graph" ? <GraphView /> : null}
      {mode === "Registry" ? <RegistryView /> : null}
      {mode === "Prompts" ? <PromptsPanel /> : null}
      {mode === "Settings" ? (
        <div style={{ padding: 12 }}>
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
      ) : null}
    </div>
  );
}


