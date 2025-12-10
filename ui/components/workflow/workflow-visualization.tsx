'use client'

import { useMemo } from 'react'
import { Node, Edge, Position } from '@xyflow/react'
import { WorkflowBuilder } from './workflow-builder'
import { useTasks, usePlans, useAgents } from '@/lib/hooks/use-api'
import { Loader2 } from 'lucide-react'

// Extended node types
interface TaskNodeData {
  type: 'task'
  label: string
  description: string
  status: string
  taskId: string
}

interface PlanNodeData {
  type: 'plan'
  label: string
  planId: string
  taskId: string
  status: string
  currentStep?: number
  totalSteps?: number
}

interface AgentNodeData {
  type: 'agent'
  label: string
  role: string
  status: 'idle' | 'busy' | 'completed' | 'failed'
  agentId: string
}

type WorkflowNodeData = TaskNodeData | PlanNodeData | AgentNodeData

const getStatusColor = (status: string): string => {
  const statusLower = status.toLowerCase()
  if (statusLower.includes('completed') || statusLower === 'approved') {
    return '#22c55e' // green
  }
  if (statusLower.includes('failed') || statusLower.includes('error') || statusLower === 'cancelled') {
    return '#ef4444' // red
  }
  if (statusLower.includes('progress') || statusLower.includes('executing') || statusLower === 'in_progress') {
    return '#3b82f6' // blue
  }
  if (statusLower.includes('pending') || statusLower === 'draft') {
    return '#f59e0b' // yellow
  }
  return '#6b7280' // gray
}

const getAgentStatus = (agent: any, tasks: any[]): 'idle' | 'busy' | 'completed' | 'failed' => {
  // Check if agent is used in any active task
  const activeTasks = tasks.filter(t => 
    t.status === 'in_progress' || t.status === 'executing' || t.status === 'pending'
  )
  const isBusy = activeTasks.some(t => t.agents_in_use?.includes(agent.id))
  
  if (isBusy) return 'busy'
  return 'idle'
}

export function WorkflowVisualization() {
  const { data: tasks, isLoading: tasksLoading } = useTasks()
  const { data: agents, isLoading: agentsLoading } = useAgents()
  
  // Get plans for active tasks
  const activeTasks = useMemo(() => {
    return (tasks || []).filter(t => 
      t.status !== 'completed' && t.status !== 'failed' && t.status !== 'cancelled'
    ).slice(0, 10) // Limit to 10 active tasks for performance
  }, [tasks])

  // Get all plans (we'll filter by task_id in useMemo)
  const { data: plansData } = usePlans()
  const plans = useMemo(() => {
    if (!plansData) return []
    // plansData can be array or object with plans property
    if (Array.isArray(plansData)) {
      return plansData
    }
    if (plansData && typeof plansData === 'object' && 'plans' in plansData) {
      return (plansData as any).plans || []
    }
    return []
  }, [plansData])

  const isLoading = tasksLoading || agentsLoading

  const { nodes, edges } = useMemo(() => {
    if (!activeTasks.length) {
      return { nodes: [], edges: [] }
    }

    const workflowNodes: Node<WorkflowNodeData>[] = []
    const workflowEdges: Edge[] = []

    // Layout configuration
    const taskYSpacing = 200
    const planYOffset = 100
    const agentYOffset = 50
    let currentX = 100
    let currentY = 100

    activeTasks.forEach((task, taskIndex) => {
      // Task Node
      const taskNode: Node<TaskNodeData> = {
        id: `task-${task.task_id}`,
        type: 'task',
        position: { x: currentX, y: currentY },
        data: {
          type: 'task',
          label: `Task ${taskIndex + 1}`,
          description: task.description?.substring(0, 50) + (task.description?.length > 50 ? '...' : '') || 'No description',
          status: task.status,
          taskId: task.task_id,
        },
        style: {
          background: getStatusColor(task.status),
          color: '#fff',
          border: '2px solid',
          borderColor: getStatusColor(task.status),
          borderRadius: '8px',
          padding: '10px',
          minWidth: '200px',
        },
      }
      workflowNodes.push(taskNode)

      // Find plans for this task
      const taskPlans = plans.filter((p: any) => p.task_id === task.task_id)
      
      if (taskPlans.length > 0) {
        taskPlans.forEach((plan: any, planIndex: number) => {
          const planY = currentY + planYOffset
          const planX = currentX + (planIndex * 250)

          // Plan Node
          const planNode: Node<PlanNodeData> = {
            id: `plan-${plan.id}`,
            type: 'plan',
            position: { x: planX, y: planY },
            data: {
              type: 'plan',
              label: `Plan v${plan.version || 1}`,
              planId: plan.id,
              taskId: plan.task_id,
              status: plan.status || 'pending',
              currentStep: plan.current_step,
              totalSteps: plan.steps?.length || 0,
            },
            style: {
              background: getStatusColor(plan.status || 'pending'),
              color: '#fff',
              border: '2px solid',
              borderColor: getStatusColor(plan.status || 'pending'),
              borderRadius: '8px',
              padding: '10px',
              minWidth: '180px',
            },
          }
          workflowNodes.push(planNode)

          // Edge: Task -> Plan
          workflowEdges.push({
            id: `edge-task-${task.task_id}-plan-${plan.id}`,
            source: `task-${task.task_id}`,
            target: `plan-${plan.id}`,
            type: 'smoothstep',
            animated: plan.status === 'in_progress' || plan.status === 'executing',
            style: { stroke: getStatusColor(plan.status || 'pending'), strokeWidth: 2 },
          })

          // Find agents used in this task
          const taskAgents = (task.agents_in_use || []).map((agentId: string) => {
            return (agents || [])?.find((a: any) => a.id === agentId || String(a.id) === String(agentId))
          }).filter(Boolean)

          taskAgents.forEach((agent: any, agentIndex: number) => {
            const agentY = planY + agentYOffset
            const agentX = planX + (agentIndex * 200)

            // Agent Node
            const agentStatus = getAgentStatus(agent, activeTasks)
            const agentNode: Node<AgentNodeData> = {
              id: `agent-${agent.id}`,
              type: 'agent',
              position: { x: agentX, y: agentY },
              data: {
                type: 'agent',
                label: agent.name || `Agent ${agent.id.substring(0, 8)}`,
                role: agent.role || 'agent',
                status: agentStatus,
                agentId: agent.id,
              },
            }
            workflowNodes.push(agentNode)

            // Edge: Plan -> Agent
            workflowEdges.push({
              id: `edge-plan-${plan.id}-agent-${agent.id}`,
              source: `plan-${plan.id}`,
              target: `agent-${agent.id}`,
              type: 'smoothstep',
              animated: agentStatus === 'busy',
              style: { stroke: agentStatus === 'busy' ? '#3b82f6' : '#6b7280', strokeWidth: 2 },
            })
          })
        })
      } else {
        // If no plans, show agents directly connected to task
        const taskAgents = (task.agents_in_use || []).map((agentId: string) => {
          return (agents || [])?.find((a: any) => a.id === agentId || String(a.id) === String(agentId))
        }).filter(Boolean)

        taskAgents.forEach((agent: any, agentIndex: number) => {
          const agentY = currentY + agentYOffset
          const agentX = currentX + (agentIndex * 200)

          const agentStatus = getAgentStatus(agent, activeTasks)
          const agentNode: Node<AgentNodeData> = {
            id: `agent-${agent.id}`,
            type: 'agent',
            position: { x: agentX, y: agentY },
            data: {
              type: 'agent',
              label: agent.name || `Agent ${agent.id.substring(0, 8)}`,
              role: agent.role || 'agent',
              status: agentStatus,
              agentId: agent.id,
            },
          }
          workflowNodes.push(agentNode)

          // Edge: Task -> Agent
          workflowEdges.push({
            id: `edge-task-${task.task_id}-agent-${agent.id}`,
            source: `task-${task.task_id}`,
            target: `agent-${agent.id}`,
            type: 'smoothstep',
            animated: agentStatus === 'busy',
            style: { stroke: agentStatus === 'busy' ? '#3b82f6' : '#6b7280', strokeWidth: 2 },
          })
        })
      }

      // Move to next column
      currentX += 400
      if (currentX > 1200) {
        currentX = 100
        currentY += 400
      }
    })

    return { nodes: workflowNodes, edges: workflowEdges }
  }, [activeTasks, plans, agents])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[600px]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (nodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[600px] text-center p-8">
        <p className="text-muted-foreground mb-2">No active workflows</p>
        <p className="text-sm text-muted-foreground">
          Create a task to see workflow visualization
        </p>
      </div>
    )
  }

  return (
    <div className="h-[600px] w-full">
      <WorkflowBuilder
        initialNodes={nodes}
        initialEdges={edges}
      />
    </div>
  )
}
