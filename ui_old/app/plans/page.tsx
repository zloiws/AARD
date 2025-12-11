'use client'

import { usePlans } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { formatDistanceToNow } from 'date-fns'
import { Search, Workflow, CheckCircle, Clock, XCircle, FileText } from 'lucide-react'
import Link from 'next/link'
import { useState } from 'react'

const getStatusConfig = (status: string) => {
  const statusLower = status?.toLowerCase() || ''
  if (statusLower === 'active' || statusLower === 'approved') {
    return { label: 'Active', icon: CheckCircle, color: 'bg-green-500', variant: 'default' as const }
  }
  if (statusLower === 'draft' || statusLower === 'pending') {
    return { label: 'Draft', icon: Clock, color: 'bg-yellow-500', variant: 'secondary' as const }
  }
  if (statusLower === 'completed') {
    return { label: 'Completed', icon: CheckCircle, color: 'bg-blue-500', variant: 'default' as const }
  }
  if (statusLower === 'failed' || statusLower === 'rejected') {
    return { label: 'Failed', icon: XCircle, color: 'bg-red-500', variant: 'destructive' as const }
  }
  return { label: status || 'Unknown', icon: Workflow, color: 'bg-gray-500', variant: 'outline' as const }
}

export default function PlansPage() {
  const { data: plans, isLoading } = usePlans()
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  const filteredPlans = plans?.filter((plan) => {
    const strategyText = typeof plan.strategy === 'string' 
      ? plan.strategy 
      : plan.strategy?.approach || plan.strategy?.success_criteria || ''
    const matchesSearch = 
      plan.goal?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      strategyText.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = statusFilter === 'all' || plan.status?.toLowerCase() === statusFilter.toLowerCase()
    return matchesSearch && matchesStatus
  }) || []

  const statusCounts = {
    all: plans?.length || 0,
    active: plans?.filter(p => ['active', 'approved'].includes(p.status?.toLowerCase())).length || 0,
    draft: plans?.filter(p => ['draft', 'pending'].includes(p.status?.toLowerCase())).length || 0,
    completed: plans?.filter(p => p.status?.toLowerCase() === 'completed').length || 0,
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold tracking-tight">Plans</h1>
        <p className="text-muted-foreground mt-2">
          View and manage execution plans
        </p>
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search plans..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="flex gap-2">
              {['all', 'active', 'draft', 'completed'].map((status) => (
                <Button
                  key={status}
                  variant={statusFilter === status ? 'default' : 'outline'}
                  onClick={() => setStatusFilter(status)}
                  className="capitalize"
                >
                  {status} ({statusCounts[status as keyof typeof statusCounts]})
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Plans List */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="h-4 bg-muted rounded w-3/4 mb-2" />
                <div className="h-3 bg-muted rounded w-1/2" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : filteredPlans.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <p className="text-muted-foreground">
              {searchQuery || statusFilter !== 'all'
                ? 'No plans found matching your filters'
                : 'No plans yet'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredPlans.map((plan) => {
            const config = getStatusConfig(plan.status)
            const Icon = config.icon
            const stepsCount = plan.steps?.length || 0
            const completedSteps = plan.steps?.filter((s: any) => s.status === 'completed').length || 0

            return (
              <Card key={plan.id} className="hover:shadow-md transition-shadow">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <div className={`h-10 w-10 rounded-full ${config.color} flex items-center justify-center`}>
                          <Icon className="h-5 w-5 text-white" />
                        </div>
                        <div className="flex-1">
                          <Link href={`/plans/${plan.id}`}>
                            <h3 className="text-lg font-semibold hover:text-primary transition-colors">
                              {plan.goal || 'Untitled Plan'}
                            </h3>
                          </Link>
                          <div className="flex items-center space-x-2 mt-1">
                            <Badge variant={config.variant}>{config.label}</Badge>
                            {plan.version > 1 && (
                              <Badge variant="outline">v{plan.version}</Badge>
                            )}
                            {stepsCount > 0 && (
                              <span className="text-sm text-muted-foreground">
                                {completedSteps}/{stepsCount} steps
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="ml-13 space-y-1">
                        {plan.strategy && (
                          <p className="text-sm text-muted-foreground line-clamp-2">
                            {typeof plan.strategy === 'string' 
                              ? plan.strategy 
                              : plan.strategy.approach || plan.strategy.success_criteria || 'Strategy defined'}
                          </p>
                        )}
                        <div className="flex items-center space-x-4 text-xs text-muted-foreground">
                          <span>
                            Task: {plan.task_id?.slice(0, 8)}...
                          </span>
                          {plan.current_step !== undefined && (
                            <span>
                              Step {plan.current_step + 1} of {stepsCount}
                            </span>
                          )}
                          <span>
                            Created {formatDistanceToNow(new Date(plan.created_at), { addSuffix: true })}
                          </span>
                        </div>
                      </div>
                    </div>

                    <Link href={`/plans/${plan.id}`}>
                      <Button variant="ghost" size="icon">
                        →
                      </Button>
                    </Link>
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
