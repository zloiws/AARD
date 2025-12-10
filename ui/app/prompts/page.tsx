'use client'

import { usePrompts } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { formatDistanceToNow } from 'date-fns'
import { Search, Plus, FileText, CheckCircle, XCircle, Clock, Sparkles } from 'lucide-react'
import Link from 'next/link'
import { useState } from 'react'

const getStatusConfig = (status: string) => {
  const statusLower = status?.toLowerCase() || ''
  if (statusLower === 'active') {
    return { label: 'Active', icon: CheckCircle, color: 'bg-green-500', variant: 'default' as const }
  }
  if (statusLower === 'testing') {
    return { label: 'Testing', icon: Clock, color: 'bg-yellow-500', variant: 'secondary' as const }
  }
  if (statusLower === 'deprecated') {
    return { label: 'Deprecated', icon: XCircle, color: 'bg-red-500', variant: 'destructive' as const }
  }
  return { label: status || 'Unknown', icon: FileText, color: 'bg-gray-500', variant: 'outline' as const }
}

const getTypeConfig = (type: string) => {
  const typeLower = type?.toLowerCase() || ''
  const configs: Record<string, { label: string; color: string }> = {
    system: { label: 'System', color: 'bg-blue-500' },
    agent: { label: 'Agent', color: 'bg-purple-500' },
    tool: { label: 'Tool', color: 'bg-orange-500' },
    meta: { label: 'Meta', color: 'bg-pink-500' },
    context: { label: 'Context', color: 'bg-cyan-500' },
  }
  return configs[typeLower] || { label: type || 'Unknown', color: 'bg-gray-500' }
}

export default function PromptsPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  
  const { data: prompts, isLoading } = usePrompts({
    name: searchQuery || undefined,
    prompt_type: typeFilter !== 'all' ? typeFilter : undefined,
    status: statusFilter !== 'all' ? statusFilter : undefined,
  })

  const filteredPrompts = prompts?.filter((prompt) => {
    const matchesSearch = 
      prompt.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      prompt.prompt_text?.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesSearch
  }) || []

  const typeCounts = {
    all: prompts?.length || 0,
    system: prompts?.filter(p => p.prompt_type?.toLowerCase() === 'system').length || 0,
    agent: prompts?.filter(p => p.prompt_type?.toLowerCase() === 'agent').length || 0,
    tool: prompts?.filter(p => p.prompt_type?.toLowerCase() === 'tool').length || 0,
    meta: prompts?.filter(p => p.prompt_type?.toLowerCase() === 'meta').length || 0,
    context: prompts?.filter(p => p.prompt_type?.toLowerCase() === 'context').length || 0,
  }

  const statusCounts = {
    all: prompts?.length || 0,
    active: prompts?.filter(p => p.status?.toLowerCase() === 'active').length || 0,
    testing: prompts?.filter(p => p.status?.toLowerCase() === 'testing').length || 0,
    deprecated: prompts?.filter(p => p.status?.toLowerCase() === 'deprecated').length || 0,
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Prompts</h1>
          <p className="text-muted-foreground mt-2">
            Manage and evolve AI prompts
          </p>
        </div>
        <Link href="/prompts/new">
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            New Prompt
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search prompts..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Type:</span>
                {['all', 'system', 'agent', 'tool', 'meta', 'context'].map((type) => (
                  <Button
                    key={type}
                    variant={typeFilter === type ? 'default' : 'outline'}
                    onClick={() => setTypeFilter(type)}
                    size="sm"
                    className="capitalize"
                  >
                    {type} ({typeCounts[type as keyof typeof typeCounts]})
                  </Button>
                ))}
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Status:</span>
                {['all', 'active', 'testing', 'deprecated'].map((status) => (
                  <Button
                    key={status}
                    variant={statusFilter === status ? 'default' : 'outline'}
                    onClick={() => setStatusFilter(status)}
                    size="sm"
                    className="capitalize"
                  >
                    {status} ({statusCounts[status as keyof typeof statusCounts]})
                  </Button>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Prompts List */}
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
      ) : filteredPrompts.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <Sparkles className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground mb-4">
              {searchQuery || typeFilter !== 'all' || statusFilter !== 'all'
                ? 'No prompts found matching your filters'
                : 'No prompts yet'}
            </p>
            {!searchQuery && typeFilter === 'all' && statusFilter === 'all' && (
              <Link href="/prompts/new">
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Prompt
                </Button>
              </Link>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredPrompts.map((prompt) => {
            const statusConfig = getStatusConfig(prompt.status)
            const typeConfig = getTypeConfig(prompt.prompt_type)
            const StatusIcon = statusConfig.icon

            return (
              <Card key={prompt.id} className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <Link href={`/prompts/${prompt.id}`}>
                        <CardTitle className="text-lg hover:text-primary transition-colors">
                          {prompt.name}
                        </CardTitle>
                      </Link>
                      <div className="flex items-center gap-2 mt-2">
                        <Badge variant="outline" className="text-xs">
                          {typeConfig.label}
                        </Badge>
                        <Badge variant={statusConfig.variant} className="text-xs">
                          {statusConfig.label}
                        </Badge>
                        {prompt.version > 1 && (
                          <Badge variant="outline" className="text-xs">
                            v{prompt.version}
                          </Badge>
                        )}
                      </div>
                    </div>
                    <div className={`h-8 w-8 rounded-full ${typeConfig.color} flex items-center justify-center flex-shrink-0`}>
                      <FileText className="h-4 w-4 text-white" />
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground line-clamp-3 mb-4">
                    {prompt.prompt_text}
                  </p>
                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between text-muted-foreground">
                      <span>Level: {prompt.level}</span>
                      <span>Used: {prompt.usage_count || 0}</span>
                    </div>
                    {prompt.success_rate !== null && prompt.success_rate !== undefined && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Success Rate:</span>
                        <span className="font-medium">
                          {(prompt.success_rate * 100).toFixed(1)}%
                        </span>
                      </div>
                    )}
                    <div className="text-muted-foreground pt-2 border-t">
                      Created {formatDistanceToNow(new Date(prompt.created_at), { addSuffix: true })}
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
