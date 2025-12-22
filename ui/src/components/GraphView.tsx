import React, { useState } from "react";
import GraphCanvas from "./GraphCanvas";

export default function GraphView(): JSX.Element {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  function handleSelect(nodeId: string) {
    setSelectedNode(nodeId);
    // also dispatch for Timeline to cross-highlight (GraphCanvas does too)
    try {
      const ev = new CustomEvent("graph-node-select", { detail: { nodeId } });
      window.dispatchEvent(ev);
    } catch {}
  }

  return (
    <div style={{ padding: 12 }}>
      <h4>Graph</h4>
      <GraphCanvas width={820} height={560} onSelectNode={handleSelect} />
      <div style={{ marginTop: 8, color: "#6b7280" }}>{selectedNode ? `Selected: ${selectedNode}` : "Click a node to view details"}</div>
    </div>
  );
}


