import React from "react";

type Props = {
  currentStage?: string;
  activeComponent?: string;
};

export default function StatusBar({ currentStage, activeComponent }: Props) {
  return (
    <div style={{ padding: 8, borderTop: "1px solid #eef2f7", fontSize: 13, color: "#6b7280", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <div>Stage: {currentStage ?? "idle"}</div>
      <div>Active: {activeComponent ?? "—"}</div>
    </div>
  );
}


