'use client'

import { useState } from 'react'
import { useCreateTask } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ArrowLeft, Loader2 } from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Textarea } from '@/components/ui/textarea'

export default function NewTaskPage() {
  const router = useRouter()
  const createTask = useCreateTask()
  const [description, setDescription] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!description.trim()) return

    setIsSubmitting(true)
    try {
      const result = await createTask.mutateAsync({
        description: description.trim(),
        status: 'pending',
      })
      router.push(`/tasks/${result.task_id || result.id}`)
    } catch (error) {
      console.error('Failed to create task:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <div className="mb-6">
        <Link href="/tasks">
          <Button variant="ghost" className="mb-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Tasks
          </Button>
        </Link>
        <h1 className="text-3xl font-bold tracking-tight">Create New Task</h1>
        <p className="text-muted-foreground mt-2">
          Describe the task you want the AI agents to complete
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Task Details</CardTitle>
          <CardDescription>
            Provide a clear description of what you want to accomplish
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="description" className="text-sm font-medium mb-2 block">
                Task Description
              </label>
              <Textarea
                id="description"
                placeholder="e.g., Create a REST API endpoint for user authentication..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={6}
                className="resize-none"
                required
              />
              <p className="text-xs text-muted-foreground mt-2">
                Be as specific as possible. The AI agents will use this to create a plan and execute the task.
              </p>
            </div>

            <div className="flex justify-end space-x-2">
              <Link href="/tasks">
                <Button type="button" variant="outline">
                  Cancel
                </Button>
              </Link>
              <Button type="submit" disabled={!description.trim() || isSubmitting}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  'Create Task'
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
