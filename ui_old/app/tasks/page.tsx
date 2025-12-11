'use client'

import { useTasks } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { formatDistanceToNow } from 'date-fns'
import { Search, Plus, Loader2, Clock, CheckCircle, XCircle, Activity, MessageSquare } from 'lucide-react'
import Link from 'next/link'
import { useState } from 'react'

const getStatusConfig = (status: string) => {
  const statusLower = status?.toLowerCase() || ''
  if (['in_progress', 'executing'].includes(statusLower)) {
    return { label: 'In Progress', icon: Activity, color: 'bg-blue-500', variant: 'default' as const }
  }
  if (['completed', 'done'].includes(statusLower)) {
    return { label: 'Completed', icon: CheckCircle, color: 'bg-green-500', variant: 'default' as const }
  }
  if (['failed', 'error'].includes(statusLower)) {
    return { label: 'Failed', icon: XCircle, color: 'bg-red-500', variant: 'destructive' as const }
  }
  if (['pending', 'planning', 'pending_approval'].includes(statusLower)) {
    return { label: 'Pending', icon: Clock, color: 'bg-yellow-500', variant: 'secondary' as const }
  }
  return { label: status || 'Unknown', icon: Clock, color: 'bg-gray-500', variant: 'outline' as const }
}

export default function TasksPage() {
  const { data: tasks, isLoading, error } = useTasks()
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  const filteredTasks = (tasks || []).filter((task) => {
    const matchesSearch = task.description?.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = statusFilter === 'all' || task.status?.toLowerCase() === statusFilter.toLowerCase()
    return matchesSearch && matchesStatus
  })

  const statusCounts = {
    all: tasks?.length || 0,
    active: tasks?.filter(t => ['in_progress', 'executing', 'planning'].includes(t.status?.toLowerCase())).length || 0,
    completed: tasks?.filter(t => t.status?.toLowerCase() === 'completed').length || 0,
    failed: tasks?.filter(t => ['failed', 'error'].includes(t.status?.toLowerCase())).length || 0,
  }

  return (
    <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Tasks</h1>
            <p className="text-muted-foreground mt-2">
              Manage and monitor all tasks
            </p>
          </div>
          <Link href="/tasks/new">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              New Task
            </Button>
          </Link>
        </div>

        {/* Filters */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Filters</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search tasks..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
              <div className="flex gap-2">
                {['all', 'active', 'completed', 'failed'].map((status) => (
                  <Button
                    key={status}
                    variant={statusFilter === status ? 'default' : 'outline'}
                    onClick={() => setStatusFilter(status)}
                    className="capitalize"
                  >
                    {status} ({statusCounts[status as keyof typeof statusCounts]})
                  </Button>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Tasks List */}
        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="animate-pulse">
                <CardContent className="p-6">
                  <div className="h-4 bg-muted rounded w-3/4 mb-2" />
                  <div className="h-3 bg-muted rounded w-1/2" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : error ? (
          <Card>
            <CardContent className="p-12 text-center">
              <p className="text-destructive mb-2">Failed to load tasks</p>
              <p className="text-sm text-muted-foreground mb-4">
                {error instanceof Error ? error.message : 'Unknown error occurred'}
              </p>
              <Button onClick={() => window.location.reload()} variant="outline">
                Retry
              </Button>
            </CardContent>
          </Card>
        ) : filteredTasks.length === 0 ? (
          <Card>
            <CardContent className="p-12 text-center">
              <p className="text-muted-foreground">
                {searchQuery || statusFilter !== 'all'
                  ? 'No tasks found matching your filters'
                  : 'No tasks yet. Create your first task to get started!'}
              </p>
              {!searchQuery && statusFilter === 'all' && (
                <Link href="/tasks/new">
                  <Button className="mt-4">
                    <Plus className="h-4 w-4 mr-2" />
                    Create Task
                  </Button>
                </Link>
              )}
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {filteredTasks.map((task) => {
              const config = getStatusConfig(task.status)
              const Icon = config.icon
              const isInProgress = ['in_progress', 'executing'].includes(task.status?.toLowerCase())

              return (
                <Card key={task.task_id} className="hover:shadow-md transition-shadow">
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-2">
                          <div className={`h-10 w-10 rounded-full ${config.color} flex items-center justify-center`}>
                            <Icon className={`h-5 w-5 text-white ${isInProgress ? 'animate-spin' : ''}`} />
                          </div>
                          <div className="flex-1">
                            <Link href={`/tasks/${task.task_id}`}>
                              <h3 className="text-lg font-semibold hover:text-primary transition-colors">
                                {task.description || 'Untitled Task'}
                              </h3>
                            </Link>
                            <div className="flex items-center space-x-2 mt-1">
                              <Badge variant={config.variant}>{config.label}</Badge>
                              {task.current_stage && (
                                <Badge variant="outline">{task.current_stage}</Badge>
                              )}
                              {task.progress_percent > 0 && (
                                <span className="text-sm text-muted-foreground">
                                  {task.progress_percent.toFixed(0)}% complete
                                </span>
                              )}
                            </div>
                          </div>
                        </div>

                        <div className="ml-13 space-y-1">
                          {task.agents_in_use && task.agents_in_use.length > 0 && (
                            <p className="text-sm text-muted-foreground">
                              Agents: {task.agents_in_use.join(', ')}
                            </p>
                          )}
                          <p className="text-xs text-muted-foreground">
                            Updated {formatDistanceToNow(new Date(task.updated_at), { addSuffix: true })}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <Link href={`/chat/${task.task_id}`}>
                          <Button variant="outline" size="sm" title="Chat about this task">
                            <MessageSquare className="h-4 w-4 mr-2" />
                            Chat
                          </Button>
                        </Link>
                        <Link href={`/tasks/${task.task_id}`}>
                          <Button variant="ghost" size="icon" title="View task details">
                            →
                          </Button>
                        </Link>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        )}
    </div>
  )
}
