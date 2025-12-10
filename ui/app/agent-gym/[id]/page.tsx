'use client'

import { useState } from 'react'
import { useAgentGymTest, useAgentGymTestRuns, useRunAgentGymTest, useAgent } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { formatDistanceToNow, format } from 'date-fns'
import { ArrowLeft, Play, Loader2, CheckCircle2, XCircle, Clock, AlertCircle, GitBranch } from 'lucide-react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { toast } from 'sonner'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

const getStatusConfig = (status: string) => {
  switch (status) {
    case 'passed':
      return { label: 'Passed', icon: CheckCircle2, color: 'text-green-500', bg: 'bg-green-100', variant: 'default' as const }
    case 'failed':
      return { label: 'Failed', icon: XCircle, color: 'text-red-500', bg: 'bg-red-100', variant: 'destructive' as const }
    case 'running':
      return { label: 'Running', icon: Loader2, color: 'text-blue-500', bg: 'bg-blue-100', variant: 'secondary' as const }
    case 'error':
      return { label: 'Error', icon: AlertCircle, color: 'text-red-500', bg: 'bg-red-100', variant: 'destructive' as const }
    case 'timeout':
      return { label: 'Timeout', icon: Clock, color: 'text-yellow-500', bg: 'bg-yellow-100', variant: 'secondary' as const }
    default:
      return { label: status, icon: Clock, color: 'text-gray-500', bg: 'bg-gray-100', variant: 'secondary' as const }
  }
}

export default function AgentGymTestDetailPage() {
  const params = useParams()
  const testId = params.id as string
  const { data: test, isLoading } = useAgentGymTest(testId)
  const { data: runs, isLoading: runsLoading } = useAgentGymTestRuns(testId)
  const runTest = useRunAgentGymTest()
  const { data: agent } = useAgent(test?.agent_id || '')
  
  const [isRunning, setIsRunning] = useState(false)

  const handleRunTest = async () => {
    if (!confirm('Run this test now?')) return

    setIsRunning(true)
    try {
      await runTest.mutateAsync({
        testId,
        data: {
          run_by: 'user',
          notes: 'Run from web interface',
        },
      })
      toast.success('Test started! Refresh the page in a few seconds to see results.')
    } catch (error) {
      console.error('Failed to run test:', error)
    } finally {
      setIsRunning(false)
    }
  }

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </div>
    )
  }

  if (!test) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card>
          <CardContent className="p-12 text-center">
            <p className="text-muted-foreground mb-4">Test not found</p>
            <Link href="/agent-gym">
              <Button variant="outline">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Tests
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Calculate statistics
  const stats = runs ? {
    total: runs.length,
    passed: runs.filter(r => r.status === 'passed').length,
    failed: runs.filter(r => r.status === 'failed').length,
    running: runs.filter(r => r.status === 'running').length,
    avgDuration: (() => {
      const durations = runs.filter(r => r.duration_ms).map(r => r.duration_ms!)
      return durations.length > 0
        ? (durations.reduce((a, b) => a + b, 0) / durations.length / 1000).toFixed(2)
        : 'N/A'
    })(),
  } : null

  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl">
      <div className="mb-6">
        <Link href="/agent-gym">
          <Button variant="ghost" className="mb-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Tests
          </Button>
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{test.name}</h1>
            <div className="flex items-center gap-2 mt-2">
              <Badge variant="outline">{test.test_type}</Badge>
              {agent && (
                <Badge variant="secondary">
                  Agent: {agent.name}
                </Badge>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={handleRunTest}
              disabled={isRunning || runTest.isPending}
            >
              {isRunning || runTest.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Run Test
                </>
              )}
            </Button>
            <Link href={`/agent-gym/${testId}/edit`}>
              <Button variant="outline">
                Edit
              </Button>
            </Link>
          </div>
        </div>
      </div>

      <Tabs defaultValue="info" className="w-full">
        <TabsList>
          <TabsTrigger value="info">Information</TabsTrigger>
          <TabsTrigger value="runs">
            Test Runs {runs && runs.length > 0 && `(${runs.length})`}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="info" className="mt-4">
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Test Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {test.description && (
                  <div>
                    <p className="text-sm text-muted-foreground">Description</p>
                    <p className="font-medium">{test.description}</p>
                  </div>
                )}
                <div>
                  <p className="text-sm text-muted-foreground">Test Type</p>
                  <p className="font-medium">{test.test_type}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Agent</p>
                  <p className="font-medium">{agent?.name || test.agent_id}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Timeout</p>
                  <p className="font-medium">{test.timeout_seconds} seconds</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Max Retries</p>
                  <p className="font-medium">{test.max_retries}</p>
                </div>
                {test.required_tools && test.required_tools.length > 0 && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-2">Required Tools</p>
                    <div className="flex flex-wrap gap-2">
                      {test.required_tools.map((tool) => (
                        <Badge key={tool} variant="outline">{tool}</Badge>
                      ))}
                    </div>
                  </div>
                )}
                {test.tags && test.tags.length > 0 && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-2">Tags</p>
                    <div className="flex flex-wrap gap-2">
                      {test.tags.map((tag) => (
                        <Badge key={tag} variant="secondary">{tag}</Badge>
                      ))}
                    </div>
                  </div>
                )}
                <div>
                  <p className="text-sm text-muted-foreground">Created</p>
                  <p className="font-medium">
                    {formatDistanceToNow(new Date(test.created_at), { addSuffix: true })}
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Test Data</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {test.input_data && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-2">Input Data</p>
                    <pre className="p-3 bg-muted rounded-md text-xs overflow-x-auto">
                      {JSON.stringify(test.input_data, null, 2)}
                    </pre>
                  </div>
                )}
                {test.expected_output && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-2">Expected Output</p>
                    <pre className="p-3 bg-muted rounded-md text-xs overflow-x-auto">
                      {JSON.stringify(test.expected_output, null, 2)}
                    </pre>
                  </div>
                )}
                {test.validation_rules && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-2">Validation Rules</p>
                    <pre className="p-3 bg-muted rounded-md text-xs overflow-x-auto">
                      {JSON.stringify(test.validation_rules, null, 2)}
                    </pre>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="runs" className="mt-4">
          {/* Statistics */}
          {stats && (
            <Card className="mb-6">
              <CardContent className="p-6">
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold">{stats.total}</div>
                    <div className="text-xs text-muted-foreground">Total</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-500">{stats.passed}</div>
                    <div className="text-xs text-muted-foreground">Passed</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-red-500">{stats.failed}</div>
                    <div className="text-xs text-muted-foreground">Failed</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-500">{stats.running}</div>
                    <div className="text-xs text-muted-foreground">Running</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold">{stats.avgDuration}s</div>
                    <div className="text-xs text-muted-foreground">Avg Duration</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Runs List */}
          <Card>
            <CardHeader>
              <CardTitle>Test Runs</CardTitle>
              <CardDescription>
                History of test executions
              </CardDescription>
            </CardHeader>
            <CardContent>
              {runsLoading ? (
                <div className="flex justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : !runs || runs.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  No test runs yet. Click "Run Test" to start.
                </div>
              ) : (
                <div className="space-y-4">
                  {runs.map((run) => {
                    const config = getStatusConfig(run.status)
                    const Icon = config.icon

                    return (
                      <Card key={run.id} className={`border-l-4 ${
                        run.status === 'passed' ? 'border-l-green-500' :
                        run.status === 'failed' ? 'border-l-red-500' :
                        run.status === 'running' ? 'border-l-blue-500' :
                        'border-l-yellow-500'
                      }`}>
                        <CardContent className="p-4">
                          <div className="flex items-start justify-between mb-3">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-2">
                                <Icon className={`h-4 w-4 ${config.color} ${run.status === 'running' ? 'animate-spin' : ''}`} />
                                <Badge variant={config.variant}>{config.label}</Badge>
                                {run.started_at && (
                                  <span className="text-sm text-muted-foreground">
                                    {format(new Date(run.started_at), 'MMM dd, yyyy HH:mm:ss')}
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                                {run.duration_ms && (
                                  <span>Duration: {(run.duration_ms / 1000).toFixed(2)}s</span>
                                )}
                                {run.tokens_used && (
                                  <span>Tokens: {run.tokens_used}</span>
                                )}
                                {run.llm_calls && (
                                  <span>LLM Calls: {run.llm_calls}</span>
                                )}
                                {run.tool_calls && (
                                  <span>Tool Calls: {run.tool_calls}</span>
                                )}
                              </div>
                            </div>
                          </div>

                          {run.validation_passed !== null && run.validation_passed !== undefined && (
                            <div className="mb-3">
                              <Badge variant={run.validation_passed === 'true' ? 'default' : 'destructive'}>
                                Validation: {run.validation_passed === 'true' ? 'Passed' : run.validation_passed === 'false' ? 'Failed' : 'Partial'}
                              </Badge>
                            </div>
                          )}

                          {run.error_message && (
                            <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-md">
                              <p className="text-sm font-medium text-red-800 mb-1">Error:</p>
                              <p className="text-sm text-red-700">{run.error_message}</p>
                            </div>
                          )}

                          {run.output_data && (
                            <div className="mt-3">
                              <p className="text-sm font-medium mb-2">Output:</p>
                              <pre className="p-3 bg-muted rounded-md text-xs overflow-x-auto max-h-64 overflow-y-auto">
                                {JSON.stringify(run.output_data, null, 2)}
                              </pre>
                            </div>
                          )}

                          {run.validation_details && (
                            <div className="mt-3">
                              <p className="text-sm font-medium mb-2">Validation Details:</p>
                              <pre className="p-3 bg-muted rounded-md text-xs overflow-x-auto">
                                {JSON.stringify(run.validation_details, null, 2)}
                              </pre>
                            </div>
                          )}

                          {/* Workflow Visualization Link */}
                          {(run as any).workflow_id && (
                            <div className="mt-3 pt-3 border-t">
                              <Link href={`/workflows/${(run as any).workflow_id}`}>
                                <Button variant="outline" size="sm" className="w-full">
                                  <GitBranch className="h-4 w-4 mr-2" />
                                  View Workflow Visualization
                                </Button>
                              </Link>
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
        </TabsContent>
      </Tabs>
    </div>
  )
}
