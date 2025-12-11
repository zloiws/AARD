'use client'

import { useMemo, useState, useEffect, useRef } from 'react'
import { logger } from '@/lib/utils/logger'
import {
  ReactFlow,
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  Panel,
  Handle,
  Position,
  ReactFlowInstance,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { cn } from '@/lib/utils'
import { SimpleMarkdown } from '@/components/ui/simple-markdown'
import { 
  Brain, 
  Code, 
  Wrench, 
  FileText, 
  GitBranch, 
  AlertCircle,
  User,
  Zap,
  CheckCircle2,
  XCircle,
  Loader2,
  Target,
  Users,
  FolderTree,
  Info,
  ChevronDown,
  ChevronRight,
  Clock,
  MessageSquare,
  Settings,
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
  task_id?: string
  plan_id?: string
  tool_id?: string
  approval_request_id?: string
  reasoning?: string
}

interface WorkflowEntity {
  id: string
  type: 'task' | 'plan' | 'agent' | 'tool' | 'approval'
  name: string
  status?: string
  created_by_event_id?: string
}

interface EnhancedWorkflowGraphProps {
  events: WorkflowEvent[]
  entities?: WorkflowEntity[]
  className?: string
  height?: string
  showEvents?: boolean  // Filter: show/hide event nodes
  showEntities?: boolean  // Filter: show/hide entity nodes
  onInit?: (instance: ReactFlowInstance) => void  // Callback when ReactFlow is initialized
}

// Component for event node content
function EventNodeContent({ 
  event, 
  entities = [],
  nodeType,
  Icon,
  color,
  StatusIcon
}: { 
  event: WorkflowEvent
  entities?: WorkflowEntity[]
  nodeType: string
  Icon: any
  color: string
  StatusIcon: any
}) {
  // Extract reasoning from event_data or metadata
  const reasoning = event.reasoning || event.event_data?.reasoning || event.metadata?.reasoning
  
  const hasDetails = reasoning || 
    event.event_data?.system_prompt || 
    event.event_data?.user_prompt || 
    event.event_data?.full_prompt ||
    event.metadata?.system_prompt ||
    event.event_data ||
    event.metadata ||
    event.task_id ||
    event.plan_id ||
    event.tool_id

  return (
    <div className="flex flex-col gap-1 p-1.5 min-w-[180px] max-w-[220px]">
      <div className="flex items-center gap-1.5 justify-between">
        <div className="flex items-center gap-1.5 flex-1 min-w-0">
          <Icon className="h-3 w-3 flex-shrink-0" style={{ color }} />
          <span className="text-[10px] font-semibold truncate uppercase">{event.event_source}</span>
          {StatusIcon && (
            <StatusIcon 
              className={cn(
                "h-2.5 w-2.5 flex-shrink-0",
                event.status === 'in_progress' && "animate-spin"
              )} 
              style={{ color }}
            />
          )}
        </div>
        {hasDetails && (
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="ghost" size="icon" className="h-4 w-4 p-0">
                <Info className="h-3 w-3" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-96 max-h-[600px] overflow-y-auto">
              <EventDetailsContent event={event} entities={entities} />
            </PopoverContent>
          </Popover>
        )}
      </div>
      
      <div className="flex items-center gap-1 text-[8px] text-muted-foreground">
        <Clock className="h-2.5 w-2.5" />
        <span>
          {new Date(event.timestamp).toLocaleTimeString('ru-RU', { 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit',
            fractionalSecondDigits: 2
          })}
        </span>
        {event.duration_ms && (
          <>
            <span>•</span>
            <span>{(event.duration_ms / 1000).toFixed(1)}s</span>
          </>
        )}
      </div>

      <p className="text-[10px] text-foreground line-clamp-2 leading-tight font-medium">
        {event.message}
      </p>

      {/* Reasoning preview */}
      {reasoning && (
        <div className="text-[9px] text-muted-foreground bg-muted/50 rounded p-1 line-clamp-2">
          <span className="font-semibold">💭 Reasoning:</span> {reasoning.substring(0, 100)}
          {reasoning.length > 100 && '...'}
        </div>
      )}

      {/* Prompt indicator */}
      {(event.event_type === 'model_request' || event.event_type === 'model_response' || 
        event.event_data?.system_prompt || event.event_data?.user_prompt || 
        event.event_data?.full_prompt || event.metadata?.system_prompt) && (
        <div className="flex items-center gap-1 mt-0.5">
          <MessageSquare className="h-2.5 w-2.5 text-primary" />
          <span className={cn(
            "text-[8px] font-semibold",
            (event.event_data?.system_prompt || event.event_data?.user_prompt || 
             event.event_data?.full_prompt || event.metadata?.system_prompt)
              ? "text-primary" 
              : "text-muted-foreground italic"
          )}>
            {(event.event_data?.system_prompt || event.event_data?.user_prompt || 
              event.event_data?.full_prompt || event.metadata?.system_prompt)
              ? "Промпт указан"
              : "Промпт не указан"}
          </span>
        </div>
      )}

      {/* Related entities */}
      {(event.task_id || event.plan_id || event.tool_id) && (
        <div className="flex items-center gap-1 mt-0.5 flex-wrap">
          {event.task_id && (
            <Badge variant="outline" className="text-[8px] px-1 py-0 h-3 bg-pink-50 border-pink-200">
              <Target className="h-2 w-2 mr-0.5" />
              Task
            </Badge>
          )}
          {event.plan_id && (
            <Badge variant="outline" className="text-[8px] px-1 py-0 h-3 bg-teal-50 border-teal-200">
              <FolderTree className="h-2 w-2 mr-0.5" />
              Plan
            </Badge>
          )}
          {event.tool_id && (
            <Badge variant="outline" className="text-[8px] px-1 py-0 h-3 bg-amber-50 border-amber-200">
              <Wrench className="h-2 w-2 mr-0.5" />
              Tool
            </Badge>
          )}
        </div>
      )}

      <div className="flex items-center gap-1 mt-0.5">
        <Badge variant="outline" className="text-[9px] px-1 py-0 h-4">
          {event.stage}
        </Badge>
        <Badge variant="secondary" className="text-[8px] px-1 py-0 h-4">
          {event.event_type}
        </Badge>
      </div>
    </div>
  )
}

// Component for detailed event information in popover
function EventDetailsContent({ 
  event, 
  entities = [] 
}: { 
  event: WorkflowEvent
  entities?: WorkflowEntity[]
}) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['reasoning', 'prompts']))
  
  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections)
    if (newExpanded.has(section)) {
      newExpanded.delete(section)
    } else {
      newExpanded.add(section)
    }
    setExpandedSections(newExpanded)
  }

  const relatedTask = event.task_id ? entities.find(e => e.id === event.task_id && e.type === 'task') : null
  const relatedPlan = event.plan_id ? entities.find(e => e.id === event.plan_id && e.type === 'plan') : null
  const relatedTool = event.tool_id ? entities.find(e => e.id === event.tool_id && e.type === 'tool') : null

  return (
    <div className="space-y-3 text-sm">
      <div className="border-b pb-2">
        <h3 className="font-semibold text-base">{event.event_type}</h3>
        <p className="text-muted-foreground text-xs mt-1">{event.message}</p>
        <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" />
          <span>{new Date(event.timestamp).toLocaleString('ru-RU')}</span>
          {event.duration_ms && (
            <>
              <span>•</span>
              <span>Длительность: {(event.duration_ms / 1000).toFixed(2)}s</span>
            </>
          )}
        </div>
      </div>

      {/* Reasoning */}
      {reasoning && (
        <details open={expandedSections.has('reasoning')}>
          <summary 
            className="cursor-pointer font-semibold mb-2 flex items-center gap-2"
            onClick={() => toggleSection('reasoning')}
          >
            {expandedSections.has('reasoning') ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
            <Brain className="h-4 w-4" />
            Логика принятия решения (Reasoning)
          </summary>
          <div className="bg-muted/50 rounded p-2 mt-1 text-xs">
            <SimpleMarkdown content={reasoning} />
          </div>
        </details>
      )}

      {/* Prompts */}
      {(event.event_data?.system_prompt || event.event_data?.user_prompt || 
        event.event_data?.full_prompt || event.metadata?.system_prompt) && (
        <details open={expandedSections.has('prompts')}>
          <summary 
            className="cursor-pointer font-semibold mb-2 flex items-center gap-2"
            onClick={() => toggleSection('prompts')}
          >
            {expandedSections.has('prompts') ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
            <MessageSquare className="h-4 w-4" />
            Промпты
          </summary>
          <div className="bg-muted/50 rounded p-2 mt-1 space-y-2 text-xs">
            {event.event_data?.system_prompt && (
              <div>
                <div className="text-[10px] font-semibold mb-1 text-primary">System Prompt:</div>
                <div className="text-xs"><SimpleMarkdown content={event.event_data.system_prompt} /></div>
              </div>
            )}
            {event.event_data?.user_prompt && (
              <div>
                <div className="text-[10px] font-semibold mb-1">User Prompt:</div>
                <div className="text-xs"><SimpleMarkdown content={event.event_data.user_prompt} /></div>
              </div>
            )}
            {event.event_data?.full_prompt && !event.event_data?.system_prompt && !event.event_data?.user_prompt && (
              <div>
                <div className="text-[10px] font-semibold mb-1">Full Prompt:</div>
                <div className="text-xs"><SimpleMarkdown content={event.event_data.full_prompt} /></div>
              </div>
            )}
            {event.metadata?.system_prompt && !event.event_data?.system_prompt && (
              <div>
                <div className="text-[10px] font-semibold mb-1 text-primary">System Prompt (from metadata):</div>
                <div className="text-xs"><SimpleMarkdown content={event.metadata.system_prompt} /></div>
              </div>
            )}
          </div>
        </details>
      )}

      {/* Related Entities */}
      {(relatedTask || relatedPlan || relatedTool) && (
        <details open={expandedSections.has('entities')}>
          <summary 
            className="cursor-pointer font-semibold mb-2 flex items-center gap-2"
            onClick={() => toggleSection('entities')}
          >
            {expandedSections.has('entities') ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
            <Settings className="h-4 w-4" />
            Связанные сущности
          </summary>
          <div className="space-y-2 mt-1 text-xs">
            {relatedTask && (
              <div className="bg-pink-50 border border-pink-200 rounded p-2">
                <div className="flex items-center gap-2 font-semibold mb-1">
                  <Target className="h-3 w-3" />
                  Задача: {relatedTask.name}
                </div>
                <div className="text-muted-foreground">ID: {relatedTask.id}</div>
                {relatedTask.status && (
                  <Badge variant="outline" className="text-xs mt-1">{relatedTask.status}</Badge>
                )}
              </div>
            )}
            {relatedPlan && (
              <div className="bg-teal-50 border border-teal-200 rounded p-2">
                <div className="flex items-center gap-2 font-semibold mb-1">
                  <FolderTree className="h-3 w-3" />
                  План: {relatedPlan.name}
                </div>
                <div className="text-muted-foreground">ID: {relatedPlan.id}</div>
                {relatedPlan.status && (
                  <Badge variant="outline" className="text-xs mt-1">{relatedPlan.status}</Badge>
                )}
              </div>
            )}
            {relatedTool && (
              <div className="bg-amber-50 border border-amber-200 rounded p-2">
                <div className="flex items-center gap-2 font-semibold mb-1">
                  <Wrench className="h-3 w-3" />
                  Инструмент: {relatedTool.name}
                </div>
                <div className="text-muted-foreground">ID: {relatedTool.id}</div>
                {relatedTool.status && (
                  <Badge variant="outline" className="text-xs mt-1">{relatedTool.status}</Badge>
                )}
              </div>
            )}
          </div>
        </details>
      )}

      {/* Event Data */}
      {event.event_data && Object.keys(event.event_data).length > 0 && (
        <details open={expandedSections.has('data')}>
          <summary 
            className="cursor-pointer font-semibold mb-2 flex items-center gap-2"
            onClick={() => toggleSection('data')}
          >
            {expandedSections.has('data') ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
            <FileText className="h-4 w-4" />
            Данные события
          </summary>
          <div className="bg-muted/50 rounded p-2 mt-1 text-xs">
            <pre className="whitespace-pre-wrap text-[10px] overflow-x-auto">
              {JSON.stringify(event.event_data, null, 2)}
            </pre>
          </div>
        </details>
      )}

      {/* Metadata */}
      {event.metadata && Object.keys(event.metadata).length > 0 && (
        <details open={expandedSections.has('metadata')}>
          <summary 
            className="cursor-pointer font-semibold mb-2 flex items-center gap-2"
            onClick={() => toggleSection('metadata')}
          >
            {expandedSections.has('metadata') ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
            <Settings className="h-4 w-4" />
            Метаданные
          </summary>
          <div className="bg-muted/50 rounded p-2 mt-1 text-xs">
            <pre className="whitespace-pre-wrap text-[10px] overflow-x-auto">
              {JSON.stringify(event.metadata, null, 2)}
            </pre>
          </div>
        </details>
      )}
    </div>
  )
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

const getEntityNodeType = (entityType: string) => {
  const types: Record<string, string> = {
    task: 'task',
    plan: 'plan',
    agent: 'agent',
    tool: 'tool',
    approval: 'approval',
  }
  return types[entityType] || 'default'
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
    task: '#ec4899',
    plan: '#14b8a6',
    agent: '#8b5cf6',
    approval: '#f59e0b',
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
    task: Target,
    plan: FolderTree,
    agent: Users,
    approval: CheckCircle2,
  }
  return icons[nodeType] || Zap
}

const getStatusIcon = (status: string) => {
  if (status === 'completed') return CheckCircle2
  if (status === 'failed') return XCircle
  if (status === 'in_progress') return Loader2
  return null
}

// Dagre layout function - using dynamic import for client-side only
// Simple layout function without dagre (fallback) - deterministic small grid/timeline
const getSimpleLayout = (nodes: Node[], edges: Edge[], events?: WorkflowEvent[]) => {
  // Separate event and entity nodes
  const eventNodes: Node[] = []
  const entityNodes: Node[] = []

  nodes.forEach((node) => {
    if (node.id.startsWith('event-')) {
      eventNodes.push(node)
    } else {
      entityNodes.push(node)
    }
  })

  // Sort events by timestamp if available, else by id
  if (events && events.length > 0) {
    const eventOrder = new Map<string, number>()
    const sortedEvents = [...events].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    )
    sortedEvents.forEach((ev, idx) => {
      eventOrder.set(`event-${ev.id}`, idx)
    })
    eventNodes.sort((a, b) => (eventOrder.get(a.id) ?? 0) - (eventOrder.get(b.id) ?? 0))
  }

  // Position events in a single row (timeline)
  const eventSpacingX = 240
  const eventStartX = 100
  const eventY = 120
  eventNodes.forEach((node, idx) => {
    node.position = { x: eventStartX + idx * eventSpacingX, y: eventY }
    node.targetPosition = 'left' as any
    node.sourcePosition = 'right' as any
  })

  // Position entities in a grid under the events
  const entitySpacingX = 220
  const entitySpacingY = 140
  const entityStartX = 120
  const entityStartY = 320
  entityNodes.forEach((node, idx) => {
    const col = idx % 4
    const row = Math.floor(idx / 4)
    node.position = {
      x: entityStartX + col * entitySpacingX,
      y: entityStartY + row * entitySpacingY,
    }
    node.targetPosition = 'top' as any
    node.sourcePosition = 'bottom' as any
  })

  const allNodes = [...eventNodes, ...entityNodes]

  // Ensure at least some positions are set even if empty
  if (allNodes.length === 0) {
    return { nodes: [], edges }
  }

  return { nodes: allNodes, edges }
}

const getLayoutedElements = async (
  nodes: Node[], 
  edges: Edge[], 
  direction: 'TB' | 'LR' = 'LR', // Default to horizontal (left-to-right)
  events?: WorkflowEvent[]
) => {
  // Try to use dagre if available, fallback to simple layout
  try {
    // Dynamic import to avoid SSR issues
    // dagre is a CommonJS module, handle it properly
    const dagreModule: any = await import('dagre')
    // dagre exports as default in ESM, but may be namespaced in CJS
    const dagre = dagreModule.default?.default || dagreModule.default || dagreModule || dagreModule.dagre
    
    if (!dagre || !dagre.graphlib) {
      logger.warn('dagre not available, using simple layout')
      return getSimpleLayout(nodes, edges, events)
    }
    
    const dagreGraph = new dagre.graphlib.Graph()
    dagreGraph.setDefaultEdgeLabel(() => ({}))
    dagreGraph.setGraph({ 
      rankdir: direction, // 'LR' for left-to-right (timeline)
      nodesep: 80, // Horizontal spacing between nodes
      ranksep: 150, // Vertical spacing between ranks
      marginx: 50,
      marginy: 50,
      align: 'UL',
    })

    nodes.forEach((node) => {
      dagreGraph.setNode(node.id, { width: 180, height: 100 })
    })

    edges.forEach((edge) => {
      dagreGraph.setEdge(edge.source, edge.target)
    })

    dagre.layout(dagreGraph)

    nodes.forEach((node) => {
      const nodeWithPosition = dagreGraph.node(node.id)
      node.targetPosition = direction === 'LR' ? 'left' as any : 'top' as any
      node.sourcePosition = direction === 'LR' ? 'right' as any : 'bottom' as any
      node.position = {
        x: nodeWithPosition.x - 90,
        y: nodeWithPosition.y - 50,
      }
    })

    return { nodes, edges }
  } catch (error) {
    // Fallback to simple layout if dagre is not available
    logger.warn('Failed to load dagre, using simple layout:', error)
    return getSimpleLayout(nodes, edges, events)
  }
}

export function EnhancedWorkflowGraph({ 
  events, 
  entities = [], 
  className,
  height = '600px',
  showEvents = true,
  showEntities = true,
  onInit
}: EnhancedWorkflowGraphProps) {
  const [layoutedNodes, setLayoutedNodes] = useState<Node[]>([])
  const [layoutedEdges, setLayoutedEdges] = useState<Edge[]>([])
  const [localShowEvents, setLocalShowEvents] = useState(showEvents)
  const [localShowEntities, setLocalShowEntities] = useState(showEntities)
  const reactFlowInstanceRef = useRef<ReactFlowInstance | null>(null)
  
  // Sync with props
  useEffect(() => {
    setLocalShowEvents(showEvents)
    setLocalShowEntities(showEntities)
  }, [showEvents, showEntities])
  
  // Calculate filtered data for use in Panel and other places
  const filteredEvents = localShowEvents ? (events || []) : []
  const filteredEntities = localShowEntities ? (entities || []) : []

  const { nodes, edges } = useMemo(() => {
    // Filter events and entities based on show flags
    const filteredEvents = localShowEvents ? (events || []) : []
    const filteredEntities = localShowEntities ? (entities || []) : []
    
    logger.debug('EnhancedWorkflowGraph: useMemo - filtering', {
      totalEvents: events.length,
      totalEntities: entities.length,
      filteredEvents: filteredEvents.length,
      filteredEntities: filteredEntities.length,
      localShowEvents,
      localShowEntities,
    })
    
    if (filteredEvents.length === 0 && filteredEntities.length === 0) {
      logger.warn('EnhancedWorkflowGraph: No nodes after filtering')
      return { nodes: [], edges: [] }
    }

    const nodeMap = new Map<string, Node>()
    const edgeList: Edge[] = []
    const eventMap = new Map(filteredEvents.map(e => [e.id, e]))
    const entityMap = new Map(filteredEntities.map(e => [e.id, e]))

    // Create event nodes (only if showEvents is true)
    filteredEvents.forEach((event) => {
      const nodeType = getNodeType(event.event_source, event.event_type)
      const Icon = getNodeIcon(nodeType)
      const color = getNodeColor(event.status, nodeType)
      const StatusIcon = getStatusIcon(event.status)

      const node: Node = {
        id: `event-${event.id}`,
        type: 'default',
        position: { x: Math.random() * 100, y: Math.random() * 100 }, // Temporary random position, will be calculated by layout
        draggable: true,
        data: {
          label: (
            <EventNodeContent 
              event={event}
              entities={entities}
              nodeType={nodeType}
              Icon={Icon}
              color={color}
              StatusIcon={StatusIcon}
            />
          ),
          event: event, // Store full event for tooltips
        },
        // Ensure node is visible
        hidden: false,
        style: {
          background: '#fff',
          border: `2px solid ${color}`,
          borderRadius: '6px',
          boxShadow: event.status === 'in_progress' ? `0 0 6px ${color}40` : 'none',
          width: 220,
          minHeight: 100,
        },
      }

      nodeMap.set(`event-${event.id}`, node)
    })

    // Create entity nodes (only if showEntities is true)
    filteredEntities.forEach((entity) => {
      const nodeType = getEntityNodeType(entity.type)
      const Icon = getNodeIcon(nodeType)
      const color = getNodeColor(entity.status || 'completed', nodeType)
      const StatusIcon = getStatusIcon(entity.status || 'completed')
      
      const node: Node = {
        id: `entity-${entity.id}`,
        type: 'default',
        position: { x: Math.random() * 100, y: Math.random() * 100 }, // Temporary random position, will be calculated by layout
        draggable: true,
        data: {
          label: (
            <div className="flex flex-col gap-0.5 p-1.5 min-w-[140px] max-w-[160px]">
              <div className="flex items-center gap-1.5">
                <Icon className="h-3 w-3 flex-shrink-0" style={{ color }} />
                <span className="text-[10px] font-semibold truncate uppercase">{entity.type}</span>
                {StatusIcon && (
                  <StatusIcon 
                    className={cn(
                      "h-2.5 w-2.5 flex-shrink-0",
                      entity.status === 'in_progress' && "animate-spin"
                    )} 
                    style={{ color }}
                  />
                )}
              </div>
              <p className="text-[10px] text-muted-foreground line-clamp-2 font-medium leading-tight">
                {entity.name}
              </p>
              {entity.status && (
                <Badge variant="outline" className="text-[9px] px-1 py-0 h-4 w-fit">
                  {entity.status}
                </Badge>
              )}
            </div>
          ),
        },
        style: {
          background: '#f8fafc',
          border: `2px solid ${color}`,
          borderRadius: '6px',
          boxShadow: `0 2px 6px ${color}30`,
          width: 160,
          height: 'auto',
        },
      }

      nodeMap.set(`entity-${entity.id}`, node)
    })

    // Sort events by timestamp to create sequential flow (timeline)
    const sortedEvents = [...filteredEvents].sort((a, b) => 
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    )

    // Create edges between events showing the flow of actions
    sortedEvents.forEach((event, index) => {
      // Primary: Parent-child relationship (explicit dependency)
      if (event.parent_event_id && eventMap.has(event.parent_event_id)) {
        const parentEvent = eventMap.get(event.parent_event_id)!
        edgeList.push({
          id: `parent-${event.parent_event_id}-event-${event.id}`,
          source: `event-${event.parent_event_id}`,
          target: `event-${event.id}`,
          type: 'smoothstep',
          animated: event.status === 'in_progress',
          style: {
            stroke: getNodeColor(event.status, getNodeType(event.event_source, event.event_type)),
            strokeWidth: 3,
          },
          label: `${event.event_type}`,
          labelStyle: { fontSize: 9, fill: '#64748b', fontWeight: 'bold', background: 'white', padding: '2px 4px' },
          markerEnd: {
            type: 'arrowclosed',
            color: getNodeColor(event.status, getNodeType(event.event_source, event.event_type)),
            width: 20,
            height: 20,
          },
        })
      } 
      // Secondary: Sequential flow (timeline progression) - only if no parent
      else if (index > 0) {
        const prevEvent = sortedEvents[index - 1]
        // Only add sequential edge if events are close in time (< 5 seconds) or same source
        const timeDiff = new Date(event.timestamp).getTime() - new Date(prevEvent.timestamp).getTime()
        if (timeDiff < 5000 || event.event_source === prevEvent.event_source) {
          edgeList.push({
            id: `seq-${prevEvent.id}-${event.id}`,
            source: `event-${prevEvent.id}`,
            target: `event-${event.id}`,
            type: 'smoothstep',
            animated: event.status === 'in_progress',
            style: {
              stroke: '#94a3b8',
              strokeWidth: 2,
              strokeDasharray: '5,5',
            },
            label: `${(timeDiff / 1000).toFixed(1)}s`,
            labelStyle: { fontSize: 8, fill: '#94a3b8', background: 'white', padding: '1px 3px' },
            markerEnd: {
              type: 'arrowclosed',
              color: '#94a3b8',
              width: 15,
              height: 15,
            },
          })
        }
      }
    })

    // Create edges from events to entities (when event creates/uses entity)
    filteredEvents.forEach((event) => {
      if (event.task_id && entityMap.has(event.task_id)) {
        edgeList.push({
          id: `event-${event.id}-entity-${event.task_id}`,
          source: `event-${event.id}`,
          target: `entity-${event.task_id}`,
          type: 'smoothstep',
          style: {
            stroke: '#ec4899',
            strokeWidth: 2,
            strokeDasharray: '5,5',
          },
          label: 'creates',
          labelStyle: { fontSize: 10, fill: '#ec4899' },
        })
      }
      if (event.plan_id && entityMap.has(event.plan_id)) {
        edgeList.push({
          id: `event-${event.id}-entity-${event.plan_id}`,
          source: `event-${event.id}`,
          target: `entity-${event.plan_id}`,
          type: 'smoothstep',
          style: {
            stroke: '#14b8a6',
            strokeWidth: 2,
            strokeDasharray: '5,5',
          },
          label: 'creates',
          labelStyle: { fontSize: 10, fill: '#14b8a6' },
        })
      }
      if (event.tool_id && entityMap.has(event.tool_id)) {
        edgeList.push({
          id: `event-${event.id}-entity-${event.tool_id}`,
          source: `event-${event.id}`,
          target: `entity-${event.tool_id}`,
          type: 'smoothstep',
          style: {
            stroke: '#f59e0b',
            strokeWidth: 2,
            strokeDasharray: '5,5',
          },
          label: 'uses',
          labelStyle: { fontSize: 10, fill: '#f59e0b' },
        })
      }
    })

    const resultNodes = Array.from(nodeMap.values())
    const resultEdges = edgeList
    
    logger.debug('EnhancedWorkflowGraph: Nodes created', {
      totalNodes: resultNodes.length,
      totalEdges: resultEdges.length,
      eventNodes: filteredEvents.length,
      entityNodes: filteredEntities.length,
    })
    
    return { nodes: resultNodes, edges: resultEdges }
  }, [events, entities, localShowEvents, localShowEntities])

  // Apply dagre layout asynchronously
  useEffect(() => {
    if (nodes.length === 0) {
      logger.debug('EnhancedWorkflowGraph: No nodes to layout', {
        showEvents: localShowEvents,
        showEntities: localShowEntities,
        eventsCount: events.length,
        entitiesCount: entities.length,
      })
      setLayoutedNodes([])
      setLayoutedEdges([])
      return
    }

    logger.debug('EnhancedWorkflowGraph: Starting layout calculation', {
      nodesCount: nodes.length,
      edgesCount: edges.length,
      eventsCount: events.length,
      entitiesCount: entities.length,
      showEvents: localShowEvents,
      showEntities: localShowEntities,
    })

    // Reset layouted nodes to trigger recalculation
    getLayoutedElements(nodes, edges, 'LR', events).then((layouted) => {
      logger.debug('EnhancedWorkflowGraph: Layout completed', {
        layoutedNodesCount: layouted.nodes.length,
        layoutedEdgesCount: layouted.edges.length,
      })
      
      // Ensure all nodes are draggable and have valid positions
      const nodesWithValidPositions = layouted.nodes.map((node, index) => {
        const hasValidPosition = node.position && 
          (node.position.x !== 0 || node.position.y !== 0) &&
          !isNaN(node.position.x) && !isNaN(node.position.y)
        
        if (!hasValidPosition) {
          // Fallback grid position
          const cols = Math.ceil(Math.sqrt(layouted.nodes.length))
          const row = Math.floor(index / cols)
          const col = index % cols
          return {
            ...node,
            draggable: true,
            position: { x: col * 250 + 100, y: row * 150 + 100 },
          }
        }
        
        return {
          ...node,
          draggable: true,
          position: node.position,
        }
      })
      
      logger.debug('EnhancedWorkflowGraph: Setting layouted nodes', {
        count: nodesWithValidPositions.length,
        samplePositions: nodesWithValidPositions.slice(0, 3).map(n => ({
          id: n.id,
          position: n.position,
        })),
      })
      
      setLayoutedNodes(nodesWithValidPositions)
      setLayoutedEdges(layouted.edges)
    }).catch((error) => {
      logger.error('EnhancedWorkflowGraph: Failed to apply layout:', error)
      // Fallback: distribute nodes in a grid
      const fallbackNodes = nodes.map((node, index) => {
        const cols = Math.ceil(Math.sqrt(nodes.length))
        const row = Math.floor(index / cols)
        const col = index % cols
        return {
          ...node,
          draggable: true,
          position: { x: col * 250 + 100, y: row * 150 + 100 },
        }
      })
      logger.debug('EnhancedWorkflowGraph: Using fallback grid layout', {
        count: fallbackNodes.length,
      })
      setLayoutedNodes(fallbackNodes)
      setLayoutedEdges(edges)
    })
  }, [nodes, edges, events, localShowEvents, localShowEntities])


  // Use layouted nodes/edges if available, otherwise use original with fallback positions
  let displayNodes = layoutedNodes.length > 0 ? layoutedNodes : nodes
  const displayEdges = layoutedEdges.length > 0 ? layoutedEdges : edges

  // If no nodes after layout, use original nodes with grid positions
  if (displayNodes.length === 0 && nodes.length > 0) {
    logger.debug('EnhancedWorkflowGraph: No layouted nodes, using original with grid positions')
    displayNodes = nodes.map((node, index) => {
      const cols = Math.ceil(Math.sqrt(nodes.length))
      const row = Math.floor(index / cols)
      const col = index % cols
      return {
        ...node,
        draggable: true,
        position: node.position && (node.position.x !== 0 || node.position.y !== 0)
          ? node.position
          : { x: col * 250 + 100, y: row * 150 + 100 },
      }
    })
  }

  // Ensure all nodes are draggable and have valid positions
  const draggableNodes = useMemo(() => {
    if (!displayNodes || displayNodes.length === 0) {
      logger.warn('EnhancedWorkflowGraph: No display nodes to process')
      return []
    }
    
    const processed = displayNodes.map((node, index) => {
      const hasValidPosition = node.position && 
        !isNaN(node.position.x) && !isNaN(node.position.y) &&
        (node.position.x !== 0 || node.position.y !== 0) &&
        node.position.x > -10000 && node.position.x < 10000 &&
        node.position.y > -10000 && node.position.y < 10000
      
      if (!hasValidPosition) {
        // Fallback grid position
        const cols = Math.ceil(Math.sqrt(displayNodes.length))
        const row = Math.floor(index / cols)
        const col = index % cols
        const fallbackPos = { x: col * 250 + 100, y: row * 150 + 100 }
        logger.debug(`EnhancedWorkflowGraph: Using fallback position for node ${node.id}`, fallbackPos)
        return {
          ...node,
          draggable: true,
          position: fallbackPos,
        }
      }
      
      return {
        ...node,
        draggable: true,
        position: node.position ?? { x: 100, y: 100 },
      }
    })
    
    logger.debug('EnhancedWorkflowGraph: Processed draggable nodes', {
      count: processed.length,
      samplePositions: processed.slice(0, 3).map(n => ({
        id: n.id,
        position: n.position,
      })),
    })
    
    return processed
  }, [displayNodes])

  // Debug logging (only in development)
  useEffect(() => {
    logger.debug('EnhancedWorkflowGraph: Render state', {
      eventsCount: events.length,
      nodesCount: nodes.length,
      layoutedNodesCount: layoutedNodes.length,
      displayNodesCount: displayNodes.length,
      draggableNodesCount: draggableNodes.length,
      displayEdgesCount: displayEdges.length,
    })
    
    if (draggableNodes.length > 0) {
      const samplePositions = draggableNodes.slice(0, 3).map(n => ({
        id: n.id,
        position: n.position,
        x: n.position?.x,
        y: n.position?.y,
        hasData: !!n.data,
      }))
      logger.debug('EnhancedWorkflowGraph: Sample node positions', samplePositions)
      
      // Check if positions are valid
      const invalidPositions = draggableNodes.filter(n => 
        !n.position || 
        isNaN(n.position.x) || 
        isNaN(n.position.y) ||
        n.position.x < -10000 || 
        n.position.x > 10000 ||
        n.position.y < -10000 || 
        n.position.y > 10000
      )
      if (invalidPositions.length > 0) {
        logger.warn('EnhancedWorkflowGraph: Invalid positions found', invalidPositions.length)
      }
    }
  }, [draggableNodes.length, displayEdges.length, events.length, nodes.length, layoutedNodes.length, displayNodes.length])

  // Fit view when layouted nodes are ready
  useEffect(() => {
    if (layoutedNodes.length === 0 || !reactFlowInstanceRef.current) return
    
    // Small delay to ensure ReactFlow is ready
    const timeoutId = setTimeout(() => {
      try {
        reactFlowInstanceRef.current?.fitView({
          padding: 0.2,
          minZoom: 0.3,
          maxZoom: 1.2,
          duration: 300,
        })
      } catch (e) {
        console.warn('EnhancedWorkflowGraph: fitView failed', e)
      }
    }, 100)
    
    return () => clearTimeout(timeoutId)
  }, [layoutedNodes.length, layoutedEdges.length])

  if (draggableNodes.length === 0) {
    return (
      <div className={cn("flex flex-col items-center justify-center h-64 text-muted-foreground p-4", className)}>
        <p className="text-sm font-medium mb-2">Нет узлов для визуализации</p>
        <div className="text-xs text-muted-foreground space-y-1 text-left">
          <p>Событий всего: {events.length}, Отфильтровано: {filteredEvents.length}</p>
          <p>Сущностей всего: {entities.length}, Отфильтровано: {filteredEntities.length}</p>
          <p>Узлов создано: {nodes.length}, Layouted: {layoutedNodes.length}, Display: {displayNodes.length}</p>
          <p>Показать события: {localShowEvents ? 'Да' : 'Нет'}</p>
          <p>Показать сущности: {localShowEntities ? 'Да' : 'Нет'}</p>
          {events.length === 0 && entities.length === 0 && (
            <p className="text-red-500 mt-2">⚠️ Данные не загружены или пусты</p>
          )}
        </div>
      </div>
    )
  }

  // Log final nodes being passed to ReactFlow (only in development)
  logger.debug('EnhancedWorkflowGraph: Passing to ReactFlow', {
    nodesCount: draggableNodes.length,
    edgesCount: displayEdges.length,
    showEvents: localShowEvents,
    showEntities: localShowEntities,
    eventsCount: events.length,
    entitiesCount: entities.length,
    firstNode: draggableNodes[0] ? {
      id: draggableNodes[0].id,
      position: draggableNodes[0].position,
      hasData: !!draggableNodes[0].data,
      hasLabel: !!draggableNodes[0].data?.label,
      style: draggableNodes[0].style,
    } : null,
    allNodeIds: draggableNodes.map(n => n.id),
  })

  // Ensure we have valid nodes before rendering
  if (!draggableNodes || draggableNodes.length === 0) {
    return (
      <div className={cn("flex flex-col items-center justify-center h-64 text-muted-foreground p-4", className)}>
        <p className="text-sm font-medium mb-2">Нет узлов для визуализации</p>
        <div className="text-xs text-muted-foreground space-y-1 text-left">
          <p>Событий: {events.length}, Сущностей: {entities.length}</p>
          <p>Узлов создано: {nodes.length}, Layouted: {layoutedNodes.length}</p>
          {events.length > 0 && (
            <p className="text-yellow-500 mt-2">⚠️ События есть, но узлы не созданы. Проверьте данные.</p>
          )}
        </div>
      </div>
    )
  }

  return (
    <TooltipProvider>
      <div className={cn("w-full", className)} style={{ height }}>
          <ReactFlow
          nodes={draggableNodes}
          edges={displayEdges}
          onInit={(instance) => {
            reactFlowInstanceRef.current = instance
            onInit?.(instance)
            logger.debug('EnhancedWorkflowGraph: ReactFlow initialized', {
              nodesCount: draggableNodes.length,
            })
            // Initial fitView after a short delay to ensure nodes are rendered
            setTimeout(() => {
              try {
                if (draggableNodes.length > 0) {
                  instance.fitView({
                    padding: 0.3,
                    minZoom: 0.4,
                    maxZoom: 1.5,
                    duration: 400,
                  })
                  logger.debug('EnhancedWorkflowGraph: fitView called')
                }
              } catch (e) {
                logger.warn('EnhancedWorkflowGraph: initial fitView failed', e)
              }
            }, 500) // Increased delay to ensure rendering
          }}
          fitView
          fitViewOptions={{ padding: 0.3, minZoom: 0.4, maxZoom: 1.5 }}
          defaultViewport={{ x: 0, y: 0, zoom: 1 }}
          nodesDraggable={true}
          nodesConnectable={false}
          elementsSelectable={true}
          selectNodesOnDrag={true}
          panOnDrag={[1, 2]} // Allow panning with middle/right mouse button, left button drags nodes
          minZoom={0.1}
          maxZoom={2}
          preventScrolling={false}
          onNodesChange={(changes) => {
            // Update node positions when dragged
            setLayoutedNodes(prevNodes => {
              const updated = [...prevNodes]
              changes.forEach(change => {
                if (change.type === 'position' && change.position) {
                  const nodeIndex = updated.findIndex(n => n.id === change.id)
                  if (nodeIndex !== -1) {
                    updated[nodeIndex] = {
                      ...updated[nodeIndex],
                      position: change.position,
                    }
                  }
                }
              })
              return updated
            })
          }}
        >
        <Background />
        <Controls />
        <MiniMap 
          nodeColor={(node) => {
            const event = events.find(e => node.id === `event-${e.id}`)
            const entity = entities.find(e => node.id === `entity-${e.id}`)
            if (event) {
              return getNodeColor(event.status, getNodeType(event.event_source, event.event_type))
            }
            if (entity) {
              return getNodeColor(entity.status || 'completed', getEntityNodeType(entity.type))
            }
            return '#94a3b8'
          }}
          maskColor="rgba(0, 0, 0, 0.1)"
        />
        <Panel position="top-left" className="bg-background/80 backdrop-blur-sm rounded-lg p-2 border">
          <div className="flex items-center gap-4 text-xs">
            <button
              onClick={() => setLocalShowEvents(!localShowEvents)}
              className={`flex items-center gap-2 px-2 py-1 rounded transition-colors ${
                localShowEvents 
                  ? 'bg-blue-500/20 text-blue-600 dark:text-blue-400' 
                  : 'opacity-50 hover:opacity-75'
              }`}
            >
              <div className={`w-3 h-3 rounded border-2 ${
                localShowEvents 
                  ? 'border-blue-500 bg-blue-500' 
                  : 'border-blue-500'
              }`}></div>
              <span>События ({filteredEvents.length})</span>
            </button>
            <button
              onClick={() => setLocalShowEntities(!localShowEntities)}
              className={`flex items-center gap-2 px-2 py-1 rounded transition-colors ${
                localShowEntities 
                  ? 'bg-pink-500/20 text-pink-600 dark:text-pink-400' 
                  : 'opacity-50 hover:opacity-75'
              }`}
            >
              <div className={`w-3 h-3 rounded border-2 ${
                localShowEntities 
                  ? 'border-pink-500 bg-pink-500' 
                  : 'border-pink-500'
              }`}></div>
              <span>Сущности ({filteredEntities.length})</span>
            </button>
          </div>
        </Panel>
      </ReactFlow>
    </div>
    </TooltipProvider>
  )
}
