'use client'

import { useState, useEffect } from 'react'
import { useBenchmarkTasks, useRunBenchmark, useServers, useServerModels } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { Loader2, Play, Search, Filter } from 'lucide-react'
import { toast } from 'sonner'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

const TASK_TYPES = [
  { value: '', label: 'All Types' },
  { value: 'code_generation', label: 'Code Generation' },
  { value: 'code_analysis', label: 'Code Analysis' },
  { value: 'reasoning', label: 'Reasoning' },
  { value: 'planning', label: 'Planning' },
  { value: 'general_chat', label: 'General Chat' },
]

const DIFFICULTY_LEVELS = [
  { value: '', label: 'All Difficulties' },
  { value: 'easy', label: 'Easy' },
  { value: 'medium', label: 'Medium' },
  { value: 'hard', label: 'Hard' },
]

export default function BenchmarksPage() {
  const router = useRouter()
  const [taskType, setTaskType] = useState('')
  const [category, setCategory] = useState('')
  const [difficulty, setDifficulty] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTasks, setSelectedTasks] = useState<Set<string>>(new Set())
  const [selectedServerId, setSelectedServerId] = useState('')
  const [selectedModelName, setSelectedModelName] = useState('')
  const [timeout, setTimeout] = useState(90)
  const [isRunning, setIsRunning] = useState(false)

  const { data: tasks, isLoading: tasksLoading } = useBenchmarkTasks({
    task_type: taskType || undefined,
    category: category || undefined,
    difficulty: difficulty || undefined,
    name: searchQuery || undefined,
  })

  const { data: servers } = useServers(true)
  const { data: models } = useServerModels(selectedServerId)
  const runBenchmark = useRunBenchmark()

  // Load servers on mount
  useEffect(() => {
    if (servers && servers.length > 0 && !selectedServerId) {
      // Auto-select first server
      setSelectedServerId(servers[0].id)
    }
  }, [servers, selectedServerId])

  const toggleTask = (taskId: string) => {
    const newSelected = new Set(selectedTasks)
    if (newSelected.has(taskId)) {
      newSelected.delete(taskId)
    } else {
      newSelected.add(taskId)
    }
    setSelectedTasks(newSelected)
  }

  const toggleSelectAll = () => {
    const tasksLength = tasks?.length || 0
    if (selectedTasks.size === tasksLength && tasksLength > 0) {
      setSelectedTasks(new Set())
    } else {
      setSelectedTasks(new Set(tasks?.map(t => t.id) || []))
    }
  }

  const handleRunBenchmark = async () => {
    if (selectedTasks.size === 0) {
      toast.error('Please select at least one task')
      return
    }

    if (!selectedModelName) {
      toast.error('Please select a model')
      return
    }

    if (!selectedServerId) {
      toast.error('Please select a server')
      return
    }

    setIsRunning(true)
    try {
      const selectedTaskIds = Array.from(selectedTasks)
      const results: string[] = []

      // Run each task sequentially
      for (const taskId of selectedTaskIds) {
        try {
          const taskResults = await runBenchmark.mutateAsync({
            task_id: taskId,
            model_name: selectedModelName,
            server_id: selectedServerId,
            timeout: timeout,
            evaluate: true,
          })
          
          // Collect result IDs
          if (taskResults && taskResults.length > 0) {
            results.push(...taskResults.map(r => r.id))
          }
        } catch (error) {
          console.error(`Failed to run task ${taskId}:`, error)
          toast.error(`Failed to run task ${taskId}`)
        }
      }

      if (results.length > 0) {
        // Redirect to results page with IDs
        const resultIds = results.join(',')
        router.push(`/benchmarks/results?ids=${resultIds}`)
      } else {
        toast.error('No results were generated. Please check server and model configuration.')
      }
    } catch (error) {
      console.error('Failed to run benchmarks:', error)
      toast.error('Failed to run benchmarks')
    } finally {
      setIsRunning(false)
    }
  }

  const tasksLength = tasks?.length || 0
  const canRun = selectedTasks.size > 0 && selectedModelName && selectedServerId && !isRunning

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold tracking-tight">Benchmark Tests</h1>
        <p className="text-muted-foreground mt-2">
          Test models on various tasks and compare performance
        </p>
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <Label>Task Type</Label>
              <Select value={taskType} onValueChange={setTaskType}>
                <SelectTrigger>
                  <SelectValue placeholder="All Types" />
                </SelectTrigger>
                <SelectContent>
                  {TASK_TYPES.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Difficulty</Label>
              <Select value={difficulty} onValueChange={setDifficulty}>
                <SelectTrigger>
                  <SelectValue placeholder="All Difficulties" />
                </SelectTrigger>
                <SelectContent>
                  {DIFFICULTY_LEVELS.map((level) => (
                    <SelectItem key={level.value} value={level.value}>
                      {level.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Category</Label>
              <Input
                placeholder="Category..."
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              />
            </div>
            <div>
              <Label>Search</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search tasks..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Model Selection */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Model Selection</CardTitle>
          <CardDescription>
            Select server and model for testing
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <Label>Server</Label>
              <Select 
                value={selectedServerId} 
                onValueChange={(value) => {
                  setSelectedServerId(value)
                  setSelectedModelName('')
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select server" />
                </SelectTrigger>
                <SelectContent>
                  {servers?.map((server) => (
                    <SelectItem key={server.id} value={server.id}>
                      {server.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Model</Label>
              <Select
                value={selectedModelName}
                onValueChange={setSelectedModelName}
                disabled={!selectedServerId}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select model" />
                </SelectTrigger>
                <SelectContent>
                  {models?.map((model) => (
                    <SelectItem key={model.id} value={model.model_name}>
                      {model.name || model.model_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Timeout (seconds)</Label>
              <Input
                type="number"
                min="60"
                max="300"
                value={timeout}
                onChange={(e) => setTimeout(parseInt(e.target.value) || 90)}
              />
            </div>
            <div className="flex items-end">
              <Button
                onClick={handleRunBenchmark}
                disabled={!canRun}
                className="w-full"
              >
                {isRunning ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Running...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    Run Selected ({selectedTasks.size})
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tasks List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Benchmark Tasks</CardTitle>
              <CardDescription>
                {tasksLength} task(s) found
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Checkbox
                checked={selectedTasks.size === tasksLength && tasksLength > 0}
                onCheckedChange={toggleSelectAll}
              />
              <Label>Select All</Label>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {tasksLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : tasksLength === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              No tasks found. Try adjusting your filters.
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {(tasks || []).map((task) => {
                const isSelected = selectedTasks.has(task.id)
                const taskTypeClass = task.task_type?.toLowerCase().replace('_', '-') || ''
                
                return (
                  <Card
                    key={task.id}
                    className={`cursor-pointer transition-all hover:shadow-md ${
                      isSelected ? 'ring-2 ring-primary' : ''
                    }`}
                    onClick={() => toggleTask(task.id)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start gap-2 mb-2">
                        <Checkbox
                          checked={isSelected}
                          onCheckedChange={() => toggleTask(task.id)}
                          onClick={(e) => e.stopPropagation()}
                        />
                        <div className="flex-1">
                          <h3 className="font-semibold text-sm mb-1">{task.name}</h3>
                          <div className="flex gap-2 flex-wrap">
                            <Badge variant="outline" className={`text-xs ${taskTypeClass}`}>
                              {task.task_type}
                            </Badge>
                            {task.difficulty && (
                              <Badge variant="secondary" className="text-xs">
                                {task.difficulty}
                              </Badge>
                            )}
                          </div>
                        </div>
                      </div>
                      <p className="text-sm text-muted-foreground line-clamp-3 mt-2">
                        {task.task_description}
                      </p>
                      {task.category && (
                        <p className="text-xs text-muted-foreground mt-2">
                          📁 {task.category}
                        </p>
                      )}
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Navigation */}
      <div className="mt-6 text-center">
        <Link href="/benchmarks/results">
          <Button variant="outline">
            View All Results
          </Button>
        </Link>
        <Link href="/benchmarks/comparison" className="ml-2">
          <Button variant="outline">
            Compare Models
          </Button>
        </Link>
      </div>
    </div>
  )
}
