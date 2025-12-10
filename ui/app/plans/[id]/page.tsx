'use client'

import { usePlan } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { formatDistanceToNow } from 'date-fns'
import { ArrowLeft, Workflow, CheckCircle, Clock, XCircle, Loader2 } from 'lucide-react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { Progress } from '@/components/ui/progress'

const getStepStatusConfig = (status: string) => {
  const statusLower = status?.toLowerCase() || ''
  if (statusLower === 'completed') {
    return { label: 'Completed', icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-100' }
  }
  if (statusLower === 'in_progress') {
    return { label: 'In Progress', icon: Loader2, color: 'text-blue-500', bg: 'bg-blue-100' }
  }
  if (statusLower === 'failed') {
    return { label: 'Failed', icon: XCircle, color: 'text-red-500', bg: 'bg-red-100' }
  }
  return { label: 'Pending', icon: Clock, color: 'text-yellow-500', bg: 'bg-yellow-100' }
}

export default function PlanDetailPage() {
  const params = useParams()
  const planId = params.id as string
  const { data: plan, isLoading } = usePlan(planId)

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

  if (!plan) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card>
          <CardContent className="p-12 text-center">
            <p className="text-muted-foreground mb-4">Plan not found</p>
            <Link href="/plans">
              <Button variant="outline">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Plans
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    )
  }

  const steps = plan.steps || []
  const completedSteps = steps.filter((s: any) => s.status === 'completed').length
  const progressPercent = steps.length > 0 ? (completedSteps / steps.length) * 100 : 0

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-6">
        <Link href="/plans">
          <Button variant="ghost" className="mb-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Plans
          </Button>
        </Link>
        <div className="flex items-center space-x-4">
          <div className="h-12 w-12 rounded-full bg-primary flex items-center justify-center">
            <Workflow className="h-6 w-6 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              {plan.goal || 'Untitled Plan'}
            </h1>
            <div className="flex items-center space-x-2 mt-2">
              <Badge variant="default">{plan.status}</Badge>
              {plan.version > 1 && (
                <Badge variant="outline">v{plan.version}</Badge>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Plan Info */}
        <Card>
          <CardHeader>
            <CardTitle>Plan Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm text-muted-foreground">Status</p>
              <p className="font-medium">{plan.status}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Version</p>
              <p className="font-medium">{plan.version}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Task ID</p>
              <p className="font-medium font-mono text-xs">{plan.task_id}</p>
            </div>
            {plan.strategy && (
              <div>
                <p className="text-sm text-muted-foreground">Strategy</p>
                {typeof plan.strategy === 'string' ? (
                  <p className="font-medium">{plan.strategy}</p>
                ) : (
                  <div className="space-y-2 mt-2">
                    {plan.strategy.approach && (
                      <div>
                        <p className="text-xs text-muted-foreground">Approach</p>
                        <p className="text-sm font-medium">{plan.strategy.approach}</p>
                      </div>
                    )}
                    {plan.strategy.assumptions && (
                      <div>
                        <p className="text-xs text-muted-foreground">Assumptions</p>
                        <p className="text-sm font-medium">{plan.strategy.assumptions}</p>
                      </div>
                    )}
                    {plan.strategy.constraints && (
                      <div>
                        <p className="text-xs text-muted-foreground">Constraints</p>
                        <p className="text-sm font-medium">{plan.strategy.constraints}</p>
                      </div>
                    )}
                    {plan.strategy.success_criteria && (
                      <div>
                        <p className="text-xs text-muted-foreground">Success Criteria</p>
                        <p className="text-sm font-medium">{plan.strategy.success_criteria}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
            <div>
              <p className="text-sm text-muted-foreground">Created</p>
              <p className="font-medium">
                {formatDistanceToNow(new Date(plan.created_at), { addSuffix: true })}
              </p>
            </div>
            {plan.approved_at && (
              <div>
                <p className="text-sm text-muted-foreground">Approved</p>
                <p className="font-medium">
                  {formatDistanceToNow(new Date(plan.approved_at), { addSuffix: true })}
                </p>
              </div>
            )}
            {plan.estimated_duration && (
              <div>
                <p className="text-sm text-muted-foreground">Estimated Duration</p>
                <p className="font-medium">{plan.estimated_duration} seconds</p>
              </div>
            )}
            {plan.actual_duration && (
              <div>
                <p className="text-sm text-muted-foreground">Actual Duration</p>
                <p className="font-medium">{plan.actual_duration} seconds</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Progress */}
        <Card>
          <CardHeader>
            <CardTitle>Execution Progress</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm text-muted-foreground">Completion</span>
                <span className="text-sm font-medium">{progressPercent.toFixed(0)}%</span>
              </div>
              <Progress value={progressPercent} />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Steps</p>
              <p className="font-medium">
                {completedSteps} of {steps.length} completed
              </p>
            </div>
            {plan.current_step !== undefined && (
              <div>
                <p className="text-sm text-muted-foreground">Current Step</p>
                <p className="font-medium">Step {plan.current_step + 1} of {steps.length}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Steps */}
        {steps.length > 0 && (
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle>Execution Steps</CardTitle>
              <CardDescription>
                {steps.length} step{steps.length !== 1 ? 's' : ''} in this plan
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {steps.map((step: any, index: number) => {
                  const stepConfig = getStepStatusConfig(step.status || 'pending')
                  const StepIcon = stepConfig.icon
                  const isCurrent = plan.current_step === index
                  const isActive = step.status === 'in_progress' || isCurrent

                  return (
                    <div
                      key={step.step_id || index}
                      className={`flex items-start space-x-4 p-4 rounded-lg border ${
                        isActive ? 'border-primary bg-accent' : ''
                      }`}
                    >
                      <div className={`h-10 w-10 rounded-full ${stepConfig.bg} flex items-center justify-center flex-shrink-0`}>
                        <StepIcon className={`h-5 w-5 ${stepConfig.color} ${isActive ? 'animate-spin' : ''}`} />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center space-x-2">
                            <span className="font-medium">Step {index + 1}</span>
                            {isCurrent && (
                              <Badge variant="default" className="text-xs">Current</Badge>
                            )}
                          </div>
                          <Badge variant="outline">{stepConfig.label}</Badge>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {step.description || 'No description'}
                        </p>
                        {step.assigned_agent && (
                          <p className="text-xs text-muted-foreground mt-1">
                            Agent: {step.assigned_agent}
                          </p>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
