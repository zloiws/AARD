'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useTasks } from '@/lib/hooks/use-api'
import { formatDistanceToNow } from 'date-fns'
import { ArrowRight, Clock, CheckCircle, XCircle, Loader2 } from 'lucide-react'
import Link from 'next/link'

const getStatusConfig = (status: string) => {
  const statusLower = status?.toLowerCase() || ''
  if (['in_progress', 'executing'].includes(statusLower)) {
    return { label: 'In Progress', icon: Loader2, color: 'bg-blue-500' }
  }
  if (['completed', 'done'].includes(statusLower)) {
    return { label: 'Completed', icon: CheckCircle, color: 'bg-green-500' }
  }
  if (['failed', 'error'].includes(statusLower)) {
    return { label: 'Failed', icon: XCircle, color: 'bg-red-500' }
  }
  if (['pending', 'planning', 'pending_approval'].includes(statusLower)) {
    return { label: 'Pending', icon: Clock, color: 'bg-yellow-500' }
  }
  return { label: status || 'Unknown', icon: Clock, color: 'bg-gray-500' }
}

export function ActiveTasksList() {
  const { data: tasks, isLoading } = useTasks()

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Active Tasks</CardTitle>
          <CardDescription>Recent and ongoing tasks</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center space-x-4 animate-pulse">
                <div className="h-12 w-12 bg-muted rounded" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-muted rounded w-3/4" />
                  <div className="h-3 bg-muted rounded w-1/2" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  const recentTasks = tasks
    ?.filter((t) => !['completed', 'done'].includes(t.status?.toLowerCase()))
    .slice(0, 5) || []

  return (
    <Card>
      <CardHeader>
        <CardTitle>Active Tasks</CardTitle>
        <CardDescription>Recent and ongoing tasks</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {recentTasks.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No active tasks
            </p>
          ) : (
            recentTasks.map((task) => {
              const config = getStatusConfig(task.status)
              const Icon = config.icon
              const isInProgress = ['in_progress', 'executing'].includes(task.status?.toLowerCase())

              return (
                <div
                  key={task.task_id}
                  className="flex items-start space-x-4 p-3 rounded-lg border hover:bg-accent/50 transition-colors"
                >
                  <div className={`h-10 w-10 rounded-full ${config.color} flex items-center justify-center`}>
                    <Icon className={`h-5 w-5 text-white ${isInProgress ? 'animate-spin' : ''}`} />
                  </div>
                  
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-medium leading-none">
                        {task.description || 'Untitled Task'}
                      </h4>
                      <Badge variant="outline">{config.label}</Badge>
                    </div>
                    {task.current_stage && (
                      <p className="text-sm text-muted-foreground line-clamp-1">
                        Stage: {task.current_stage} • {task.progress_percent.toFixed(0)}% complete
                      </p>
                    )}
                    <p className="text-xs text-muted-foreground">
                      Updated {formatDistanceToNow(new Date(task.updated_at), { addSuffix: true })}
                    </p>
                  </div>

                  <Link href={`/tasks/${task.task_id}`}>
                    <Button variant="ghost" size="icon">
                      <ArrowRight className="h-4 w-4" />
                    </Button>
                  </Link>
                </div>
              )
            })
          )}

          {tasks && tasks.length > 5 && (
            <Link href="/tasks">
              <Button variant="outline" className="w-full">
                View All Tasks
              </Button>
            </Link>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
