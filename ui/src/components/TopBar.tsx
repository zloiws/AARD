import React from "react";

type Props = {
  onOpenSettings: () => void;
  onOpenRegistry: () => void;
  onOpenPrompts: () => void;
  onPauseToggle: () => void;
  paused: boolean;
};

export default function TopBar({ onOpenSettings, onOpenRegistry, onOpenPrompts, onPauseToggle, paused }: Props) {
  return (
    <div style={{ padding: 12, borderBottom: "1px solid #e6e9ef", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        <div style={{ fontWeight: 700 }}>AARD</div>
        <div style={{ fontSize: 13, color: "#6b7280" }}>Session: —</div>
        <div style={{ fontSize: 13, color: "#6b7280" }}>Backend: <span style={{ marginLeft: 6 }}>🟢 connected</span></div>
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={onOpenSettings} style={{ padding: "6px 10px" }}>Settings</button>
        <button onClick={onOpenRegistry} style={{ padding: "6px 10px" }}>Registry</button>
        <button onClick={onOpenPrompts} style={{ padding: "6px 10px" }}>Prompts</button>
        <button onClick={onPauseToggle} style={{ padding: "6px 10px" }}>{paused ? "Resume execution" : "Pause execution"}</button>
      </div>
    </div>
  );
}


