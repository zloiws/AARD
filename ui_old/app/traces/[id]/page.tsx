'use client'

import { use } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api/client'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { formatDistanceToNow, format } from 'date-fns'
import { ArrowLeft, Activity, CheckCircle2, XCircle, Clock, Loader2 } from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

export default function TraceDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const router = useRouter()

  const { data: trace, isLoading, error } = useQuery({
    queryKey: ['trace', id],
    queryFn: () => api.traces.get(id),
  })

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-center items-center min-h-[400px]">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </div>
    )
  }

  if (error || !trace) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card>
          <CardContent className="p-6">
            <div className="text-center">
              <XCircle className="h-12 w-12 mx-auto mb-4 text-destructive" />
              <h2 className="text-2xl font-bold mb-2">Trace Not Found</h2>
              <p className="text-muted-foreground mb-4">
                The trace with ID {id} could not be found.
              </p>
              <Button onClick={() => router.push('/traces')} variant="outline">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Traces
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  const getStatusConfig = (status?: string) => {
    switch (status?.toLowerCase()) {
      case 'success':
      case 'completed':
        return { icon: CheckCircle2, color: 'text-green-500', variant: 'default' as const }
      case 'error':
      case 'failed':
        return { icon: XCircle, color: 'text-red-500', variant: 'destructive' as const }
      case 'running':
      case 'in_progress':
        return { icon: Clock, color: 'text-yellow-500', variant: 'secondary' as const }
      default:
        return { icon: Activity, color: 'text-gray-500', variant: 'secondary' as const }
    }
  }

  const statusConfig = getStatusConfig(trace.status)

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <Button
          variant="ghost"
          onClick={() => router.push('/traces')}
          className="mb-4"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Traces
        </Button>
        <h1 className="text-3xl font-bold tracking-tight">Trace Details</h1>
        <p className="text-muted-foreground mt-2">
          Execution trace information
        </p>
      </div>

      <div className="space-y-6">
        {/* Main Info */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  {trace.operation_name || 'Unknown Operation'}
                </CardTitle>
                <CardDescription className="mt-2">
                  Trace ID: {trace.trace_id}
                </CardDescription>
              </div>
              {trace.status && (
                <Badge variant={statusConfig.variant} className="flex items-center gap-2">
                  <statusConfig.icon className="h-4 w-4" />
                  {trace.status}
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div className="text-sm font-medium text-muted-foreground">Trace ID</div>
                <div className="text-sm font-mono mt-1">{trace.trace_id}</div>
              </div>
              {trace.span_id && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground">Span ID</div>
                  <div className="text-sm font-mono mt-1">{trace.span_id}</div>
                </div>
              )}
              {trace.parent_span_id && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground">Parent Span ID</div>
                  <div className="text-sm font-mono mt-1">{trace.parent_span_id}</div>
                </div>
              )}
              {trace.operation_name && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground">Operation</div>
                  <div className="text-sm mt-1">{trace.operation_name}</div>
                </div>
              )}
              {trace.start_time && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground">Start Time</div>
                  <div className="text-sm mt-1">
                    {format(new Date(trace.start_time), 'PPpp')}
                    <span className="text-muted-foreground ml-2">
                      ({formatDistanceToNow(new Date(trace.start_time), { addSuffix: true })})
                    </span>
                  </div>
                </div>
              )}
              {trace.end_time && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground">End Time</div>
                  <div className="text-sm mt-1">
                    {format(new Date(trace.end_time), 'PPpp')}
                    <span className="text-muted-foreground ml-2">
                      ({formatDistanceToNow(new Date(trace.end_time), { addSuffix: true })})
                    </span>
                  </div>
                </div>
              )}
              {trace.duration_ms !== null && trace.duration_ms !== undefined && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground">Duration</div>
                  <div className="text-sm mt-1">
                    {(trace.duration_ms / 1000).toFixed(2)}s ({trace.duration_ms}ms)
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Related Entities */}
        {(trace.task_id || trace.plan_id || trace.agent_id || trace.tool_id) && (
          <Card>
            <CardHeader>
              <CardTitle>Related Entities</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {trace.task_id && (
                  <div>
                    <div className="text-sm font-medium text-muted-foreground">Task</div>
                    <Link href={`/tasks/${trace.task_id}`} className="text-sm text-primary hover:underline mt-1 block">
                      {trace.task_id}
                    </Link>
                  </div>
                )}
                {trace.plan_id && (
                  <div>
                    <div className="text-sm font-medium text-muted-foreground">Plan</div>
                    <Link href={`/plans/${trace.plan_id}`} className="text-sm text-primary hover:underline mt-1 block">
                      {trace.plan_id}
                    </Link>
                  </div>
                )}
                {trace.agent_id && (
                  <div>
                    <div className="text-sm font-medium text-muted-foreground">Agent</div>
                    <Link href={`/agents/${trace.agent_id}`} className="text-sm text-primary hover:underline mt-1 block">
                      {trace.agent_id}
                    </Link>
                  </div>
                )}
                {trace.tool_id && (
                  <div>
                    <div className="text-sm font-medium text-muted-foreground">Tool</div>
                    <div className="text-sm mt-1">{trace.tool_id}</div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Error Information */}
        {(trace.error_message || trace.error_type) && (
          <Card className="border-destructive">
            <CardHeader>
              <CardTitle className="text-destructive">Error Information</CardTitle>
            </CardHeader>
            <CardContent>
              {trace.error_type && (
                <div className="mb-4">
                  <div className="text-sm font-medium text-muted-foreground">Error Type</div>
                  <div className="text-sm mt-1">{trace.error_type}</div>
                </div>
              )}
              {trace.error_message && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground">Error Message</div>
                  <div className="text-sm mt-1 p-3 bg-destructive/10 rounded-md font-mono">
                    {trace.error_message}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Attributes */}
        {trace.attributes && Object.keys(trace.attributes).length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Attributes</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="text-sm bg-muted p-4 rounded-md overflow-auto">
                {JSON.stringify(trace.attributes, null, 2)}
              </pre>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
