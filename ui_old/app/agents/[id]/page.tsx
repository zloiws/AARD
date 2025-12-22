'use client'

import { useAgent, useActivateAgent, usePauseAgent, useDeprecateAgent, useAgentMemories, useAgentContext } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { formatDistanceToNow } from 'date-fns'
import { ArrowLeft, Bot, Activity, CheckCircle, XCircle, Settings, Clock, Edit, Play, Pause, Ban, Brain, Database, Clock as ClockIcon } from 'lucide-react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

const getStatusConfig = (status: string) => {
  const statusLower = status?.toLowerCase() || ''
  if (statusLower === 'active') {
    return { label: 'Active', icon: Activity, color: 'bg-green-500', variant: 'default' as const }
  }
  if (statusLower === 'paused') {
    return { label: 'Paused', icon: XCircle, color: 'bg-yellow-500', variant: 'secondary' as const }
  }
  if (statusLower === 'deprecated') {
    return { label: 'Deprecated', icon: XCircle, color: 'bg-red-500', variant: 'destructive' as const }
  }
  return { label: status || 'Unknown', icon: Bot, color: 'bg-gray-500', variant: 'outline' as const }
}

export default function AgentDetailPage() {
  const params = useParams()
  const agentId = params.id as string
  const { data: agent, isLoading } = useAgent(agentId)
  const { data: memories } = useAgentMemories(agentId, { limit: 50 })
  const { data: context } = useAgentContext(agentId)
  const activateAgent = useActivateAgent()
  const pauseAgent = usePauseAgent()
  const deprecateAgent = useDeprecateAgent()

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

  if (!agent) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card>
          <CardContent className="p-12 text-center">
            <p className="text-muted-foreground mb-4">Agent not found</p>
            <Link href="/agents">
              <Button variant="outline">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Agents
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    )
  }

  const config = getStatusConfig(agent.status)
  const Icon = config.icon
  const successRate = agent.success_rate ? parseFloat(agent.success_rate.replace('%', '')) : 0

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-6">
        <Link href="/agents">
          <Button variant="ghost" className="mb-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Agents
          </Button>
        </Link>
        <div className="flex items-center space-x-4">
          <div className={`h-12 w-12 rounded-full ${config.color} flex items-center justify-center`}>
            <Icon className="h-6 w-6 text-white" />
          </div>
          <div className="flex-1">
            <h1 className="text-3xl font-bold tracking-tight">{agent.name}</h1>
            <div className="flex items-center space-x-2 mt-2">
              <Badge variant={config.variant}>{config.label}</Badge>
              {agent.version > 1 && (
                <Badge variant="outline">v{agent.version}</Badge>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            <Link href={`/agents/${agentId}/edit`}>
              <Button variant="outline">
                <Edit className="h-4 w-4 mr-2" />
                Edit
              </Button>
            </Link>
            {agent.status?.toLowerCase() !== 'active' && (
              <Button
                variant="outline"
                onClick={() => activateAgent.mutate(agentId)}
                disabled={activateAgent.isPending}
              >
                <Play className="h-4 w-4 mr-2" />
                Activate
              </Button>
            )}
            {agent.status?.toLowerCase() === 'active' && (
              <Button
                variant="outline"
                onClick={() => pauseAgent.mutate(agentId)}
                disabled={pauseAgent.isPending}
              >
                <Pause className="h-4 w-4 mr-2" />
                Pause
              </Button>
            )}
            {agent.status?.toLowerCase() !== 'deprecated' && (
              <Button
                variant="outline"
                onClick={() => {
                  if (confirm('Are you sure you want to deprecate this agent?')) {
                    deprecateAgent.mutate(agentId)
                  }
                }}
                disabled={deprecateAgent.isPending}
              >
                <Ban className="h-4 w-4 mr-2" />
                Deprecate
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Agent Info */}
        <Card>
          <CardHeader>
            <CardTitle>Agent Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {agent.description && (
              <div>
                <p className="text-sm text-muted-foreground">Description</p>
                <p className="font-medium">{agent.description}</p>
              </div>
            )}
            <div>
              <p className="text-sm text-muted-foreground">Status</p>
              <p className="font-medium">{config.label}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Version</p>
              <p className="font-medium">{agent.version}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Created</p>
              <p className="font-medium">
                {formatDistanceToNow(new Date(agent.created_at), { addSuffix: true })}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Last Updated</p>
              <p className="font-medium">
                {formatDistanceToNow(new Date(agent.updated_at), { addSuffix: true })}
              </p>
            </div>
            {agent.last_used_at && (
              <div>
                <p className="text-sm text-muted-foreground">Last Used</p>
                <p className="font-medium">
                  {formatDistanceToNow(new Date(agent.last_used_at), { addSuffix: true })}
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Metrics */}
        <Card>
          <CardHeader>
            <CardTitle>Performance Metrics</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm text-muted-foreground">Success Rate</span>
                <span className="text-sm font-medium">{agent.success_rate || 'N/A'}</span>
              </div>
              {successRate > 0 && <Progress value={successRate} />}
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Total Tasks</p>
                <p className="text-2xl font-bold">{agent.total_tasks_executed || 0}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Successful</p>
                <p className="text-2xl font-bold text-green-600">{agent.successful_tasks || 0}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Failed</p>
                <p className="text-2xl font-bold text-red-600">{agent.failed_tasks || 0}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Avg Time</p>
                <p className="text-2xl font-bold">
                  {agent.average_execution_time ? `${agent.average_execution_time}ms` : 'N/A'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Capabilities */}
        {agent.capabilities && agent.capabilities.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Capabilities</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {agent.capabilities.map((cap) => (
                  <Badge key={cap} variant="outline">{cap}</Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Configuration */}
        <Card>
          <CardHeader>
            <CardTitle>Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {agent.model_preference && (
              <div>
                <p className="text-muted-foreground">Preferred Model</p>
                <p className="font-medium">{agent.model_preference}</p>
              </div>
            )}
            {agent.temperature && (
              <div>
                <p className="text-muted-foreground">Temperature</p>
                <p className="font-medium">{agent.temperature}</p>
              </div>
            )}
            <div>
              <p className="text-muted-foreground">Max Concurrent Tasks</p>
              <p className="font-medium">{agent.max_concurrent_tasks || 1}</p>
            </div>
            {agent.rate_limit_per_minute && (
              <div>
                <p className="text-muted-foreground">Rate Limit</p>
                <p className="font-medium">{agent.rate_limit_per_minute} / min</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Memory Section */}
      <div className="mt-6">
        <Tabs defaultValue="long-term" className="w-full">
          <TabsList>
            <TabsTrigger value="long-term">
              <Database className="h-4 w-4 mr-2" />
              Long-term Memory ({memories?.length || 0})
            </TabsTrigger>
            <TabsTrigger value="short-term">
              <ClockIcon className="h-4 w-4 mr-2" />
              Short-term Memory ({context?.length || 0})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="long-term" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle>Long-term Memory</CardTitle>
                <CardDescription>
                  Persistent memories stored by the agent (facts, experiences, patterns, rules)
                </CardDescription>
              </CardHeader>
              <CardContent>
                {!memories || memories.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <Brain className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No long-term memories yet</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {memories.map((memory) => (
                      <div
                        key={memory.id}
                        className="p-4 border rounded-lg hover:bg-accent transition-colors"
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Badge variant="outline">{memory.memory_type}</Badge>
                            {memory.importance > 0.7 && (
                              <Badge variant="default" className="text-xs">High Importance</Badge>
                            )}
                            {memory.tags && memory.tags.length > 0 && (
                              <div className="flex gap-1">
                                {memory.tags.slice(0, 3).map((tag) => (
                                  <Badge key={tag} variant="secondary" className="text-xs">
                                    {tag}
                                  </Badge>
                                ))}
                              </div>
                            )}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {formatDistanceToNow(new Date(memory.created_at), { addSuffix: true })}
                          </div>
                        </div>
                        {memory.summary && (
                          <p className="text-sm mb-2">{memory.summary}</p>
                        )}
                        <div className="text-xs text-muted-foreground">
                          <span>Importance: {(memory.importance * 100).toFixed(0)}%</span>
                          {memory.access_count > 0 && (
                            <span className="ml-4">Accessed {memory.access_count} times</span>
                          )}
                          {memory.source && (
                            <span className="ml-4">Source: {memory.source}</span>
                          )}
                        </div>
                        {memory.content && typeof memory.content === 'object' && (
                          <details className="mt-2">
                            <summary className="text-xs text-muted-foreground cursor-pointer">
                              View content
                            </summary>
                            <pre className="mt-2 p-2 bg-muted rounded text-xs overflow-auto">
                              {JSON.stringify(memory.content, null, 2)}
                            </pre>
                          </details>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="short-term" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle>Short-term Memory (Context)</CardTitle>
                <CardDescription>
                  Temporary context stored for current sessions (may expire)
                </CardDescription>
              </CardHeader>
              <CardContent>
                {!context || context.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <ClockIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No short-term context stored</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {context.map((ctx) => (
                      <div
                        key={ctx.id}
                        className="p-4 border rounded-lg hover:bg-accent transition-colors"
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Badge variant="outline">{ctx.context_key}</Badge>
                            {ctx.session_id && (
                              <Badge variant="secondary" className="text-xs">
                                Session: {ctx.session_id.slice(0, 8)}...
                              </Badge>
                            )}
                            {ctx.expires_at && new Date(ctx.expires_at) > new Date() && (
                              <Badge variant="default" className="text-xs">
                                Expires {formatDistanceToNow(new Date(ctx.expires_at), { addSuffix: true })}
                              </Badge>
                            )}
                            {ctx.expires_at && new Date(ctx.expires_at) <= new Date() && (
                              <Badge variant="destructive" className="text-xs">
                                Expired
                              </Badge>
                            )}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {formatDistanceToNow(new Date(ctx.created_at), { addSuffix: true })}
                          </div>
                        </div>
                        {ctx.content && typeof ctx.content === 'object' && (
                          <details className="mt-2">
                            <summary className="text-xs text-muted-foreground cursor-pointer">
                              View context
                            </summary>
                            <pre className="mt-2 p-2 bg-muted rounded text-xs overflow-auto">
                              {JSON.stringify(ctx.content, null, 2)}
                            </pre>
                          </details>
                        )}
                        {ctx.ttl_seconds && (
                          <div className="text-xs text-muted-foreground mt-2">
                            TTL: {ctx.ttl_seconds} seconds
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
