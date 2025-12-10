'use client'

import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Clock, GitBranch, ExternalLink } from 'lucide-react'
import Link from 'next/link'
import { WorkflowTimeline } from './workflow-timeline'
import { EnhancedWorkflowGraph } from '@/components/workflow/enhanced-workflow-graph'
import { useWorkflowEvents } from '@/lib/hooks/use-api'
import { Loader2 } from 'lucide-react'

interface WorkflowViewProps {
  workflowId: string
  className?: string
  compact?: boolean // Compact mode for chat messages
}

export function WorkflowView({ workflowId, className, compact = false }: WorkflowViewProps) {
  const [activeView, setActiveView] = useState<'timeline' | 'graph'>('timeline')
  const { data: workflowData, isLoading } = useWorkflowEvents(workflowId, true)
  const events = workflowData?.events || []
  const entities = workflowData?.entities || []

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-4">
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground mr-2" />
        <span className="text-xs text-muted-foreground">Loading workflow...</span>
      </div>
    )
  }

  if (events.length === 0 && entities.length === 0) {
    return (
      <div className="text-xs text-muted-foreground py-2">
        No workflow events found yet. Workflow may still be processing...
      </div>
    )
  }

  // Compact mode: simplified view with link to full page
  if (compact) {
    return (
      <div className="mt-3 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Clock className="h-3 w-3" />
            <span>Workflow: {workflowId.slice(0, 8)}...</span>
            {events.length > 0 && (
              <span className="text-xs">({events.length} events)</span>
            )}
          </div>
          <Link href={`/workflows/${workflowId}`}>
            <Button variant="ghost" size="sm" className="h-6 px-2 text-xs">
              <ExternalLink className="h-3 w-3 mr-1" />
              View Full Graph
            </Button>
          </Link>
        </div>
        {/* Show simplified timeline preview */}
        <div className="max-h-48 overflow-y-auto border rounded-lg p-2 bg-muted/30">
          <WorkflowTimeline workflowId={workflowId} showGraph={false} />
        </div>
      </div>
    )
  }

  // Full mode: show tabs with both views
  return (
    <div className={className}>
      <Tabs value={activeView} onValueChange={(v) => setActiveView(v as 'timeline' | 'graph')}>
        <div className="flex items-center justify-between mb-2">
          <TabsList>
            <TabsTrigger value="timeline">
              <Clock className="h-4 w-4 mr-2" />
              Timeline
            </TabsTrigger>
            <TabsTrigger value="graph">
              <GitBranch className="h-4 w-4 mr-2" />
              Graph
            </TabsTrigger>
          </TabsList>
          <Link href={`/workflows/${workflowId}`}>
            <Button variant="outline" size="sm">
              <ExternalLink className="h-4 w-4 mr-2" />
              Full View
            </Button>
          </Link>
        </div>
        <TabsContent value="timeline" className="mt-0">
          <WorkflowTimeline workflowId={workflowId} showGraph={true} />
        </TabsContent>
        <TabsContent value="graph" className="mt-0">
          <div className="h-[600px] border rounded-lg overflow-hidden">
            <EnhancedWorkflowGraph 
              events={events} 
              entities={entities}
              height="100%"
              showEvents={true}
              showEntities={true}
            />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
