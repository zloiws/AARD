'use client'

import { useState } from 'react'
import { useCreateServer } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { ArrowLeft, Loader2, Plus, X } from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Badge } from '@/components/ui/badge'

const CAPABILITY_OPTIONS = [
  'code_generation',
  'code_analysis',
  'reasoning',
  'planning',
  'general_chat',
  'embeddings',
]

export default function NewServerPage() {
  const router = useRouter()
  const createServer = useCreateServer()
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  // Form state
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [apiVersion, setApiVersion] = useState('v1')
  const [description, setDescription] = useState('')
  const [maxConcurrent, setMaxConcurrent] = useState(1)
  const [priority, setPriority] = useState(0)
  const [isDefault, setIsDefault] = useState(false)
  const [capabilities, setCapabilities] = useState<string[]>([])

  const toggleCapability = (cap: string) => {
    if (capabilities.includes(cap)) {
      setCapabilities(capabilities.filter(c => c !== cap))
    } else {
      setCapabilities([...capabilities, cap])
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || !url.trim()) return

    setIsSubmitting(true)
    try {
      const result = await createServer.mutateAsync({
        name: name.trim(),
        url: url.trim(),
        api_version: apiVersion || 'v1',
        description: description.trim() || undefined,
        capabilities: capabilities.length > 0 ? capabilities : undefined,
        max_concurrent: maxConcurrent || 1,
        priority: priority || 0,
        is_default: isDefault,
      })
      router.push(`/servers/${result.id}`)
    } catch (error) {
      console.error('Failed to create server:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-3xl">
      <div className="mb-6">
        <Link href="/servers">
          <Button variant="ghost" className="mb-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Servers
          </Button>
        </Link>
        <h1 className="text-3xl font-bold tracking-tight">Add New Server</h1>
        <p className="text-muted-foreground mt-2">
          Configure a new Ollama server connection
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Information */}
        <Card>
          <CardHeader>
            <CardTitle>Server Information</CardTitle>
            <CardDescription>
              Basic server connection details
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="name">Server Name *</Label>
              <Input
                id="name"
                placeholder="e.g., Local Ollama, Production Server"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="mt-1"
              />
            </div>

            <div>
              <Label htmlFor="url">Server URL *</Label>
              <Input
                id="url"
                placeholder="e.g., http://10.39.0.6:11434"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                required
                className="mt-1"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Base URL of the Ollama server (without /v1)
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="apiVersion">API Version</Label>
                <Input
                  id="apiVersion"
                  value={apiVersion}
                  onChange={(e) => setApiVersion(e.target.value)}
                  className="mt-1"
                />
              </div>
            </div>

            <div>
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Optional description..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                className="mt-1 resize-none"
              />
            </div>
          </CardContent>
        </Card>

        {/* Configuration */}
        <Card>
          <CardHeader>
            <CardTitle>Server Configuration</CardTitle>
            <CardDescription>
              Configure server capabilities and limits
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="maxConcurrent">Max Concurrent Requests</Label>
                <Input
                  id="maxConcurrent"
                  type="number"
                  min="1"
                  max="10"
                  value={maxConcurrent}
                  onChange={(e) => setMaxConcurrent(parseInt(e.target.value) || 1)}
                  className="mt-1"
                />
              </div>

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
                  Higher priority = selected first
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="isDefault"
                checked={isDefault}
                onChange={(e) => setIsDefault(e.target.checked)}
                className="h-4 w-4"
              />
              <Label htmlFor="isDefault" className="cursor-pointer">
                Set as default server
              </Label>
            </div>
          </CardContent>
        </Card>

        {/* Capabilities */}
        <Card>
          <CardHeader>
            <CardTitle>Capabilities</CardTitle>
            <CardDescription>
              Select what this server can do
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
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex justify-end space-x-2">
          <Link href="/servers">
            <Button type="button" variant="outline">
              Cancel
            </Button>
          </Link>
          <Button type="submit" disabled={!name.trim() || !url.trim() || isSubmitting}>
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Creating...
              </>
            ) : (
              'Create Server'
            )}
          </Button>
        </div>
      </form>
    </div>
  )
}
