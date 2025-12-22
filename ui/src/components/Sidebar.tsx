import React from "react";

type Props = {
  mode: string;
  onChangeMode: (m: string) => void;
};

const MODES = ["Chat", "Timeline", "Graph", "Registry", "Prompts", "Settings"];

export default function Sidebar({ mode, onChangeMode }: Props) {
  return (
    <div style={{ width: 220, background: "#fafbfe", padding: 12, borderRight: "1px solid #eef2f7", display: "flex", flexDirection: "column", gap: 8 }}>
      {MODES.map((m) => (
        <button
          key={m}
          onClick={() => onChangeMode(m)}
          style={{
            textAlign: "left",
            padding: "8px 10px",
            borderRadius: 6,
            background: m === mode ? "#eef2ff" : "transparent",
            border: "1px solid transparent",
            cursor: "pointer"
          }}
        >
          {m}
        </button>
      ))}
    </div>
  );
}


