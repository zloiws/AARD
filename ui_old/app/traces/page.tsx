'use client'

import { useState } from 'react'
import { useTraces } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { formatDistanceToNow } from 'date-fns'
import { Search, Loader2, Activity, ArrowRight } from 'lucide-react'
import Link from 'next/link'

export default function TracesPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [pageSize, setPageSize] = useState(50)

  const { data: tracesData, isLoading } = useTraces({ page_size: pageSize })

  // API returns { traces: [...], total: ..., page: ..., page_size: ... }
  const traces = tracesData?.traces || (Array.isArray(tracesData) ? tracesData : [])

  const filteredTraces = traces.filter((trace) => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    return (
      trace.trace_id?.toLowerCase().includes(query) ||
      (trace.task_id && String(trace.task_id).toLowerCase().includes(query)) ||
      (trace.operation_name && trace.operation_name.toLowerCase().includes(query))
    )
  })

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold tracking-tight">Traces</h1>
        <p className="text-muted-foreground mt-2">
          View execution traces and spans
        </p>
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardContent className="p-4">
          <div className="flex gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by trace ID or task ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="w-32">
              <Label>Page Size</Label>
              <Input
                type="number"
                min="1"
                max="100"
                value={pageSize}
                onChange={(e) => setPageSize(parseInt(e.target.value) || 50)}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Traces List */}
      <Card>
        <CardHeader>
          <CardTitle>Execution Traces</CardTitle>
          <CardDescription>
            {filteredTraces.length} trace(s) found
            {tracesData && 'total' in tracesData && (
              <span className="ml-2">(Total: {tracesData.total})</span>
            )}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : filteredTraces.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Activity className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No traces found</p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredTraces.map((trace) => (
                <Card key={trace.id || trace.trace_id} className="hover:shadow-md transition-shadow">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <Link href={`/traces/${trace.trace_id || trace.id}`}>
                            <h3 className="font-semibold hover:text-primary transition-colors">
                              {trace.trace_id || trace.id}
                            </h3>
                          </Link>
                          {trace.status && (
                            <Badge variant={trace.status === 'success' ? 'default' : 'destructive'}>
                              {trace.status}
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-4 text-sm text-muted-foreground flex-wrap">
                          {trace.operation_name && (
                            <span className="font-medium">{trace.operation_name}</span>
                          )}
                          {trace.task_id && (
                            <span>Task: {String(trace.task_id).substring(0, 8)}...</span>
                          )}
                          {trace.agent_id && (
                            <span>Agent: {String(trace.agent_id).substring(0, 8)}...</span>
                          )}
                          {trace.start_time && (
                            <span>
                              {formatDistanceToNow(new Date(trace.start_time), { addSuffix: true })}
                            </span>
                          )}
                          {trace.duration_ms !== null && trace.duration_ms !== undefined && (
                            <span>Duration: {(trace.duration_ms / 1000).toFixed(2)}s</span>
                          )}
                        </div>
                      </div>
                      <Link href={`/traces/${trace.trace_id || trace.id}`}>
                        <Button variant="outline" size="sm">
                          View
                          <ArrowRight className="h-4 w-4 ml-2" />
                        </Button>
                      </Link>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
