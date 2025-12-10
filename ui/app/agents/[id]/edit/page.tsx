'use client'

import { useState, useEffect } from 'react'
import { useAgent, useUpdateAgent } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { ArrowLeft, Loader2, Plus, X } from 'lucide-react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { Badge } from '@/components/ui/badge'

export default function EditAgentPage() {
  const params = useParams()
  const router = useRouter()
  const agentId = params.id as string
  const { data: agent, isLoading } = useAgent(agentId)
  const updateAgent = useUpdateAgent()
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  // Form state
  const [description, setDescription] = useState('')
  const [systemPrompt, setSystemPrompt] = useState('')
  const [modelPreference, setModelPreference] = useState('')
  const [temperature, setTemperature] = useState('0.7')
  const [maxConcurrentTasks, setMaxConcurrentTasks] = useState(1)
  const [capabilities, setCapabilities] = useState<string[]>([])
  const [newCapability, setNewCapability] = useState('')
  const [tags, setTags] = useState<string[]>([])
  const [newTag, setNewTag] = useState('')

  // Load agent data
  useEffect(() => {
    if (agent) {
      setDescription(agent.description || '')
      setSystemPrompt(agent.system_prompt || '')
      setModelPreference(agent.model_preference || '')
      setTemperature(agent.temperature || '0.7')
      setMaxConcurrentTasks(agent.max_concurrent_tasks || 1)
      setCapabilities(agent.capabilities || [])
      setTags(agent.tags || [])
    }
  }, [agent])

  const addCapability = () => {
    if (newCapability.trim() && !capabilities.includes(newCapability.trim())) {
      setCapabilities([...capabilities, newCapability.trim()])
      setNewCapability('')
    }
  }

  const removeCapability = (cap: string) => {
    setCapabilities(capabilities.filter(c => c !== cap))
  }

  const addTag = () => {
    if (newTag.trim() && !tags.includes(newTag.trim())) {
      setTags([...tags, newTag.trim()])
      setNewTag('')
    }
  }

  const removeTag = (tag: string) => {
    setTags(tags.filter(t => t !== tag))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!agent) return

    setIsSubmitting(true)
    try {
      await updateAgent.mutateAsync({
        id: agentId,
        data: {
          description: description.trim() || undefined,
          system_prompt: systemPrompt.trim() || undefined,
          capabilities: capabilities.length > 0 ? capabilities : undefined,
          model_preference: modelPreference.trim() || undefined,
          temperature: temperature || '0.7',
          max_concurrent_tasks: maxConcurrentTasks || 1,
          tags: tags.length > 0 ? tags : undefined,
        },
      })
      router.push(`/agents/${agentId}`)
    } catch (error) {
      console.error('Failed to update agent:', error)
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

  if (!agent) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card>
          <CardContent className="p-12 text-center">
            <p className="text-muted-foreground mb-4">Agent not found</p>
            <Link href="/agents">
              <Button variant="outline">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Agents
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-3xl">
      <div className="mb-6">
        <Link href={`/agents/${agentId}`}>
          <Button variant="ghost" className="mb-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Agent
          </Button>
        </Link>
        <h1 className="text-3xl font-bold tracking-tight">Edit Agent: {agent.name}</h1>
        <p className="text-muted-foreground mt-2">
          Update agent configuration and settings
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Information */}
        <Card>
          <CardHeader>
            <CardTitle>Basic Information</CardTitle>
            <CardDescription>
              Agent name cannot be changed
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Agent Name</Label>
              <Input
                value={agent.name}
                disabled
                className="mt-1"
              />
            </div>

            <div>
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Brief description of what this agent does..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                className="mt-1 resize-none"
              />
            </div>
          </CardContent>
        </Card>

        {/* Agent Configuration */}
        <Card>
          <CardHeader>
            <CardTitle>Agent Configuration</CardTitle>
            <CardDescription>
              Configure the agent's behavior and preferences
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="systemPrompt">System Prompt</Label>
              <Textarea
                id="systemPrompt"
                placeholder="You are a helpful AI assistant specialized in..."
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                rows={4}
                className="mt-1 resize-none font-mono text-sm"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="modelPreference">Model Preference</Label>
                <Input
                  id="modelPreference"
                  placeholder="e.g., llama3.2, gpt-4"
                  value={modelPreference}
                  onChange={(e) => setModelPreference(e.target.value)}
                  className="mt-1"
                />
              </div>

              <div>
                <Label htmlFor="temperature">Temperature</Label>
                <Input
                  id="temperature"
                  type="number"
                  min="0"
                  max="2"
                  step="0.1"
                  placeholder="0.7"
                  value={temperature}
                  onChange={(e) => setTemperature(e.target.value)}
                  className="mt-1"
                />
              </div>
            </div>

            <div>
              <Label htmlFor="maxConcurrentTasks">Max Concurrent Tasks</Label>
              <Input
                id="maxConcurrentTasks"
                type="number"
                min="1"
                max="10"
                value={maxConcurrentTasks}
                onChange={(e) => setMaxConcurrentTasks(parseInt(e.target.value) || 1)}
                className="mt-1"
              />
            </div>
          </CardContent>
        </Card>

        {/* Capabilities */}
        <Card>
          <CardHeader>
            <CardTitle>Capabilities</CardTitle>
            <CardDescription>
              Define what this agent can do
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <Input
                placeholder="e.g., code_review, testing, documentation"
                value={newCapability}
                onChange={(e) => setNewCapability(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    addCapability()
                  }
                }}
              />
              <Button
                type="button"
                variant="outline"
                onClick={addCapability}
                disabled={!newCapability.trim()}
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            {capabilities.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {capabilities.map((cap) => (
                  <Badge key={cap} variant="secondary" className="flex items-center gap-1">
                    {cap}
                    <button
                      type="button"
                      onClick={() => removeCapability(cap)}
                      className="ml-1 hover:text-destructive"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Tags */}
        <Card>
          <CardHeader>
            <CardTitle>Tags</CardTitle>
            <CardDescription>
              Add tags for categorization and filtering
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <Input
                placeholder="e.g., production, experimental, beta"
                value={newTag}
                onChange={(e) => setNewTag(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    addTag()
                  }
                }}
              />
              <Button
                type="button"
                variant="outline"
                onClick={addTag}
                disabled={!newTag.trim()}
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            {tags.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {tags.map((tag) => (
                  <Badge key={tag} variant="outline" className="flex items-center gap-1">
                    {tag}
                    <button
                      type="button"
                      onClick={() => removeTag(tag)}
                      className="ml-1 hover:text-destructive"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex justify-end space-x-2">
          <Link href={`/agents/${agentId}`}>
            <Button type="button" variant="outline">
              Cancel
            </Button>
          </Link>
          <Button type="submit" disabled={isSubmitting}>
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
