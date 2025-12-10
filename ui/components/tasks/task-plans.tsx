'use client'

import { usePlans } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Workflow, ArrowRight } from 'lucide-react'
import Link from 'next/link'
import { formatDistanceToNow } from 'date-fns'

interface TaskPlansProps {
  taskId: string
}

export function TaskPlans({ taskId }: TaskPlansProps) {
  // Ensure taskId is a string
  const taskIdString = typeof taskId === 'string' ? taskId : String(taskId)
  const { data: plans, isLoading } = usePlans(taskIdString)

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Plans</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[1, 2].map((i) => (
              <div key={i} className="h-16 bg-muted rounded animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!plans || plans.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Plans</CardTitle>
          <CardDescription>No plans created for this task yet</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Plans ({plans.length})</CardTitle>
        <CardDescription>Execution plans for this task</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {plans.map((plan) => (
            <Link
              key={plan.id}
              href={`/plans/${plan.id}`}
              className="block p-3 rounded-lg border hover:bg-accent transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-1">
                    <Workflow className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium">{plan.goal || 'Untitled Plan'}</span>
                    <Badge variant="outline">{plan.status}</Badge>
                    {plan.version > 1 && (
                      <Badge variant="outline" className="text-xs">v{plan.version}</Badge>
                    )}
                  </div>
                  {plan.strategy && (
                    <p className="text-xs text-muted-foreground line-clamp-1">
                      {typeof plan.strategy === 'string' 
                        ? plan.strategy 
                        : plan.strategy.approach || plan.strategy.success_criteria || 'Strategy defined'}
                    </p>
                  )}
                  <p className="text-xs text-muted-foreground mt-1">
                    Created {formatDistanceToNow(new Date(plan.created_at), { addSuffix: true })}
                  </p>
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground" />
              </div>
            </Link>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
