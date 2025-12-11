'use client'

import { useCallback } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Node,
  Edge,
  BackgroundVariant,
} from '@xyflow/react'
import { AgentNode, AgentNodeData } from './agent-node'
import { TaskNode, TaskNodeData } from './task-node'
import { PlanNode, PlanNodeData } from './plan-node'
import '@xyflow/react/dist/style.css'

const nodeTypes = {
  agent: AgentNode,
  task: TaskNode,
  plan: PlanNode,
  default: TaskNode, // Default node type
}

type WorkflowNodeData = AgentNodeData | TaskNodeData | PlanNodeData

interface WorkflowBuilderProps {
  initialNodes?: Node<WorkflowNodeData>[]
  initialEdges?: Edge[]
  onNodesChange?: (nodes: Node<WorkflowNodeData>[]) => void
  onEdgesChange?: (edges: Edge[]) => void
}

export function WorkflowBuilder({
  initialNodes = [],
  initialEdges = [],
  onNodesChange,
  onEdgesChange,
}: WorkflowBuilderProps) {
  const [nodes, setNodes, onNodesChangeInternal] = useNodesState<WorkflowNodeData>(initialNodes)
  const [edges, setEdges, onEdgesChangeInternal] = useEdgesState(initialEdges)

  const onConnect = useCallback(
    (params: Connection) => {
      const newEdges = addEdge(params, edges)
      setEdges(newEdges)
      onEdgesChange?.(newEdges)
    },
    [edges, setEdges, onEdgesChange]
  )

  const handleNodesChange = useCallback(
    (changes: any) => {
      onNodesChangeInternal(changes)
    },
    [onNodesChangeInternal]
  )

  const handleEdgesChange = useCallback(
    (changes: any) => {
      onEdgesChangeInternal(changes)
      onEdgesChange?.(edges)
    },
    [onEdgesChangeInternal, onEdgesChange, edges]
  )

  return (
    <div className="h-[600px] w-full rounded-lg border bg-background">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={handleEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-left"
      >
        <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
        <Controls />
        <MiniMap
          nodeColor={(node) => {
            const data = node.data as WorkflowNodeData
            if ('type' in data) {
              if (data.type === 'task' || data.type === 'plan') {
                const status = data.status.toLowerCase()
                if (status.includes('completed') || status === 'approved') return '#22c55e'
                if (status.includes('failed') || status === 'cancelled') return '#ef4444'
                if (status.includes('progress') || status.includes('executing')) return '#3b82f6'
                if (status.includes('pending')) return '#f59e0b'
              }
              if (data.type === 'agent') {
                switch (data.status) {
                  case 'busy': return '#3b82f6'
                  case 'completed': return '#22c55e'
                  case 'failed': return '#ef4444'
                  default: return '#6b7280'
                }
              }
            }
            return '#6b7280'
          }}
        />
      </ReactFlow>
    </div>
  )
}
