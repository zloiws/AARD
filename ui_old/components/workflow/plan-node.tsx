'use client'

import { memo } from 'react'
import { Handle, Position, NodeProps } from '@xyflow/react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Workflow, CheckCircle, Clock, XCircle, AlertCircle } from 'lucide-react'
import Link from 'next/link'

export interface PlanNodeData {
  type: 'plan'
  label: string
  planId: string
  taskId: string
  status: string
  currentStep?: number
  totalSteps?: number
}

const statusConfig: Record<string, { icon: any; color: string; bg: string; variant: any }> = {
  completed: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-100', variant: 'default' },
  failed: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-100', variant: 'destructive' },
  in_progress: { icon: Clock, color: 'text-blue-500', bg: 'bg-blue-100', variant: 'default' },
  executing: { icon: Clock, color: 'text-blue-500', bg: 'bg-blue-100', variant: 'default' },
  pending: { icon: AlertCircle, color: 'text-yellow-500', bg: 'bg-yellow-100', variant: 'secondary' },
  approved: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-100', variant: 'default' },
}

export const PlanNode = memo(({ data }: NodeProps<PlanNodeData>) => {
  const config = statusConfig[data.status.toLowerCase()] || {
    icon: Workflow,
    color: 'text-gray-500',
    bg: 'bg-gray-100',
    variant: 'secondary' as const,
  }
  const Icon = config.icon

  const progress = data.totalSteps && data.currentStep
    ? `${data.currentStep}/${data.totalSteps}`
    : null

  return (
    <Card className="w-56 shadow-lg">
      <Handle type="target" position={Position.Top} className="!bg-purple-500" />
      
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className={`p-2 rounded-lg ${config.bg}`}>
              <Workflow className={`h-4 w-4 ${config.color}`} />
            </div>
            <CardTitle className="text-sm">{data.label}</CardTitle>
          </div>
          <Icon className={`h-4 w-4 ${config.color}`} />
        </div>
      </CardHeader>
      
      <CardContent className="pt-0 space-y-2">
        {progress && (
          <div className="text-xs text-muted-foreground">
            Step {progress}
          </div>
        )}
        <div className="flex items-center justify-between">
          <Badge variant={config.variant} className="text-xs">
            {data.status}
          </Badge>
          <Link 
            href={`/plans/${data.planId}`}
            className="text-xs text-primary hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            View →
          </Link>
        </div>
      </CardContent>

      <Handle type="source" position={Position.Bottom} className="!bg-purple-500" />
    </Card>
  )
})

PlanNode.displayName = 'PlanNode'
