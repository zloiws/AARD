'use client'

import { useState, useEffect } from 'react'
import { useServer, useUpdateServer } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { ArrowLeft, Loader2 } from 'lucide-react'
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

export default function EditServerPage() {
  const params = useParams()
  const router = useRouter()
  const serverId = params.id as string
  const { data: server, isLoading } = useServer(serverId)
  const updateServer = useUpdateServer()
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  // Form state
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [apiVersion, setApiVersion] = useState('v1')
  const [description, setDescription] = useState('')
  const [maxConcurrent, setMaxConcurrent] = useState(1)
  const [priority, setPriority] = useState(0)
  const [isActive, setIsActive] = useState(true)
  const [isDefault, setIsDefault] = useState(false)
  const [capabilities, setCapabilities] = useState<string[]>([])

  // Load server data
  useEffect(() => {
    if (server) {
      setName(server.name)
      setUrl(server.url)
      setApiVersion(server.api_version || 'v1')
      setDescription(server.description || '')
      setMaxConcurrent(server.max_concurrent || 1)
      setPriority(server.priority || 0)
      setIsActive(server.is_active)
      setIsDefault(server.is_default)
      setCapabilities(server.capabilities || [])
    }
  }, [server])

  const toggleCapability = (cap: string) => {
    if (capabilities.includes(cap)) {
      setCapabilities(capabilities.filter(c => c !== cap))
    } else {
      setCapabilities([...capabilities, cap])
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || !url.trim() || !server) return

    setIsSubmitting(true)
    try {
      await updateServer.mutateAsync({
        id: serverId,
        data: {
          name: name.trim(),
          url: url.trim(),
          api_version: apiVersion || 'v1',
          description: description.trim() || undefined,
          capabilities: capabilities.length > 0 ? capabilities : undefined,
          max_concurrent: maxConcurrent || 1,
          priority: priority || 0,
          is_active: isActive,
          is_default: isDefault,
        },
      })
      router.push(`/servers/${serverId}`)
    } catch (error) {
      console.error('Failed to update server:', error)
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

  if (!server) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card>
          <CardContent className="p-12 text-center">
            <p className="text-muted-foreground mb-4">Server not found</p>
            <Link href="/servers">
              <Button variant="outline">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Servers
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
        <Link href={`/servers/${serverId}`}>
          <Button variant="ghost" className="mb-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Server
          </Button>
        </Link>
        <h1 className="text-3xl font-bold tracking-tight">Edit Server: {server.name}</h1>
        <p className="text-muted-foreground mt-2">
          Update server configuration
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
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                required
                className="mt-1"
              />
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
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="isActive"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  className="h-4 w-4"
                />
                <Label htmlFor="isActive" className="cursor-pointer">
                  Server is active
                </Label>
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
          <Link href={`/servers/${serverId}`}>
            <Button type="button" variant="outline">
              Cancel
            </Button>
          </Link>
          <Button type="submit" disabled={!name.trim() || !url.trim() || isSubmitting}>
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
