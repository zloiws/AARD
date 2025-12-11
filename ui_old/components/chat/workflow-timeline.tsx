'use client'

import { useState, useEffect, useMemo, useRef } from 'react'
import Link from 'next/link'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { 
  ChevronDown, 
  ChevronRight, 
  Clock, 
  CheckCircle2, 
  XCircle, 
  Loader2,
  Play,
  Pause,
  RotateCcw,
  Brain,
  Code,
  Wrench,
  FileText,
  GitBranch,
  AlertCircle,
  Zap
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { SimpleMarkdown } from './simple-markdown'
import { ReasoningHighlight } from './reasoning-highlight'
import { cn } from '@/lib/utils'
import { useWorkflowEvents, useControlWorkflow } from '@/lib/hooks/use-api'
import { useQueryClient } from '@tanstack/react-query'
import { WorkflowGraph } from './workflow-graph'
import { EnhancedWorkflowGraph } from '@/components/workflow/enhanced-workflow-graph'

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

interface WorkflowTimelineProps {
  workflowId: string | null
  className?: string
  showGraph?: boolean  // Option to show/hide graph section
}

const getEventIcon = (eventType: string, eventSource: string) => {
  if (eventType === 'model_request' || eventType === 'model_response') {
    return Brain
  }
  if (eventType === 'tool_call' || eventType === 'tool_result') {
    return Wrench
  }
  if (eventType === 'plan_update') {
    return GitBranch
  }
  if (eventType === 'execution_step') {
    return Code
  }
  if (eventType === 'user_input') {
    return FileText
  }
  if (eventType === 'error') {
    return AlertCircle
  }
  if (eventType === 'completion') {
    return CheckCircle2
  }
  return Zap
}

const getEventColor = (eventType: string, status: string) => {
  if (status === 'failed' || eventType === 'error') {
    return 'destructive'
  }
  if (status === 'completed' || eventType === 'completion') {
    return 'default'
  }
  if (status === 'in_progress') {
    return 'secondary'
  }
  return 'outline'
}

const getSourceLabel = (source: string) => {
  const labels: Record<string, string> = {
    user: 'Пользователь',
    model: 'Модель',
    system: 'Система',
    planner_agent: 'Планировщик',
    coder_agent: 'Кодер',
    validator: 'Валидатор',
    tool: 'Инструмент',
  }
  return labels[source] || source
}

const getStageLabel = (stage: string) => {
  const labels: Record<string, string> = {
    user_request: 'Запрос пользователя',
    request_parsing: 'Разбор запроса',
    action_determination: 'Определение действий',
    execution: 'Выполнение',
    result: 'Результат',
    error: 'Ошибка',
  }
  return labels[stage] || stage
}

export function WorkflowTimeline({ workflowId, className, showGraph = true }: WorkflowTimelineProps) {
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set())
  const [isGraphExpanded, setIsGraphExpanded] = useState(true)
  const [wsConnected, setWsConnected] = useState(false)
  const [wsError, setWsError] = useState<string | null>(null)
  const [reconnectAttempts, setReconnectAttempts] = useState(0)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const controlWorkflow = useControlWorkflow()
  const queryClient = useQueryClient()
  
  // Load events via API hook with entities
  const { data: eventsData, isLoading } = useWorkflowEvents(workflowId, true)
  const events = eventsData?.events || []
  const entities = eventsData?.entities || []

  // Connect to WebSocket for real-time updates with reconnection logic
  useEffect(() => {
    if (!workflowId) return

    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/api/ws/events'
    const maxReconnectAttempts = 5
    const reconnectDelay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000) // Exponential backoff, max 30s

    const connectWebSocket = () => {
      try {
        // Close existing connection if any
        if (wsRef.current) {
          wsRef.current.close()
        }

        const ws = new WebSocket(`${wsUrl}/${workflowId}`)
        wsRef.current = ws

        ws.onopen = () => {
          setWsConnected(true)
          setWsError(null)
          setReconnectAttempts(0)
        }

        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data)
            if (message.type === 'event' && message.data) {
              // Invalidate query to refetch events immediately
              queryClient.invalidateQueries({ queryKey: ['workflow-events', workflowId] })
            }
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error)
            setWsError('Failed to parse WebSocket message')
          }
        }

        ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          setWsConnected(false)
          setWsError('WebSocket connection error')
        }

        ws.onclose = (event) => {
          setWsConnected(false)
          
          // Only attempt reconnect if it wasn't a clean close and we haven't exceeded max attempts
          if (event.code !== 1000 && reconnectAttempts < maxReconnectAttempts) {
            setWsError(`Reconnecting... (${reconnectAttempts + 1}/${maxReconnectAttempts})`)
            reconnectTimeoutRef.current = setTimeout(() => {
              setReconnectAttempts(prev => prev + 1)
            }, reconnectDelay)
          } else if (reconnectAttempts >= maxReconnectAttempts) {
            setWsError('Max reconnection attempts reached. Using polling instead.')
          } else {
            setWsError(null)
          }
        }
      } catch (error) {
        console.error('Failed to create WebSocket:', error)
        setWsError('Failed to create WebSocket connection')
        setWsConnected(false)
      }
    }

    connectWebSocket()

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [workflowId, queryClient, reconnectAttempts])

  const toggleEvent = (eventId: string) => {
    setExpandedEvents(prev => {
      const next = new Set(prev)
      if (next.has(eventId)) {
        next.delete(eventId)
      } else {
        next.add(eventId)
      }
      return next
    })
  }

  // Build event tree structure
  const eventTree = useMemo(() => {
    const eventMap = new Map<string, WorkflowEvent & { children: WorkflowEvent[] }>()
    const rootEvents: (WorkflowEvent & { children: WorkflowEvent[] })[] = []

    // First pass: create all nodes
    events.forEach(event => {
      eventMap.set(event.id, { ...event, children: [] })
    })

    // Second pass: build tree
    events.forEach(event => {
      const node = eventMap.get(event.id)!
      if (event.parent_event_id && eventMap.has(event.parent_event_id)) {
        const parent = eventMap.get(event.parent_event_id)!
        parent.children.push(node)
      } else {
        rootEvents.push(node)
      }
    })

    return rootEvents.sort((a, b) => 
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    )
  }, [events])

  if (!workflowId) {
    return null
  }

  const renderEvent = (event: WorkflowEvent & { children: WorkflowEvent[] }, depth = 0) => {
    const isExpanded = expandedEvents.has(event.id)
    const Icon = getEventIcon(event.event_type, event.event_source)
    const hasDetails = event.event_data || event.metadata || event.reasoning || event.task_id || event.plan_id || event.tool_id
    
    // Find related entities
    const relatedTask = event.task_id ? entities.find(e => e.id === event.task_id && e.type === 'task') : null
    const relatedPlan = event.plan_id ? entities.find(e => e.id === event.plan_id && e.type === 'plan') : null
    const relatedTool = event.tool_id ? entities.find(e => e.id === event.tool_id && e.type === 'tool') : null

    return (
      <div key={event.id} className={cn("mb-2", depth > 0 && "ml-6 border-l-2 border-muted pl-4")}>
        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-3">
            <div className="flex items-start gap-3">
              {/* Timeline indicator */}
              <div className="flex flex-col items-center pt-1">
                <div className={cn(
                  "rounded-full p-1.5",
                  event.status === 'completed' ? "bg-green-100 text-green-600" :
                  event.status === 'failed' ? "bg-red-100 text-red-600" :
                  event.status === 'in_progress' ? "bg-blue-100 text-blue-600 animate-pulse" :
                  "bg-muted text-muted-foreground"
                )}>
                  <Icon className="h-3 w-3" />
                </div>
                {event.status === 'in_progress' && (
                  <div className="w-0.5 h-full bg-blue-200 mt-1" />
                )}
              </div>

              {/* Event content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2 mb-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge variant={getEventColor(event.event_type, event.status) as any}>
                      {getSourceLabel(event.event_source)}
                    </Badge>
                    <Badge variant="outline">
                      {getStageLabel(event.stage)}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {formatDistanceToNow(new Date(event.timestamp), { addSuffix: true })}
                    </span>
                    {event.duration_ms && (
                      <span className="text-xs text-muted-foreground">
                        {(event.duration_ms / 1000).toFixed(2)}s
                      </span>
                    )}
                  </div>
                  {hasDetails && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => toggleEvent(event.id)}
                      className="h-6 w-6 p-0"
                    >
                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      )}
                    </Button>
                  )}
                </div>

                <p className="text-sm font-medium mb-1">{event.message}</p>

                {/* Expanded details */}
                {isExpanded && hasDetails && (
                  <div className="mt-3 space-y-3 border-t pt-3">
                    {/* Reasoning - highlight important parts */}
                    {event.event_data?.reasoning || event.metadata?.reasoning ? (
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                          <Brain className="h-4 w-4 text-primary" />
                          <span className="text-xs font-semibold">Размышления модели</span>
                        </div>
                        <div className="bg-muted/50 rounded p-2 text-xs border-l-2 border-primary/30">
                          <ReasoningHighlight 
                            content={event.event_data?.reasoning || event.metadata?.reasoning} 
                          />
                        </div>
                      </div>
                    ) : null}
                    
                    {/* Model Thinking step - combine reasoning with request/response */}
                    {event.event_type === 'model_response' && event.event_data?.reasoning ? (
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                          <Brain className="h-4 w-4 text-primary" />
                          <span className="text-xs font-semibold">Model Thinking</span>
                        </div>
                        <div className="bg-primary/5 rounded p-2 text-xs border-l-2 border-primary/50">
                          <ReasoningHighlight content={event.event_data.reasoning} />
                        </div>
                      </div>
                    ) : null}

                    {/* Prompt details - show even if empty to indicate prompt was used */}
                    {(event.event_data?.system_prompt || event.event_data?.user_prompt || event.event_data?.full_prompt || event.metadata?.system_prompt) ? (
                      <details className="text-xs" defaultOpen={false}>
                        <summary className="cursor-pointer font-semibold mb-1 flex items-center gap-2">
                          <span>📝 Промпт</span>
                          {event.event_data?.system_prompt && (
                            <Badge variant="outline" className="text-[9px]">System</Badge>
                          )}
                          {event.event_data?.user_prompt && (
                            <Badge variant="outline" className="text-[9px]">User</Badge>
                          )}
                        </summary>
                        <div className="bg-muted/50 rounded p-2 mt-1 space-y-2">
                          {event.event_data?.system_prompt && (
                            <div>
                              <div className="text-[10px] font-semibold mb-1 text-primary">System Prompt:</div>
                              <div className="text-xs">
                                <SimpleMarkdown content={event.event_data.system_prompt} />
                              </div>
                            </div>
                          )}
                          {event.event_data?.user_prompt && (
                            <div>
                              <div className="text-[10px] font-semibold mb-1">User Prompt:</div>
                              <div className="text-xs">
                                <SimpleMarkdown content={event.event_data.user_prompt} />
                              </div>
                            </div>
                          )}
                          {event.event_data?.full_prompt && !event.event_data?.system_prompt && !event.event_data?.user_prompt && (
                            <div>
                              <SimpleMarkdown content={event.event_data.full_prompt} />
                            </div>
                          )}
                          {event.metadata?.system_prompt && !event.event_data?.system_prompt && (
                            <div>
                              <div className="text-[10px] font-semibold mb-1 text-primary">System Prompt (from metadata):</div>
                              <div className="text-xs">
                                <SimpleMarkdown content={event.metadata.system_prompt} />
                              </div>
                            </div>
                          )}
                        </div>
                      </details>
                    ) : (
                      // Show indicator even if no prompt to indicate it was checked
                      event.event_type === 'model_request' || event.event_type === 'model_response' ? (
                        <div className="text-xs text-muted-foreground italic">
                          📝 Промпт не указан (используется дефолтный)
                        </div>
                      ) : null
                    )}

                    {/* Response */}
                    {event.event_data?.full_response || event.event_data?.response ? (
                      <details className="text-xs">
                        <summary className="cursor-pointer font-semibold mb-1">
                          Ответ модели
                        </summary>
                        <div className="bg-muted/50 rounded p-2 mt-1">
                          <SimpleMarkdown 
                            content={event.event_data?.full_response || event.event_data?.response} 
                          />
                        </div>
                      </details>
                    ) : null}

                    {/* Tool call details */}
                    {event.event_type === 'tool_call' && event.event_data ? (
                      <details className="text-xs">
                        <summary className="cursor-pointer font-semibold mb-1">
                          Параметры инструмента
                        </summary>
                        <div className="bg-muted/50 rounded p-2 mt-1">
                          <pre className="text-xs whitespace-pre-wrap">
                            {JSON.stringify(event.event_data, null, 2)}
                          </pre>
                        </div>
                      </details>
                    ) : null}

                    {/* Tool result */}
                    {event.event_type === 'tool_result' && event.event_data ? (
                      <details className="text-xs">
                        <summary className="cursor-pointer font-semibold mb-1">
                          Результат инструмента
                        </summary>
                        <div className="bg-muted/50 rounded p-2 mt-1">
                          <pre className="text-xs whitespace-pre-wrap">
                            {JSON.stringify(event.event_data, null, 2)}
                          </pre>
                        </div>
                      </details>
                    ) : null}

                    {/* Full event data */}
                    {event.event_data && Object.keys(event.event_data).length > 0 && (
                      <details className="text-xs">
                        <summary className="cursor-pointer font-semibold mb-1">
                          Полные данные события
                        </summary>
                        <div className="bg-muted/50 rounded p-2 mt-1">
                          <pre className="text-xs whitespace-pre-wrap overflow-x-auto">
                            {JSON.stringify(event.event_data, null, 2)}
                          </pre>
                        </div>
                      </details>
                    )}

                    {/* Metadata */}
                    {event.metadata && Object.keys(event.metadata).length > 0 && (
                      <details className="text-xs">
                        <summary className="cursor-pointer font-semibold mb-1">
                          Метаданные
                        </summary>
                        <div className="bg-muted/50 rounded p-2 mt-1">
                          <pre className="text-xs whitespace-pre-wrap overflow-x-auto">
                            {JSON.stringify(event.metadata, null, 2)}
                          </pre>
                        </div>
                      </details>
                    )}

                    {/* Related Entities */}
                    {(relatedTask || relatedPlan || relatedTool) && (
                      <div className="space-y-2">
                        <div className="text-xs font-semibold mb-1">Связанные сущности</div>
                        
                        {relatedTask && (
                          <details className="text-xs">
                            <summary className="cursor-pointer font-semibold mb-1 flex items-center gap-2">
                              <FileText className="h-3 w-3" />
                              Задача: {relatedTask.name}
                            </summary>
                            <div className="bg-muted/50 rounded p-2 mt-1 space-y-1">
                              <div className="flex items-center gap-2">
                                <span className="font-medium">ID:</span>
                                <code className="text-xs bg-background px-1 rounded">{relatedTask.id}</code>
                              </div>
                              {relatedTask.status && (
                                <div className="flex items-center gap-2">
                                  <span className="font-medium">Статус:</span>
                                  <Badge variant="outline" className="text-xs">
                                    {relatedTask.status}
                                  </Badge>
                                </div>
                              )}
                              <div className="text-xs text-muted-foreground">
                                <Link 
                                  href={`/tasks/${relatedTask.id}`}
                                  className="text-primary hover:underline"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  Открыть детали задачи →
                                </Link>
                              </div>
                            </div>
                          </details>
                        )}

                        {relatedPlan && (
                          <details className="text-xs">
                            <summary className="cursor-pointer font-semibold mb-1 flex items-center gap-2">
                              <Brain className="h-3 w-3" />
                              План: {relatedPlan.name}
                            </summary>
                            <div className="bg-muted/50 rounded p-2 mt-1 space-y-1">
                              <div className="flex items-center gap-2">
                                <span className="font-medium">ID:</span>
                                <code className="text-xs bg-background px-1 rounded">{relatedPlan.id}</code>
                              </div>
                              {relatedPlan.status && (
                                <div className="flex items-center gap-2">
                                  <span className="font-medium">Статус:</span>
                                  <Badge variant="outline" className="text-xs">
                                    {relatedPlan.status}
                                  </Badge>
                                </div>
                              )}
                              <div className="text-xs text-muted-foreground">
                                <Link 
                                  href={`/plans?task_id=${relatedTask?.id || ''}`}
                                  className="text-primary hover:underline"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  Просмотреть планы →
                                </Link>
                              </div>
                            </div>
                          </details>
                        )}

                        {relatedTool && (
                          <details className="text-xs">
                            <summary className="cursor-pointer font-semibold mb-1 flex items-center gap-2">
                              <Wrench className="h-3 w-3" />
                              Инструмент: {relatedTool.name}
                            </summary>
                            <div className="bg-muted/50 rounded p-2 mt-1 space-y-1">
                              <div className="flex items-center gap-2">
                                <span className="font-medium">ID:</span>
                                <code className="text-xs bg-background px-1 rounded">{relatedTool.id}</code>
                              </div>
                              {relatedTool.status && (
                                <div className="flex items-center gap-2">
                                  <span className="font-medium">Статус:</span>
                                  <Badge variant="outline" className="text-xs">
                                    {relatedTool.status}
                                  </Badge>
                                </div>
                              )}
                            </div>
                          </details>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* Children events */}
                {event.children.length > 0 && (
                  <div className="mt-2">
                    {event.children.map(child => renderEvent(child, depth + 1))}
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className={cn("space-y-2", className)}>
      <div className="space-y-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-semibold">Execution Timeline</span>
            {wsConnected ? (
              <Badge variant="outline" className="text-xs bg-green-50 text-green-700 border-green-200">
                Live
              </Badge>
            ) : wsError ? (
              <Badge variant="outline" className="text-xs bg-yellow-50 text-yellow-700 border-yellow-200" title={wsError}>
                Polling
              </Badge>
            ) : null}
          </div>
          <div className="flex items-center gap-1">
            <Button 
              variant="ghost" 
              size="sm" 
              className="h-7 px-2"
              onClick={() => workflowId && controlWorkflow.mutate({ workflowId, action: 'pause' })}
              title="Приостановить выполнение"
            >
              <Pause className="h-3 w-3" />
            </Button>
            <Button 
              variant="ghost" 
              size="sm" 
              className="h-7 px-2"
              onClick={() => workflowId && controlWorkflow.mutate({ workflowId, action: 'resume' })}
              title="Продолжить выполнение"
            >
              <Play className="h-3 w-3" />
            </Button>
            <Button 
              variant="ghost" 
              size="sm" 
              className="h-7 px-2"
              onClick={() => workflowId && controlWorkflow.mutate({ workflowId, action: 'cancel' })}
              title="Отменить выполнение"
            >
              <XCircle className="h-3 w-3" />
            </Button>
          </div>
        </div>

        {/* Enhanced Dependency Graph - only show if showGraph is true */}
        {showGraph && events.length > 0 && (
          <div className="mb-3">
            <button
              onClick={() => setIsGraphExpanded(!isGraphExpanded)}
              className="text-xs font-semibold cursor-pointer hover:text-foreground mb-2 flex items-center gap-2 w-full text-left"
            >
              {isGraphExpanded ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <ChevronRight className="h-3 w-3" />
              )}
              <GitBranch className="h-3 w-3" />
              Граф зависимостей компонентов и сущностей
            </button>
            {isGraphExpanded && (
              <Card className="mt-2">
                <CardContent className="p-0">
                  <EnhancedWorkflowGraph 
                    events={events} 
                    entities={entities}
                    height="500px"
                    className="w-full"
                  />
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : eventTree.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground text-sm">
          <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p>Ожидание событий...</p>
        </div>
      ) : (
        <div className="space-y-1 max-h-96 overflow-y-auto">
          {eventTree.map(event => renderEvent(event))}
        </div>
      )}
    </div>
  )
}
