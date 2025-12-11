'use client'

import { useState } from 'react'
import { useBenchmarkComparison, useBenchmarkStats } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Loader2, BarChart3, TrendingUp, TrendingDown } from 'lucide-react'
import Link from 'next/link'
import { toast } from 'sonner'

export default function BenchmarkComparisonPage() {
  const [modelIds, setModelIds] = useState<string[]>([])
  const [modelIdInput, setModelIdInput] = useState('')
  const [taskType, setTaskType] = useState('')
  
  const comparisonMutation = useBenchmarkComparison()
  const { data: stats } = useBenchmarkStats()
  
  const comparison = comparisonMutation.data
  const isLoading = comparisonMutation.isPending

  const addModelId = () => {
    if (modelIdInput.trim() && !modelIds.includes(modelIdInput.trim())) {
      setModelIds([...modelIds, modelIdInput.trim()])
      setModelIdInput('')
    }
  }

  const removeModelId = (id: string) => {
    setModelIds(modelIds.filter(m => m !== id))
  }

  const handleCompare = () => {
    if (modelIds.length < 2) {
      toast.error('Please add at least 2 model IDs to compare')
      return
    }

    comparisonMutation.mutate({
      model_ids: modelIds,
      task_type: taskType || undefined,
    })
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold tracking-tight">Model Comparison</h1>
        <p className="text-muted-foreground mt-2">
          Compare performance of different models on benchmark tasks
        </p>
      </div>

      {/* Configuration */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Comparison Settings</CardTitle>
          <CardDescription>
            Select models and task type to compare
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label>Model IDs</Label>
            <div className="flex gap-2 mt-1">
              <Input
                placeholder="Enter model ID..."
                value={modelIdInput}
                onChange={(e) => setModelIdInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && addModelId()}
              />
              <Button onClick={addModelId} type="button">
                Add
              </Button>
            </div>
            {modelIds.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {modelIds.map((id) => (
                  <Badge key={id} variant="secondary" className="flex items-center gap-1">
                    {id}
                    <button
                      onClick={() => removeModelId(id)}
                      className="ml-1 hover:text-destructive"
                    >
                      ×
                    </button>
                  </Badge>
                ))}
              </div>
            )}
          </div>
          <div>
            <Label>Task Type (Optional)</Label>
            <Input
              placeholder="e.g., code_generation, reasoning..."
              value={taskType}
              onChange={(e) => setTaskType(e.target.value)}
              className="mt-1"
            />
          </div>
          <Button
            onClick={handleCompare}
            disabled={modelIds.length < 2 || isLoading}
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Comparing...
              </>
            ) : (
              <>
                <BarChart3 className="h-4 w-4 mr-2" />
                Compare Models
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Comparison Results */}
      {comparison && (
        <Card>
          <CardHeader>
            <CardTitle>Comparison Results</CardTitle>
            <CardDescription>
              Performance comparison across selected models
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {Object.entries(comparison).map(([key, value]) => (
                <div key={key} className="p-4 border rounded-lg">
                  <h3 className="font-semibold mb-2">{key}</h3>
                  <pre className="text-sm overflow-x-auto bg-muted p-3 rounded">
                    {JSON.stringify(value, null, 2)}
                  </pre>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Statistics */}
      {stats && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Overall Statistics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {Object.entries(stats).map(([key, value]) => (
                <div key={key} className="p-4 border rounded-lg">
                  <p className="text-sm text-muted-foreground mb-1">{key}</p>
                  <p className="text-2xl font-bold">{String(value)}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Navigation */}
      <div className="mt-6 text-center">
        <Link href="/benchmarks">
          <Button variant="outline">
            Back to Benchmarks
          </Button>
        </Link>
        <Link href="/benchmarks/results" className="ml-2">
          <Button variant="outline">
            View All Results
          </Button>
        </Link>
      </div>
    </div>
  )
}
