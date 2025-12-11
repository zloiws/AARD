'use client'

import { useState } from 'react'
import { useBenchmarkResults } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { formatDistanceToNow, format } from 'date-fns'
import { CheckCircle2, XCircle, Clock, Loader2, ArrowLeft, ChevronDown, ChevronUp, Filter, Search, Calendar } from 'lucide-react'
import Link from 'next/link'
import { useSearchParams, useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api/client'

export default function BenchmarkResultsPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const resultIdsParam = searchParams.get('ids')
  const resultIds = resultIdsParam ? resultIdsParam.split(',').filter(Boolean) : []
  
  // Filters
  const [taskIdFilter, setTaskIdFilter] = useState('')
  const [modelIdFilter, setModelIdFilter] = useState('')
  const [limit, setLimit] = useState(50)
  const [expandedOutputs, setExpandedOutputs] = useState<Set<string>>(new Set())
  const [showFilters, setShowFilters] = useState(resultIds.length === 0)

  // Load all results (if no specific IDs) or specific results
  const { data: allResults, isLoading: allLoading } = useBenchmarkResults({
    task_id: taskIdFilter || undefined,
    model_id: modelIdFilter || undefined,
    limit: limit || undefined,
  })

  // Load specific results by IDs
  const { data: specificResults, isLoading: specificLoading } = useQuery({
    queryKey: ['benchmarks', 'results', 'details', resultIds],
    queryFn: async () => {
      if (resultIds.length === 0) return []
      
      const promises = resultIds.map(id => 
        api.benchmarks.getResult(id).catch(err => {
          console.error(`Failed to load result ${id}:`, err)
          return null
        })
      )
      
      const loadedResults = await Promise.all(promises)
      return loadedResults.filter(r => r !== null)
    },
    enabled: resultIds.length > 0,
  })

  // Use specific results if IDs provided, otherwise use all results
  const results = resultIds.length > 0 ? specificResults : allResults
  const isLoading = resultIds.length > 0 ? specificLoading : allLoading

  const toggleOutput = (resultId: string) => {
    const newExpanded = new Set(expandedOutputs)
    if (newExpanded.has(resultId)) {
      newExpanded.delete(resultId)
    } else {
      newExpanded.add(resultId)
    }
    setExpandedOutputs(newExpanded)
  }

  // Calculate summary statistics
  const stats = results ? {
    total: results.length,
    passed: results.filter(r => r.passed).length,
    failed: results.filter(r => !r.passed).length,
    avgScore: (() => {
      const scores = results
        .filter(r => r.score !== null && r.score !== undefined)
        .map(r => r.score!)
      return scores.length > 0
        ? (scores.reduce((a, b) => a + b, 0) / scores.length * 100).toFixed(1)
        : 'N/A'
    })(),
    avgExecutionTime: (() => {
      const times = results
        .filter(r => r.execution_time !== null && r.execution_time !== undefined)
        .map(r => r.execution_time!)
      return times.length > 0
        ? (times.reduce((a, b) => a + b, 0) / times.length / 1000).toFixed(2)
        : 'N/A'
    })(),
    uniqueTasks: new Set(results.map(r => r.benchmark_task_id)).size,
    uniqueModels: new Set(results.filter(r => r.model_id).map(r => r.model_id)).size,
  } : null

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <Link href="/benchmarks">
          <Button variant="ghost" className="mb-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Benchmarks
          </Button>
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Benchmark Results</h1>
            <p className="text-muted-foreground mt-2">
              {resultIds.length > 0 
                ? `Viewing ${resultIds.length} specific result(s)`
                : 'View and analyze all benchmark test results'}
            </p>
          </div>
          <Button
            variant="outline"
            onClick={() => setShowFilters(!showFilters)}
          >
            <Filter className="h-4 w-4 mr-2" />
            {showFilters ? 'Hide' : 'Show'} Filters
          </Button>
        </div>
      </div>

      {/* Filters */}
      {showFilters && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Filter className="h-5 w-5" />
              Filters
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <Label>Task ID</Label>
                <Input
                  placeholder="Filter by task ID..."
                  value={taskIdFilter}
                  onChange={(e) => setTaskIdFilter(e.target.value)}
                />
              </div>
              <div>
                <Label>Model ID</Label>
                <Input
                  placeholder="Filter by model ID..."
                  value={modelIdFilter}
                  onChange={(e) => setModelIdFilter(e.target.value)}
                />
              </div>
              <div>
                <Label>Limit</Label>
                <Input
                  type="number"
                  min="1"
                  max="100"
                  value={limit}
                  onChange={(e) => setLimit(parseInt(e.target.value) || 50)}
                />
              </div>
            </div>
            {resultIds.length > 0 && (
              <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
                <p className="text-sm text-blue-800">
                  Currently viewing specific results. Clear filters to see all results.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2"
                  onClick={() => router.push('/benchmarks/results')}
                >
                  View All Results
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Summary Statistics */}
      {stats && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Summary Statistics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
              <div className="text-center">
                <div className="text-3xl font-bold text-primary">{stats.total}</div>
                <div className="text-sm text-muted-foreground mt-1">Total Tests</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-green-500">{stats.passed}</div>
                <div className="text-sm text-muted-foreground mt-1">Passed</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-red-500">{stats.failed}</div>
                <div className="text-sm text-muted-foreground mt-1">Failed</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-primary">
                  {stats.avgScore === 'N/A' ? 'N/A' : `${stats.avgScore}%`}
                </div>
                <div className="text-sm text-muted-foreground mt-1">Avg Score</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-primary">
                  {stats.avgExecutionTime === 'N/A' ? 'N/A' : `${stats.avgExecutionTime}s`}
                </div>
                <div className="text-sm text-muted-foreground mt-1">Avg Time</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-primary">{stats.uniqueTasks}</div>
                <div className="text-sm text-muted-foreground mt-1">Unique Tasks</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-primary">{stats.uniqueModels}</div>
                <div className="text-sm text-muted-foreground mt-1">Unique Models</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Results List */}
      <Card>
        <CardHeader>
          <CardTitle>Results</CardTitle>
          <CardDescription>
            {results?.length || 0} result(s) {resultIds.length > 0 ? 'selected' : 'found'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : !results || results.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              No results found. {resultIds.length > 0 
                ? 'Try running some benchmarks first.'
                : 'Try adjusting your filters or run some benchmarks.'}
            </div>
          ) : (
            <div className="space-y-4">
              {results.map((result) => {
                const isExpanded = expandedOutputs.has(result.id)
                const task = (result as any).task || {}
                const outputText = typeof result.output === 'string' 
                  ? result.output 
                  : result.output ? JSON.stringify(result.output, null, 2) : ''
                const shouldTruncate = outputText && outputText.length > 200
                const displayOutput = shouldTruncate && !isExpanded
                  ? outputText.substring(0, 200) + '...'
                  : outputText

                return (
                  <Card
                    key={result.id}
                    className={`${
                      result.passed 
                        ? 'border-l-4 border-l-green-500' 
                        : 'border-l-4 border-l-red-500'
                    }`}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <h3 className="font-semibold text-lg">
                              {task.name || `Task ${result.benchmark_task_id.substring(0, 8)}`}
                            </h3>
                            <Badge variant={result.passed ? 'default' : 'destructive'}>
                              {result.passed ? (
                                <>
                                  <CheckCircle2 className="h-3 w-3 mr-1" />
                                  Passed
                                </>
                              ) : (
                                <>
                                  <XCircle className="h-3 w-3 mr-1" />
                                  Failed
                                </>
                              )}
                            </Badge>
                            {task.task_type && (
                              <Badge variant="outline">{task.task_type}</Badge>
                            )}
                          </div>
                          <div className="flex items-center gap-4 text-sm text-muted-foreground mb-2">
                            <span>Task ID: {result.benchmark_task_id.substring(0, 8)}...</span>
                            {result.model_id && (
                              <span>Model: {result.model_id.substring(0, 8)}...</span>
                            )}
                            {result.created_at && (
                              <span className="flex items-center gap-1">
                                <Calendar className="h-3 w-3" />
                                {format(new Date(result.created_at), 'MMM dd, yyyy HH:mm')}
                                {' '}({formatDistanceToNow(new Date(result.created_at), { addSuffix: true })})
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-2">
                            {result.score !== null && result.score !== undefined && (
                              <Badge variant="outline">
                                Score: {(result.score * 100).toFixed(1)}%
                              </Badge>
                            )}
                            {result.execution_time && (
                              <Badge variant="outline" className="flex items-center gap-1">
                                <Clock className="h-3 w-3" />
                                {(result.execution_time / 1000).toFixed(2)}s
                              </Badge>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Task Description */}
                      {task.task_description && (
                        <div className="mb-3 p-2 bg-muted rounded text-sm">
                          {task.task_description}
                        </div>
                      )}

                      {/* Error Message */}
                      {result.error_message && (
                        <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                          <p className="text-sm font-medium text-yellow-800 mb-1">Error:</p>
                          <p className="text-sm text-yellow-700">{result.error_message}</p>
                        </div>
                      )}

                      {/* Output */}
                      {outputText && (
                        <div className="mt-4">
                          <div className="flex items-center justify-between mb-2">
                            <p className="text-sm font-medium">Output:</p>
                            {shouldTruncate && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => toggleOutput(result.id)}
                              >
                                {isExpanded ? (
                                  <>
                                    <ChevronUp className="h-4 w-4 mr-1" />
                                    Collapse
                                  </>
                                ) : (
                                  <>
                                    <ChevronDown className="h-4 w-4 mr-1" />
                                    Expand
                                  </>
                                )}
                              </Button>
                            )}
                          </div>
                          <pre className="p-3 bg-muted rounded-md text-xs overflow-x-auto whitespace-pre-wrap break-words max-h-96 overflow-y-auto">
                            {displayOutput}
                          </pre>
                        </div>
                      )}

                      {/* Metrics JSON */}
                      {result.metrics && (
                        <div className="mt-4">
                          <p className="text-sm font-medium mb-2">Metrics:</p>
                          <pre className="p-3 bg-muted rounded-md text-xs overflow-x-auto">
                            {JSON.stringify(result.metrics, null, 2)}
                          </pre>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
