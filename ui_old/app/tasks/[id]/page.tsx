'use client'

import { useTask } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { formatDistanceToNow } from 'date-fns'
import { ArrowLeft, Activity, Clock, CheckCircle, XCircle, Loader2, MessageSquare } from 'lucide-react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { Progress } from '@/components/ui/progress'
import { TaskPlans } from '@/components/tasks/task-plans'

const getStatusConfig = (status: string) => {
  const statusLower = status?.toLowerCase() || ''
  if (['in_progress', 'executing'].includes(statusLower)) {
    return { label: 'In Progress', icon: Activity, color: 'bg-blue-500' }
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

export default function TaskDetailPage() {
  const params = useParams()
  const taskId = params.id as string
  const { data: task, isLoading } = useTask(taskId)

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="space-y-4">
          <div className="h-8 bg-muted rounded w-1/4 animate-pulse" />
          <Card className="animate-pulse">
            <CardContent className="p-6">
              <div className="h-4 bg-muted rounded w-3/4 mb-4" />
              <div className="h-3 bg-muted rounded w-1/2" />
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  if (!task) {
    return (
      <div className="container mx-auto px-4 py-8">
          <Card>
            <CardContent className="p-12 text-center">
              <p className="text-muted-foreground mb-4">Task not found</p>
              <Link href="/tasks">
                <Button variant="outline">
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Back to Tasks
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>
    )
  }

  const config = getStatusConfig(task.status)
  const Icon = config.icon
  const isInProgress = ['in_progress', 'executing'].includes(task.status?.toLowerCase())

  return (
    <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-6">
          <Link href="/tasks">
            <Button variant="ghost" className="mb-4">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Tasks
            </Button>
          </Link>
          <div className="flex items-center space-x-4">
            <div className={`h-12 w-12 rounded-full ${config.color} flex items-center justify-center`}>
              <Icon className={`h-6 w-6 text-white ${isInProgress ? 'animate-spin' : ''}`} />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">
                {task.description || 'Untitled Task'}
              </h1>
              <div className="flex items-center space-x-2 mt-2">
                <Badge variant="default">{config.label}</Badge>
                {task.current_stage && (
                  <Badge variant="outline">{task.current_stage}</Badge>
                )}
                <Link href={`/chat/${taskId}`}>
                  <Button variant="outline" size="sm">
                    <MessageSquare className="h-4 w-4 mr-2" />
                    Chat
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          {/* Main Info */}
          <Card>
            <CardHeader>
              <CardTitle>Task Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground">Status</p>
                <p className="font-medium">{config.label}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Current Stage</p>
                <p className="font-medium">{task.current_stage || 'N/A'}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Created</p>
                <p className="font-medium">
                  {formatDistanceToNow(new Date(task.created_at), { addSuffix: true })}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Last Updated</p>
                <p className="font-medium">
                  {formatDistanceToNow(new Date(task.updated_at), { addSuffix: true })}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Progress */}
          <Card>
            <CardHeader>
              <CardTitle>Progress</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-sm text-muted-foreground">Completion</span>
                  <span className="text-sm font-medium">{task.progress_percent.toFixed(0)}%</span>
                </div>
                <Progress value={task.progress_percent} />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Steps</p>
                <p className="font-medium">
                  {task.completed_steps} of {task.total_steps} completed
                </p>
              </div>
              {task.current_step && (
                <div>
                  <p className="text-sm text-muted-foreground">Current Step</p>
                  <p className="font-medium">{task.current_step.description}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Step {task.current_step.step_number} • {task.current_step.status}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Agents & Tools */}
          {(task.agents_in_use?.length > 0 || task.tools_in_use?.length > 0) && (
            <Card>
              <CardHeader>
                <CardTitle>Resources</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {task.agents_in_use && task.agents_in_use.length > 0 && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-2">Agents</p>
                    <div className="flex flex-wrap gap-2">
                      {task.agents_in_use.map((agent) => (
                        <Badge key={agent} variant="outline">{agent}</Badge>
                      ))}
                    </div>
                  </div>
                )}
                {task.tools_in_use && task.tools_in_use.length > 0 && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-2">Tools</p>
                    <div className="flex flex-wrap gap-2">
                      {task.tools_in_use.map((tool) => (
                        <Badge key={tool} variant="outline">{tool}</Badge>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Latest Logs */}
          {task.latest_logs && task.latest_logs.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Recent Activity</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {task.latest_logs.slice(0, 5).map((log, idx) => (
                    <div key={idx} className="text-sm border-l-2 pl-3 py-1">
                      <div className="flex items-center justify-between">
                        <span className="font-medium">{log.stage}</span>
                        <span className="text-xs text-muted-foreground">
                          {formatDistanceToNow(new Date(log.timestamp), { addSuffix: true })}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                        {log.content_preview}
                      </p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Plans for this task */}
          <div className="md:col-span-2">
            <TaskPlans taskId={task.task_id} />
          </div>
        </div>
    </div>
  )
}
