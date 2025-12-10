'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useTasks, useAgents } from '@/lib/hooks/use-api'
import { Activity, CheckCircle, Clock, AlertCircle } from 'lucide-react'

export function MetricsCards() {
  const { data: tasks, isLoading: tasksLoading } = useTasks()
  const { data: agents, isLoading: agentsLoading } = useAgents()

  if (tasksLoading || agentsLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i} className="animate-pulse">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div className="h-4 w-20 bg-muted rounded" />
              <div className="h-4 w-4 bg-muted rounded" />
            </CardHeader>
            <CardContent>
              <div className="h-8 w-16 bg-muted rounded" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  // Map backend statuses to our categories
  const activeTasks = tasks?.filter((t) => 
    ['in_progress', 'executing', 'planning', 'pending_approval'].includes(t.status?.toLowerCase())
  ).length || 0
  const completedTasks = tasks?.filter((t) => 
    t.status?.toLowerCase() === 'completed'
  ).length || 0
  const pendingTasks = tasks?.filter((t) => 
    ['pending', 'planning'].includes(t.status?.toLowerCase())
  ).length || 0
  const failedTasks = tasks?.filter((t) => 
    ['failed', 'error'].includes(t.status?.toLowerCase())
  ).length || 0
  const activeAgents = agents?.filter((a) => 
    a.status?.toLowerCase() === 'active' || a.status?.toLowerCase() === 'busy'
  ).length || 0

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Active Tasks</CardTitle>
          <Activity className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{activeTasks}</div>
          <p className="text-xs text-muted-foreground">
            {activeAgents} agent{activeAgents !== 1 ? 's' : ''} working
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Completed</CardTitle>
          <CheckCircle className="h-4 w-4 text-green-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{completedTasks}</div>
          <p className="text-xs text-muted-foreground">
            Total tasks completed
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Pending</CardTitle>
          <Clock className="h-4 w-4 text-yellow-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{pendingTasks}</div>
          <p className="text-xs text-muted-foreground">
            Waiting to start
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Failed</CardTitle>
          <AlertCircle className="h-4 w-4 text-red-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{failedTasks}</div>
          <p className="text-xs text-muted-foreground">
            Requires attention
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
