'use client'

import { useAgents } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { formatDistanceToNow } from 'date-fns'
import { Search, Plus, Bot, Activity, CheckCircle, XCircle } from 'lucide-react'
import Link from 'next/link'
import { useState } from 'react'

const getStatusConfig = (status: string) => {
  const statusLower = status?.toLowerCase() || ''
  if (statusLower === 'active') {
    return { label: 'Active', icon: Activity, color: 'bg-green-500', variant: 'default' as const }
  }
  if (statusLower === 'paused') {
    return { label: 'Paused', icon: XCircle, color: 'bg-yellow-500', variant: 'secondary' as const }
  }
  if (statusLower === 'deprecated') {
    return { label: 'Deprecated', icon: XCircle, color: 'bg-red-500', variant: 'destructive' as const }
  }
  return { label: status || 'Unknown', icon: Bot, color: 'bg-gray-500', variant: 'outline' as const }
}

export default function AgentsPage() {
  const { data: agents, isLoading } = useAgents()
  const [searchQuery, setSearchQuery] = useState('')

  const filteredAgents = agents?.filter((agent) =>
    agent.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    agent.description?.toLowerCase().includes(searchQuery.toLowerCase())
  ) || []

  return (
    <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Agents</h1>
            <p className="text-muted-foreground mt-2">
              Manage AI agents and their capabilities
            </p>
          </div>
          <Link href="/agents/new">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              New Agent
            </Button>
          </Link>
        </div>

        {/* Search */}
        <Card className="mb-6">
          <CardContent className="p-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search agents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
          </CardContent>
        </Card>

        {/* Agents Grid */}
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
        ) : filteredAgents.length === 0 ? (
          <Card>
            <CardContent className="p-12 text-center">
              <p className="text-muted-foreground mb-4">
                {searchQuery ? 'No agents found matching your search' : 'No agents yet'}
              </p>
              {!searchQuery && (
                <Link href="/agents/new">
                  <Button>
                    <Plus className="h-4 w-4 mr-2" />
                    Create Agent
                  </Button>
                </Link>
              )}
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredAgents.map((agent) => {
              const config = getStatusConfig(agent.status)
              const Icon = config.icon

              return (
                <Card key={agent.id} className="hover:shadow-md transition-shadow">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex items-center space-x-3">
                        <div className={`h-10 w-10 rounded-full ${config.color} flex items-center justify-center`}>
                          <Icon className="h-5 w-5 text-white" />
                        </div>
                        <div>
                          <CardTitle className="text-lg">
                            <Link href={`/agents/${agent.id}`} className="hover:text-primary transition-colors">
                              {agent.name}
                            </Link>
                          </CardTitle>
                          <Badge variant={config.variant} className="mt-1">
                            {config.label}
                          </Badge>
                        </div>
                      </div>
                    </div>
                    {agent.description && (
                      <CardDescription className="mt-2 line-clamp-2">
                        {agent.description}
                      </CardDescription>
                    )}
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2 text-sm">
                      {agent.capabilities && agent.capabilities.length > 0 && (
                        <div>
                          <p className="text-muted-foreground mb-1">Capabilities</p>
                          <div className="flex flex-wrap gap-1">
                            {agent.capabilities.slice(0, 3).map((cap) => (
                              <Badge key={cap} variant="outline" className="text-xs">
                                {cap}
                              </Badge>
                            ))}
                            {agent.capabilities.length > 3 && (
                              <Badge variant="outline" className="text-xs">
                                +{agent.capabilities.length - 3}
                              </Badge>
                            )}
                          </div>
                        </div>
                      )}
                      <div className="flex justify-between text-xs text-muted-foreground pt-2 border-t">
                        <span>
                          {agent.total_tasks_executed || 0} tasks
                        </span>
                        <span>
                          {agent.success_rate || 'N/A'} success
                        </span>
                      </div>
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
