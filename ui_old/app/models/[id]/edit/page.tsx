'use client'

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useUpdateModel } from '@/lib/hooks/use-api'
import { api } from '@/lib/api/client'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ArrowLeft, Loader2, Plus, X } from 'lucide-react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { Badge } from '@/components/ui/badge'

const CAPABILITY_OPTIONS = [
  'code_generation',
  'code_analysis',
  'reasoning',
  'planning',
  'general_chat',
  'embeddings',
]

export default function EditModelPage() {
  const params = useParams()
  const router = useRouter()
  const modelId = params.id as string
  const { data: model, isLoading } = useQuery({
    queryKey: ['models', modelId],
    queryFn: () => api.models.get(modelId),
    enabled: !!modelId,
  })
  const updateModel = useUpdateModel()
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  // Form state
  const [name, setName] = useState('')
  const [capabilities, setCapabilities] = useState<string[]>([])
  const [priority, setPriority] = useState(0)
  const [isActive, setIsActive] = useState(true)

  // Load model data
  useEffect(() => {
    if (model) {
      setName(model.name)
      setCapabilities(model.capabilities || [])
      setPriority(model.priority || 0)
      setIsActive(model.is_active)
    }
  }, [model])

  const toggleCapability = (cap: string) => {
    if (capabilities.includes(cap)) {
      setCapabilities(capabilities.filter(c => c !== cap))
    } else {
      setCapabilities([...capabilities, cap])
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || !model) return

    setIsSubmitting(true)
    try {
      await updateModel.mutateAsync({
        id: modelId,
        data: {
          name: name.trim(),
          capabilities: capabilities.length > 0 ? capabilities : undefined,
          priority: priority || 0,
          is_active: isActive,
        },
      })
      router.back()
    } catch (error) {
      console.error('Failed to update model:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="space-y-4">
          <div className="h-8 bg-muted rounded w-1/4 animate-pulse" />
          <Card className="animate-pulse">
            <CardContent className="p-6">
              <div className="h-4 bg-muted rounded w-3/4 mb-4" />
              <div className="h-3 bg-muted rounded w-1/2" />
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  if (!model) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card>
          <CardContent className="p-12 text-center">
            <p className="text-muted-foreground mb-4">Model not found</p>
            <Button variant="outline" onClick={() => router.back()}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-3xl">
      <div className="mb-6">
        <Button variant="ghost" className="mb-4" onClick={() => router.back()}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
        <h1 className="text-3xl font-bold tracking-tight">Edit Model: {model.model_name}</h1>
        <p className="text-muted-foreground mt-2">
          Configure model capabilities and settings
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Model Information</CardTitle>
            <CardDescription>
              Model name cannot be changed
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Model Name</Label>
              <Input
                value={model.model_name}
                disabled
                className="mt-1"
              />
            </div>

            <div>
              <Label htmlFor="name">Display Name *</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="mt-1"
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Configuration</CardTitle>
            <CardDescription>
              Configure model capabilities and priority
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="priority">Priority</Label>
              <Input
                id="priority"
                type="number"
                min="0"
                max="100"
                value={priority}
                onChange={(e) => setPriority(parseInt(e.target.value) || 0)}
                className="mt-1"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Higher priority = selected first for matching task types
              </p>
            </div>

            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="isActive"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
                className="h-4 w-4"
              />
              <Label htmlFor="isActive" className="cursor-pointer">
                Model is active (available for selection)
              </Label>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Capabilities</CardTitle>
            <CardDescription>
              Select what this model can do. Models with matching capabilities will be selected for corresponding task types.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {CAPABILITY_OPTIONS.map((cap) => (
                <Badge
                  key={cap}
                  variant={capabilities.includes(cap) ? 'default' : 'outline'}
                  className="cursor-pointer"
                  onClick={() => toggleCapability(cap)}
                >
                  {cap}
                </Badge>
              ))}
            </div>
            <p className="text-xs text-muted-foreground mt-4">
              <strong>Note:</strong> Models with capabilities matching the task type will be preferred. 
              For example, a model with "code_generation" capability will be selected for code generation tasks.
            </p>
          </CardContent>
        </Card>

        <div className="flex justify-end space-x-2">
          <Button type="button" variant="outline" onClick={() => router.back()}>
            Cancel
          </Button>
          <Button type="submit" disabled={!name.trim() || isSubmitting}>
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              'Save Changes'
            )}
          </Button>
        </div>
      </form>
    </div>
  )
}
