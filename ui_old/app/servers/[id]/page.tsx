'use client'

import { useServer, useServerModels, useDiscoverServer, useUpdateServer, useDeleteServer } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { formatDistanceToNow, format } from 'date-fns'
import { ArrowLeft, Server, CheckCircle, XCircle, Edit, RefreshCw, Trash2, Database, Settings } from 'lucide-react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { useState } from 'react'
import { toast } from 'sonner'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useUpdateModel, useCheckModelAvailability } from '@/lib/hooks/use-api'

const getStatusConfig = (isActive: boolean, isAvailable: boolean) => {
  if (!isActive) {
    return { label: 'Inactive', icon: XCircle, color: 'text-gray-500', bg: 'bg-gray-100' }
  }
  if (isAvailable) {
    return { label: 'Available', icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-100' }
  }
  return { label: 'Unavailable', icon: XCircle, color: 'text-red-500', bg: 'bg-red-100' }
}

export default function ServerDetailPage() {
  const params = useParams()
  const router = useRouter()
  const serverId = params.id as string
  const { data: server, isLoading } = useServer(serverId)
  const { data: models, refetch: refetchModels } = useServerModels(serverId)
  const discoverServer = useDiscoverServer()
  const updateServer = useUpdateServer()
  const deleteServer = useDeleteServer()
  const updateModel = useUpdateModel()
  const checkAvailability = useCheckModelAvailability()
  
  const [isDiscovering, setIsDiscovering] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)

  const handleDiscover = async () => {
    setIsDiscovering(true)
    try {
      const result = await discoverServer.mutateAsync(serverId)
      const message = result?.message || 'Models discovered successfully'
      const modelsFound = result?.models_found || 0
      const modelsAdded = result?.models_added || 0
      const modelsUpdated = result?.models_updated || 0
      const modelsDeactivated = result?.models_deactivated || 0
      const totalInDb = result?.total_in_db || 0
      
      const details = [
        `Found on server: ${modelsFound}`,
        `Added: ${modelsAdded}`,
        `Updated: ${modelsUpdated}`,
        modelsDeactivated > 0 ? `Deactivated: ${modelsDeactivated}` : null,
        `Total active in DB: ${totalInDb}`
      ].filter(Boolean).join('\n')
      
      toast.success(
        `${message}\n${details}`,
        { duration: 6000 }
      )
      
      // Refresh models list
      refetchModels()
    } catch (error: any) {
      console.error('Failed to discover models:', error)
      toast.error(`Failed to discover models: ${error?.message || 'Unknown error'}`)
    } finally {
      setIsDiscovering(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm(`Are you sure you want to delete server "${server?.name}"? This action cannot be undone.`)) {
      return
    }

    setIsDeleting(true)
    try {
      await deleteServer.mutateAsync(serverId)
      router.push('/servers')
    } catch (error) {
      console.error('Failed to delete server:', error)
    } finally {
      setIsDeleting(false)
    }
  }

  const handleToggleModelActive = async (modelId: string, currentState: boolean) => {
    try {
      await updateModel.mutateAsync({
        id: modelId,
        data: { is_active: !currentState },
      })
    } catch (error) {
      console.error('Failed to update model:', error)
    }
  }

  const handleCheckModel = async (modelId: string) => {
    try {
      const result = await checkAvailability.mutateAsync(modelId)
      if (result.is_available) {
        toast.success(`Model "${result.model_name}" is available`)
      } else {
        toast.error(`Model "${result.model_name}" is not available: ${result.error || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Failed to check model:', error)
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

  const statusConfig = getStatusConfig(server.is_active, server.is_available)
  const StatusIcon = statusConfig.icon

  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl">
      {/* Header */}
      <div className="mb-6">
        <Link href="/servers">
          <Button variant="ghost" className="mb-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Servers
          </Button>
        </Link>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className={`h-12 w-12 rounded-full ${statusConfig.bg} flex items-center justify-center`}>
              <Server className={`h-6 w-6 ${statusConfig.color}`} />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">
                {server.name}
              </h1>
              <div className="flex items-center space-x-2 mt-2">
                <Badge variant={server.is_active && server.is_available ? 'default' : 'secondary'}>
                  {statusConfig.label}
                </Badge>
                {server.is_default && (
                  <Badge variant="outline">Default</Badge>
                )}
              </div>
            </div>
          </div>
          <div className="flex gap-2">
            <Link href={`/servers/${serverId}/edit`}>
              <Button variant="outline">
                <Edit className="h-4 w-4 mr-2" />
                Edit
              </Button>
            </Link>
            <Button
              variant="outline"
              onClick={handleDiscover}
              disabled={isDiscovering}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${isDiscovering ? 'animate-spin' : ''}`} />
              Discover Models
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={isDeleting}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </Button>
          </div>
        </div>
      </div>

      <Tabs defaultValue="info" className="w-full">
        <TabsList>
          <TabsTrigger value="info">
            <Settings className="h-4 w-4 mr-2" />
            Information
          </TabsTrigger>
          <TabsTrigger value="models">
            <Database className="h-4 w-4 mr-2" />
            Models ({models?.length || 0})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="info" className="mt-4">
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Server Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground">URL</p>
                  <p className="font-mono text-sm">{server.url}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">API Version</p>
                  <p className="font-medium">{server.api_version}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Status</p>
                  <div className="flex items-center gap-2">
                    <StatusIcon className={`h-4 w-4 ${statusConfig.color}`} />
                    <p className="font-medium">{statusConfig.label}</p>
                  </div>
                </div>
                {server.description && (
                  <div>
                    <p className="text-sm text-muted-foreground">Description</p>
                    <p className="font-medium">{server.description}</p>
                  </div>
                )}
                <div>
                  <p className="text-sm text-muted-foreground">Created</p>
                  <p className="font-medium">
                    {formatDistanceToNow(new Date(server.created_at), { addSuffix: true })}
                  </p>
                </div>
                {server.last_checked_at && (
                  <div>
                    <p className="text-sm text-muted-foreground">Last Checked</p>
                    <p className="font-medium">
                      {formatDistanceToNow(new Date(server.last_checked_at), { addSuffix: true })}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Configuration</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground">Max Concurrent</p>
                  <p className="font-medium">{server.max_concurrent}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Priority</p>
                  <p className="font-medium">{server.priority}</p>
                </div>
                {server.capabilities && server.capabilities.length > 0 && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-2">Capabilities</p>
                    <div className="flex flex-wrap gap-2">
                      {server.capabilities.map((cap) => (
                        <Badge key={cap} variant="outline">
                          {cap}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="models" className="mt-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Server Models</CardTitle>
                  <CardDescription>
                    <div className="flex items-center gap-2">
                      <span>Models in database: <strong>{models?.length || 0}</strong></span>
                      {server.last_checked_at ? (
                        <span className="text-xs text-muted-foreground">
                          (Synced {formatDistanceToNow(new Date(server.last_checked_at), { addSuffix: true })})
                        </span>
                      ) : (
                        <span className="text-xs text-yellow-600">
                          ⚠️ Not synced - click "Sync from Server" to discover models
                        </span>
                      )}
                    </div>
                  </CardDescription>
                </div>
                <Button
                  variant="outline"
                  onClick={handleDiscover}
                  disabled={isDiscovering}
                >
                  <RefreshCw className={`h-4 w-4 mr-2 ${isDiscovering ? 'animate-spin' : ''}`} />
                  {isDiscovering ? 'Discovering...' : 'Sync from Server'}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {!models || models.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Database className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p className="font-medium mb-2">No models found in database</p>
                  <p className="text-sm mb-4">
                    Models are stored in the database after syncing from the Ollama server.
                    <br />
                    Click "Sync from Server" to discover models from <code className="text-xs bg-muted px-1 rounded">{server?.url}</code>
                  </p>
                  <Button
                    variant="default"
                    className="mt-4"
                    onClick={handleDiscover}
                    disabled={isDiscovering}
                  >
                    <RefreshCw className={`h-4 w-4 mr-2 ${isDiscovering ? 'animate-spin' : ''}`} />
                    {isDiscovering ? 'Syncing from Server...' : 'Sync from Server'}
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  {models.map((model) => (
                    <div
                      key={model.id}
                      className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent transition-colors"
                    >
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-2">
                          <span className="font-medium">{model.name}</span>
                          <Badge variant={model.is_active ? 'default' : 'secondary'}>
                            {model.is_active ? 'Active' : 'Inactive'}
                          </Badge>
                          {model.capabilities && model.capabilities.length > 0 && (
                            <div className="flex gap-1">
                              {model.capabilities.slice(0, 3).map((cap) => (
                                <Badge key={cap} variant="outline" className="text-xs">
                                  {cap}
                                </Badge>
                              ))}
                            </div>
                          )}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          <span className="font-mono text-xs">{model.model_name}</span>
                          {model.size_bytes && (
                            <span className="ml-4">
                              {(model.size_bytes / 1024 / 1024 / 1024).toFixed(2)} GB
                            </span>
                          )}
                          <span className="ml-4">Priority: {model.priority}</span>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleCheckModel(model.id)}
                          disabled={checkAvailability.isPending}
                        >
                          Check
                        </Button>
                        <Link href={`/models/${model.id}/edit`}>
                          <Button variant="outline" size="sm">
                            <Settings className="h-4 w-4" />
                          </Button>
                        </Link>
                        <Button
                          variant={model.is_active ? 'secondary' : 'default'}
                          size="sm"
                          onClick={() => handleToggleModelActive(model.id, model.is_active)}
                          disabled={updateModel.isPending}
                        >
                          {model.is_active ? 'Deactivate' : 'Activate'}
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
