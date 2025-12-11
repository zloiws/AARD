'use client'

import { useState } from 'react'
import { useAgentGymTests, useAgents } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { formatDistanceToNow } from 'date-fns'
import { Plus, Loader2, Search, Filter, Play, Edit, Trash2, TestTube } from 'lucide-react'
import Link from 'next/link'
import { toast } from 'sonner'

const TEST_TYPES = [
  { value: '', label: 'All Types' },
  { value: 'unit', label: 'Unit Test' },
  { value: 'integration', label: 'Integration Test' },
  { value: 'e2e', label: 'End-to-End Test' },
  { value: 'performance', label: 'Performance Test' },
  { value: 'regression', label: 'Regression Test' },
]

export default function AgentGymPage() {
  const [agentIdFilter, setAgentIdFilter] = useState('')
  const [testTypeFilter, setTestTypeFilter] = useState('')
  const [searchQuery, setSearchQuery] = useState('')

  const { data: agents } = useAgents()
  const { data: tests, isLoading } = useAgentGymTests({
    agent_id: agentIdFilter || undefined,
    test_type: testTypeFilter || undefined,
  })

  const filteredTests = tests?.filter((test) =>
    !searchQuery || test.name?.toLowerCase().includes(searchQuery.toLowerCase())
  ) || []

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Agent Gym</h1>
            <p className="text-muted-foreground mt-2">
              Test and benchmark your agents
            </p>
          </div>
          <Link href="/agent-gym/new">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              New Test
            </Button>
          </Link>
        </div>
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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <Label>Agent</Label>
              <Select value={agentIdFilter} onValueChange={setAgentIdFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="All Agents" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All Agents</SelectItem>
                  {agents?.map((agent) => (
                    <SelectItem key={agent.id} value={agent.id}>
                      {agent.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Test Type</Label>
              <Select value={testTypeFilter} onValueChange={setTestTypeFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="All Types" />
                </SelectTrigger>
                <SelectContent>
                  {TEST_TYPES.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Search</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search tests..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tests List */}
      <Card>
        <CardHeader>
          <CardTitle>Agent Tests</CardTitle>
          <CardDescription>
            {filteredTests.length} test(s) found
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : filteredTests.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <TestTube className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No tests found</p>
              <Link href="/agent-gym/new">
                <Button variant="outline" className="mt-4">
                  <Plus className="h-4 w-4 mr-2" />
                  Create First Test
                </Button>
              </Link>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredTests.map((test) => {
                const agent = agents?.find(a => a.id === test.agent_id)
                
                return (
                  <Card key={test.id} className="hover:shadow-md transition-shadow">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <Link href={`/agent-gym/${test.id}`}>
                              <h3 className="font-semibold text-lg hover:text-primary transition-colors">
                                {test.name}
                              </h3>
                            </Link>
                            <Badge variant="outline">{test.test_type}</Badge>
                            {test.tags && test.tags.length > 0 && (
                              <div className="flex gap-1">
                                {test.tags.slice(0, 3).map((tag) => (
                                  <Badge key={tag} variant="secondary" className="text-xs">
                                    {tag}
                                  </Badge>
                                ))}
                              </div>
                            )}
                          </div>
                          {test.description && (
                            <p className="text-sm text-muted-foreground mb-2 line-clamp-2">
                              {test.description}
                            </p>
                          )}
                          <div className="flex items-center gap-4 text-sm text-muted-foreground">
                            <span>Agent: {agent?.name || test.agent_id.substring(0, 8)}...</span>
                            <span>Timeout: {test.timeout_seconds}s</span>
                            <span>Max Retries: {test.max_retries}</span>
                            {test.created_at && (
                              <span>
                                Created {formatDistanceToNow(new Date(test.created_at), { addSuffix: true })}
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Link href={`/agent-gym/${test.id}`}>
                            <Button variant="outline" size="sm">
                              <Play className="h-4 w-4 mr-2" />
                              Run
                            </Button>
                          </Link>
                          <Link href={`/agent-gym/${test.id}/edit`}>
                            <Button variant="outline" size="sm">
                              <Edit className="h-4 w-4" />
                            </Button>
                          </Link>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
