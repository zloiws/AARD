'use client'

import { useParams } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ArrowLeft, ExternalLink, Download } from 'lucide-react'
import Link from 'next/link'
import { useWorkflowEvents } from '@/lib/hooks/use-api'
import { EnhancedWorkflowGraph } from '@/components/workflow/enhanced-workflow-graph'
import { WorkflowTimeline } from '@/components/chat/workflow-timeline'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useState, useEffect, useRef } from 'react'
import { Loader2 } from 'lucide-react'
import { exportGraphToPNG, exportGraphToSVG } from '@/lib/utils/export-graph'
import { toast } from 'sonner'
import { ReactFlowInstance } from '@xyflow/react'

export default function WorkflowVisualizationPage() {
  const params = useParams()
  const workflowId = params.workflowId as string
  const [activeTab, setActiveTab] = useState<'graph' | 'timeline'>('graph')
  const [exportFormat, setExportFormat] = useState<'png' | 'svg'>('png')
  const [isExporting, setIsExporting] = useState(false)
  const graphContainerRef = useRef<HTMLDivElement>(null)
  const reactFlowInstanceRef = useRef<ReactFlowInstance | null>(null)
  
  const { data: workflowData, isLoading, error, isError } = useWorkflowEvents(workflowId, true)
  const events = workflowData?.events || []
  const entities = workflowData?.entities || []
  
  // Debug logging
  useEffect(() => {
    console.log('WorkflowVisualizationPage: State', {
      workflowId,
      isLoading,
      isError,
      hasData: !!workflowData,
      rawData: workflowData,
      eventsCount: events.length,
      entitiesCount: entities.length,
      events: events.length > 0 ? events.slice(0, 3).map(e => ({ 
        id: e.id, 
        source: e.event_source, 
        type: e.event_type, 
        message: e.message?.substring(0, 50) 
      })) : [],
      entities: entities.length > 0 ? entities.slice(0, 3).map(e => ({ 
        id: e.id, 
        type: e.type, 
        name: e.name 
      })) : [],
    })
    if (error) {
      console.error('Workflow Events Error:', error)
      console.error('Error details:', {
        message: error.message,
        stack: error.stack,
        name: error.name,
      })
    }
  }, [workflowData, events, entities, error, workflowId, isLoading, isError])

  const handleExportGraph = async () => {
    if (!reactFlowInstanceRef.current || !graphContainerRef.current || activeTab !== 'graph') {
      toast.error('Please switch to Graph View to export')
      return
    }

    setIsExporting(true)
    try {
      const filename = `workflow-${workflowId.slice(0, 8)}-${Date.now()}.${exportFormat}`
      
      if (exportFormat === 'png') {
        await exportGraphToPNG(reactFlowInstanceRef.current, graphContainerRef.current, {
          format: 'png',
          filename,
          backgroundColor: '#ffffff',
          scale: 2,
        })
        toast.success('Graph exported as PNG')
      } else {
        await exportGraphToSVG(reactFlowInstanceRef.current, graphContainerRef.current, {
          format: 'svg',
          filename,
          backgroundColor: '#ffffff',
        })
        toast.success('Graph exported as SVG')
      }
    } catch (error: any) {
      console.error('Export failed:', error)
      toast.error(`Failed to export graph: ${error.message || 'Unknown error'}`)
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-[95%]">
      {/* Header */}
      <div className="mb-6">
        <Link href="/chat">
          <Button variant="ghost" className="mb-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Chat
          </Button>
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              Workflow Visualization
            </h1>
            <p className="text-muted-foreground mt-1">
              Complete execution flow from message receipt to response
            </p>
            <div className="flex items-center gap-2 mt-2">
              <Badge variant="outline">Workflow ID: {workflowId.slice(0, 8)}...</Badge>
              {events.length > 0 && (
                <Badge variant="secondary">{events.length} events</Badge>
              )}
              {entities.length > 0 && (
                <Badge variant="secondary">{entities.length} entities</Badge>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={exportFormat}
              onChange={(e) => setExportFormat(e.target.value as 'png' | 'svg')}
              className="h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
              disabled={isExporting || activeTab !== 'graph'}
            >
              <option value="png">PNG</option>
              <option value="svg">SVG</option>
            </select>
            <Button 
              variant="outline" 
              onClick={handleExportGraph}
              disabled={isExporting || activeTab !== 'graph'}
            >
              {isExporting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Exporting...
                </>
              ) : (
                <>
                  <Download className="h-4 w-4 mr-2" />
                  Export
                </>
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <Card>
          <CardContent className="p-12 text-center">
            <Loader2 className="h-8 w-8 mx-auto mb-4 animate-spin text-muted-foreground" />
            <p className="text-muted-foreground">Loading workflow data...</p>
          </CardContent>
        </Card>
      ) : error ? (
        <Card>
          <CardContent className="p-12 text-center">
            <p className="text-red-500 mb-2">Error loading workflow data</p>
            <p className="text-sm text-muted-foreground">{error.message}</p>
            <p className="text-xs text-muted-foreground mt-2">Workflow ID: {workflowId}</p>
            <details className="mt-4 text-left">
              <summary className="cursor-pointer text-xs text-muted-foreground">Error details</summary>
              <pre className="text-xs mt-2 p-2 bg-muted rounded overflow-auto">
                {JSON.stringify(error, null, 2)}
              </pre>
            </details>
          </CardContent>
        </Card>
      ) : !isLoading && events.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <p className="text-muted-foreground">No workflow events found</p>
            <p className="text-xs text-muted-foreground mt-2">Workflow ID: {workflowId}</p>
            <p className="text-xs text-muted-foreground">Check if events exist in the database</p>
          </CardContent>
        </Card>
      ) : (
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'graph' | 'timeline')}>
          <TabsList className="mb-4">
            <TabsTrigger value="graph">Graph View</TabsTrigger>
            <TabsTrigger value="timeline">Timeline View</TabsTrigger>
          </TabsList>
          
          <TabsContent value="graph" className="mt-0">
            <Card>
              <CardHeader>
                <CardTitle>Workflow Graph</CardTitle>
                <CardDescription>
                  Visual representation of all events and entities with their relationships
                </CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                {events.length === 0 && entities.length === 0 ? (
                  <div className="p-12 text-center text-muted-foreground">
                    <p className="mb-2">Нет данных для отображения</p>
                    <p className="text-xs">
                      Workflow ID: {workflowId}<br/>
                      Событий: {events.length}, Сущностей: {entities.length}
                    </p>
                    {isLoading && <p className="text-xs mt-2">Загрузка...</p>}
                    {error && <p className="text-xs mt-2 text-red-500">Ошибка: {error.message}</p>}
                  </div>
                ) : (
                  <div ref={graphContainerRef}>
                    <EnhancedWorkflowGraph 
                      events={events} 
                      entities={entities}
                      height="calc(100vh - 350px)"
                      showEvents={true}
                      showEntities={true}
                      onInit={(instance) => {
                        reactFlowInstanceRef.current = instance
                      }}
                    />
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="timeline" className="mt-0">
            <Card>
              <CardHeader>
                <CardTitle>Execution Timeline</CardTitle>
                <CardDescription>
                  Chronological view of all workflow events with details
                </CardDescription>
              </CardHeader>
              <CardContent>
                <WorkflowTimeline workflowId={workflowId} showGraph={false} />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}

      {/* Entities Summary */}
      {entities.length > 0 && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Created Entities</CardTitle>
            <CardDescription>
              Entities (tasks, plans, tools) created during this workflow
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {entities.map((entity) => (
                <div
                  key={entity.id}
                  className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <Badge variant="outline" className="capitalize">
                      {entity.type}
                    </Badge>
                    <div>
                      <p className="text-sm font-medium">{entity.name}</p>
                      {entity.status && (
                        <p className="text-xs text-muted-foreground">{entity.status}</p>
                      )}
                    </div>
                  </div>
                  {entity.type === 'task' && (
                    <Link href={`/tasks/${entity.id}`}>
                      <Button variant="ghost" size="sm">
                        <ExternalLink className="h-3 w-3" />
                      </Button>
                    </Link>
                  )}
                  {entity.type === 'plan' && (
                    <Link href={`/plans/${entity.id}`}>
                      <Button variant="ghost" size="sm">
                        <ExternalLink className="h-3 w-3" />
                      </Button>
                    </Link>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
