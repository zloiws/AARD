'use client'

import { useState } from 'react'
import { useTasks, useAgents, usePlans, usePrompts } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Search as SearchIcon, FileText, Users, Workflow, Sparkles } from 'lucide-react'
import Link from 'next/link'
import { formatDistanceToNow } from 'date-fns'

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const { data: tasks } = useTasks()
  const { data: agents } = useAgents()
  const { data: plans } = usePlans()
  const { data: prompts } = usePrompts()

  const searchResults = {
    tasks: tasks?.filter((task) =>
      task.description?.toLowerCase().includes(query.toLowerCase())
    ) || [],
    agents: agents?.filter((agent) =>
      agent.name?.toLowerCase().includes(query.toLowerCase()) ||
      agent.description?.toLowerCase().includes(query.toLowerCase())
    ) || [],
    plans: plans?.filter((plan) => {
      const strategyText = typeof plan.strategy === 'string' 
        ? plan.strategy 
        : plan.strategy?.approach || plan.strategy?.success_criteria || ''
      return plan.goal?.toLowerCase().includes(query.toLowerCase()) ||
        strategyText.toLowerCase().includes(query.toLowerCase())
    }) || [],
    prompts: (prompts || []).filter((prompt: any) =>
      prompt.name?.toLowerCase().includes(query.toLowerCase()) ||
      prompt.prompt_text?.toLowerCase().includes(query.toLowerCase())
    ) || [],
  }

  const totalResults = searchResults.tasks.length + searchResults.agents.length + searchResults.plans.length + searchResults.prompts.length

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold tracking-tight">Search</h1>
        <p className="text-muted-foreground mt-2">
          Search across tasks, agents, plans, and prompts
        </p>
      </div>

      {/* Search Input */}
      <Card className="mb-6">
        <CardContent className="p-4">
          <div className="relative">
            <SearchIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-muted-foreground" />
            <Input
              placeholder="Search tasks, agents, plans, prompts..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="pl-10 text-lg h-12"
              autoFocus
            />
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {!query ? (
        <Card>
          <CardContent className="p-12 text-center">
            <SearchIcon className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">
              Enter a search query to find tasks, agents, and plans
            </p>
          </CardContent>
        </Card>
      ) : totalResults === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <p className="text-muted-foreground">
              No results found for "{query}"
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Tasks Results */}
          {searchResults.tasks.length > 0 && (
            <Card>
              <CardHeader>
                <div className="flex items-center space-x-2">
                  <FileText className="h-5 w-5" />
                  <CardTitle>Tasks ({searchResults.tasks.length})</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {searchResults.tasks.map((task) => (
                    <Link
                      key={task.task_id}
                      href={`/tasks/${task.task_id}`}
                      className="block p-3 rounded-lg border hover:bg-accent transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">{task.description || 'Untitled Task'}</p>
                          <p className="text-xs text-muted-foreground mt-1">
                            Updated {formatDistanceToNow(new Date(task.updated_at), { addSuffix: true })}
                          </p>
                        </div>
                        <Badge variant="outline">{task.status}</Badge>
                      </div>
                    </Link>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Agents Results */}
          {searchResults.agents.length > 0 && (
            <Card>
              <CardHeader>
                <div className="flex items-center space-x-2">
                  <Users className="h-5 w-5" />
                  <CardTitle>Agents ({searchResults.agents.length})</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {searchResults.agents.map((agent) => (
                    <Link
                      key={agent.id}
                      href={`/agents/${agent.id}`}
                      className="block p-3 rounded-lg border hover:bg-accent transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">{agent.name}</p>
                          {agent.description && (
                            <p className="text-xs text-muted-foreground mt-1 line-clamp-1">
                              {agent.description}
                            </p>
                          )}
                        </div>
                        <Badge variant="outline">{agent.status}</Badge>
                      </div>
                    </Link>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Plans Results */}
          {searchResults.plans.length > 0 && (
            <Card>
              <CardHeader>
                <div className="flex items-center space-x-2">
                  <Workflow className="h-5 w-5" />
                  <CardTitle>Plans ({searchResults.plans.length})</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {searchResults.plans.map((plan) => (
                    <Link
                      key={plan.id}
                      href={`/plans/${plan.id}`}
                      className="block p-3 rounded-lg border hover:bg-accent transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">{plan.goal || 'Untitled Plan'}</p>
                          {plan.strategy && (
                            <p className="text-xs text-muted-foreground mt-1 line-clamp-1">
                              {typeof plan.strategy === 'string' 
                                ? plan.strategy 
                                : plan.strategy.approach || plan.strategy.success_criteria || 'Strategy defined'}
                            </p>
                          )}
                        </div>
                        <Badge variant="outline">{plan.status}</Badge>
                      </div>
                    </Link>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Prompts Results */}
          {searchResults.prompts.length > 0 && (
            <Card>
              <CardHeader>
                <div className="flex items-center space-x-2">
                  <Sparkles className="h-5 w-5" />
                  <CardTitle>Prompts ({searchResults.prompts.length})</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {searchResults.prompts.map((prompt: any) => (
                    <Link
                      key={prompt.id}
                      href={`/prompts/${prompt.id}`}
                      className="block p-3 rounded-lg border hover:bg-accent transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">{prompt.name || 'Untitled Prompt'}</p>
                          {prompt.prompt_text && (
                            <p className="text-xs text-muted-foreground mt-1 line-clamp-1">
                              {prompt.prompt_text.substring(0, 100)}...
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          {prompt.prompt_type && (
                            <Badge variant="outline">{prompt.prompt_type}</Badge>
                          )}
                          {prompt.status && (
                            <Badge variant={prompt.status === 'active' ? 'default' : 'secondary'}>
                              {prompt.status}
                            </Badge>
                          )}
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
