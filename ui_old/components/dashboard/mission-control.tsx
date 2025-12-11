'use client'

import { MetricsCards } from '@/components/dashboard/metrics-cards'
import { ActiveTasksList } from '@/components/dashboard/active-tasks-list'
import { useWebSocket } from '@/lib/hooks/use-websocket'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { WorkflowVisualization } from '@/components/workflow/workflow-visualization'

export function MissionControlDashboard() {
  // Enable WebSocket for real-time updates
  useWebSocket(true)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Mission Control</h1>
        <p className="text-muted-foreground">
          Monitor and manage your AI agent workflows
        </p>
      </div>

      <MetricsCards />

      <div className="grid gap-6 md:grid-cols-2">
        <ActiveTasksList />
        
        {/* Workflow Visualization */}
        <Card>
          <CardHeader>
            <CardTitle>Workflow Visualization</CardTitle>
            <CardDescription>
              Visual representation of active workflows and agent interactions
            </CardDescription>
          </CardHeader>
          <CardContent>
            <WorkflowVisualization />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
