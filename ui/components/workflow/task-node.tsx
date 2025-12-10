'use client'

import { memo } from 'react'
import { Handle, Position, NodeProps } from '@xyflow/react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { FileText, CheckCircle, Clock, XCircle, AlertCircle } from 'lucide-react'
import Link from 'next/link'

export interface TaskNodeData {
  type: 'task'
  label: string
  description: string
  status: string
  taskId: string
}

const statusConfig: Record<string, { icon: any; color: string; bg: string; variant: any }> = {
  completed: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-100', variant: 'default' },
  failed: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-100', variant: 'destructive' },
  cancelled: { icon: XCircle, color: 'text-gray-500', bg: 'bg-gray-100', variant: 'secondary' },
  in_progress: { icon: Clock, color: 'text-blue-500', bg: 'bg-blue-100', variant: 'default' },
  executing: { icon: Clock, color: 'text-blue-500', bg: 'bg-blue-100', variant: 'default' },
  pending: { icon: AlertCircle, color: 'text-yellow-500', bg: 'bg-yellow-100', variant: 'secondary' },
  pending_approval: { icon: AlertCircle, color: 'text-orange-500', bg: 'bg-orange-100', variant: 'secondary' },
  approved: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-100', variant: 'default' },
  paused: { icon: Clock, color: 'text-gray-500', bg: 'bg-gray-100', variant: 'secondary' },
}

export const TaskNode = memo(({ data }: NodeProps<TaskNodeData>) => {
  const config = statusConfig[data.status.toLowerCase()] || {
    icon: FileText,
    color: 'text-gray-500',
    bg: 'bg-gray-100',
    variant: 'secondary' as const,
  }
  const Icon = config.icon

  return (
    <Card className="w-64 shadow-lg">
      <Handle type="target" position={Position.Top} className="!bg-blue-500" />
      
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className={`p-2 rounded-lg ${config.bg}`}>
              <FileText className={`h-4 w-4 ${config.color}`} />
            </div>
            <CardTitle className="text-sm">{data.label}</CardTitle>
          </div>
          <Icon className={`h-4 w-4 ${config.color}`} />
        </div>
      </CardHeader>
      
      <CardContent className="pt-0 space-y-2">
        <p className="text-xs text-muted-foreground line-clamp-2">
          {data.description}
        </p>
        <div className="flex items-center justify-between">
          <Badge variant={config.variant} className="text-xs">
            {data.status}
          </Badge>
          <Link 
            href={`/tasks/${data.taskId}`}
            className="text-xs text-primary hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            View →
          </Link>
        </div>
      </CardContent>

      <Handle type="source" position={Position.Bottom} className="!bg-blue-500" />
    </Card>
  )
})

TaskNode.displayName = 'TaskNode'
