'use client'

import { useMemo } from 'react'
import {
  ReactFlow,
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { 
  Brain, 
  Code, 
  Wrench, 
  FileText, 
  GitBranch, 
  AlertCircle,
  User,
  Zap
} from 'lucide-react'

interface WorkflowEvent {
  id: string
  workflow_id: string
  event_type: string
  event_source: string
  stage: string
  status: string
  message: string
  event_data?: any
  metadata?: any
  timestamp: string
  duration_ms?: number
  parent_event_id?: string
}

interface WorkflowGraphProps {
  events: WorkflowEvent[]
  className?: string
}

const getNodeType = (eventSource: string, eventType: string) => {
  if (eventSource === 'user') return 'user'
  if (eventSource === 'model' || eventType.includes('model')) return 'model'
  if (eventSource === 'tool' || eventType.includes('tool')) return 'tool'
  if (eventSource === 'planner_agent' || eventType.includes('plan')) return 'planner'
  if (eventSource === 'coder_agent') return 'coder'
  if (eventSource === 'system') return 'system'
  return 'default'
}

const getNodeColor = (status: string, nodeType: string) => {
  if (status === 'failed') return '#ef4444'
  if (status === 'completed') return '#22c55e'
  if (status === 'in_progress') return '#3b82f6'
  
  const typeColors: Record<string, string> = {
    user: '#8b5cf6',
    model: '#06b6d4',
    tool: '#f59e0b',
    planner: '#10b981',
    coder: '#6366f1',
    system: '#64748b',
  }
  return typeColors[nodeType] || '#94a3b8'
}

const getNodeIcon = (nodeType: string) => {
  const icons: Record<string, any> = {
    user: User,
    model: Brain,
    tool: Wrench,
    planner: GitBranch,
    coder: Code,
    system: Zap,
  }
  return icons[nodeType] || Zap
}

export function WorkflowGraph({ events, className }: WorkflowGraphProps) {
  const { nodes, edges } = useMemo(() => {
    if (!events || events.length === 0) {
      return { nodes: [], edges: [] }
    }

    const nodeMap = new Map<string, Node>()
    const edgeList: Edge[] = []
    const eventMap = new Map(events.map(e => [e.id, e]))

    // Create nodes
    events.forEach((event, index) => {
      const nodeType = getNodeType(event.event_source, event.event_type)
      const Icon = getNodeIcon(nodeType)
      const color = getNodeColor(event.status, nodeType)
      
      const node: Node = {
        id: event.id,
        type: 'default',
        position: {
          x: (index % 4) * 250,
          y: Math.floor(index / 4) * 150,
        },
        data: {
          label: (
            <div className="flex flex-col gap-1 p-2 min-w-[200px]">
              <div className="flex items-center gap-2">
                <Icon className="h-4 w-4" style={{ color }} />
                <span className="text-xs font-semibold">{event.event_source}</span>
              </div>
              <p className="text-xs text-muted-foreground line-clamp-2">
                {event.message}
              </p>
              <div className="flex items-center gap-1 mt-1">
                <Badge variant="outline" className="text-xs">
                  {event.stage}
                </Badge>
                {event.duration_ms && (
                  <span className="text-xs text-muted-foreground">
                    {(event.duration_ms / 1000).toFixed(1)}s
                  </span>
                )}
              </div>
            </div>
          ),
        },
        style: {
          background: '#fff',
          border: `2px solid ${color}`,
          borderRadius: '8px',
        },
      }

      nodeMap.set(event.id, node)

      // Create edges
      if (event.parent_event_id && eventMap.has(event.parent_event_id)) {
        edgeList.push({
          id: `${event.parent_event_id}-${event.id}`,
          source: event.parent_event_id,
          target: event.id,
          type: 'smoothstep',
          animated: event.status === 'in_progress',
          style: {
            stroke: color,
            strokeWidth: 2,
          },
        })
      }
    })

    return {
      nodes: Array.from(nodeMap.values()),
      edges: edgeList,
    }
  }, [events])

  if (nodes.length === 0) {
    return (
      <div className={cn("flex items-center justify-center h-64 text-muted-foreground", className)}>
        <p className="text-sm">Нет событий для визуализации</p>
      </div>
    )
  }

  return (
    <div className={cn("h-96 w-full", className)}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        nodesDraggable
        nodesConnectable={false}
        elementsSelectable
      >
        <Background />
        <Controls />
        <MiniMap 
          nodeColor={(node) => {
            const event = events.find(e => e.id === node.id)
            if (!event) return '#94a3b8'
            return getNodeColor(event.status, getNodeType(event.event_source, event.event_type))
          }}
        />
      </ReactFlow>
    </div>
  )
}
