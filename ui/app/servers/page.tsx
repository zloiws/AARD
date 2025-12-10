'use client'

import { useServers, useDeleteServer } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { formatDistanceToNow, format } from 'date-fns'
import { Search, Plus, Server, CheckCircle, XCircle, Settings, RefreshCw, Trash2 } from 'lucide-react'
import Link from 'next/link'
import { useState } from 'react'
import { toast } from 'sonner'

const getStatusConfig = (isActive: boolean, isAvailable: boolean) => {
  if (!isActive) {
    return { label: 'Inactive', icon: XCircle, color: 'bg-gray-500', variant: 'secondary' as const }
  }
  if (isAvailable) {
    return { label: 'Available', icon: CheckCircle, color: 'bg-green-500', variant: 'default' as const }
  }
  return { label: 'Unavailable', icon: XCircle, color: 'bg-red-500', variant: 'destructive' as const }
}

export default function ServersPage() {
  const { data: servers, isLoading } = useServers()
  const deleteServer = useDeleteServer()
  const [searchQuery, setSearchQuery] = useState('')

  const filteredServers = servers?.filter((server) =>
    server.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    server.url?.toLowerCase().includes(searchQuery.toLowerCase())
  ) || []

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete server "${name}"? This action cannot be undone.`)) {
      return
    }

    try {
      await deleteServer.mutateAsync(id)
    } catch (error) {
      console.error('Failed to delete server:', error)
    }
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Ollama Servers</h1>
          <p className="text-muted-foreground mt-2">
            Manage Ollama servers and their models
          </p>
        </div>
        <Link href="/servers/new">
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            New Server
          </Button>
        </Link>
      </div>

      {/* Search */}
      <Card className="mb-6">
        <CardContent className="p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search servers..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Servers List */}
      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="h-4 bg-muted rounded w-3/4 mb-2" />
                <div className="h-3 bg-muted rounded w-1/2" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : filteredServers.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <Server className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground mb-4">
              {searchQuery ? 'No servers found matching your search' : 'No servers configured yet'}
            </p>
            {!searchQuery && (
              <Link href="/servers/new">
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Server
                </Button>
              </Link>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredServers.map((server) => {
            const config = getStatusConfig(server.is_active, server.is_available)
            const Icon = config.icon

            return (
              <Card key={server.id} className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-3">
                      <div className={`h-10 w-10 rounded-full ${config.color} flex items-center justify-center`}>
                        <Icon className="h-5 w-5 text-white" />
                      </div>
                      <div className="flex-1">
                        <Link href={`/servers/${server.id}`}>
                          <CardTitle className="text-lg hover:text-primary transition-colors">
                            {server.name}
                          </CardTitle>
                        </Link>
                        <div className="flex items-center space-x-2 mt-1">
                          <Badge variant={config.variant}>{config.label}</Badge>
                          {server.is_default && (
                            <Badge variant="outline">Default</Badge>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                  {server.description && (
                    <CardDescription className="mt-2 line-clamp-2">
                      {server.description}
                    </CardDescription>
                  )}
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 text-sm">
                    <div>
                      <p className="text-muted-foreground">URL</p>
                      <p className="font-mono text-xs">{server.url}</p>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-muted-foreground">Models (in DB)</span>
                      <span className="font-medium">{server.models_count || 0}</span>
                    </div>
                    {server.last_checked_at ? (
                      <div className="text-xs text-muted-foreground mt-1">
                        Synced: {formatDistanceToNow(new Date(server.last_checked_at), { addSuffix: true })}
                      </div>
                    ) : (
                      <div className="text-xs text-yellow-600 mt-1">
                        ⚠️ Not synced yet
                      </div>
                    )}
                    {server.capabilities && server.capabilities.length > 0 && (
                      <div>
                        <p className="text-muted-foreground mb-1">Capabilities</p>
                        <div className="flex flex-wrap gap-1">
                          {server.capabilities.slice(0, 3).map((cap) => (
                            <Badge key={cap} variant="outline" className="text-xs">
                              {cap}
                            </Badge>
                          ))}
                          {server.capabilities.length > 3 && (
                            <Badge variant="outline" className="text-xs">
                              +{server.capabilities.length - 3}
                            </Badge>
                          )}
                        </div>
                      </div>
                    )}
                    <div className="flex justify-between text-xs text-muted-foreground pt-2 border-t">
                      <span>Priority: {server.priority}</span>
                      <span>Max: {server.max_concurrent}</span>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Updated {formatDistanceToNow(new Date(server.updated_at), { addSuffix: true })}
                    </div>
                  </div>
                  <div className="flex gap-2 mt-4">
                    <Link href={`/servers/${server.id}`} className="flex-1">
                      <Button variant="outline" size="sm" className="w-full">
                        <Settings className="h-4 w-4 mr-2" />
                        Manage
                      </Button>
                    </Link>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleDelete(server.id, server.name)}
                      disabled={deleteServer.isPending}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
