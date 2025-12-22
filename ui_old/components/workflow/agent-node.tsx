'use client'

import { memo } from 'react'
import { Handle, Position, NodeProps } from '@xyflow/react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Bot, CheckCircle, Clock, XCircle } from 'lucide-react'

export interface AgentNodeData {
  label: string
  role: string
  status: 'idle' | 'busy' | 'completed' | 'failed'
}

const statusConfig = {
  idle: { icon: Clock, color: 'text-gray-500', bg: 'bg-gray-100' },
  busy: { icon: Clock, color: 'text-blue-500', bg: 'bg-blue-100' },
  completed: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-100' },
  failed: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-100' },
}

export const AgentNode = memo(({ data }: NodeProps<AgentNodeData>) => {
  const config = statusConfig[data.status]
  const Icon = config.icon

  return (
    <Card className="w-64 shadow-lg">
      <Handle type="target" position={Position.Top} className="!bg-blue-500" />
      
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className={`p-2 rounded-lg ${config.bg}`}>
              <Bot className={`h-4 w-4 ${config.color}`} />
            </div>
            <CardTitle className="text-sm">{data.label}</CardTitle>
          </div>
          <Icon className={`h-4 w-4 ${config.color}`} />
        </div>
      </CardHeader>
      
      <CardContent className="pt-0">
        <Badge variant="outline" className="text-xs">
          {data.role}
        </Badge>
      </CardContent>

      <Handle type="source" position={Position.Bottom} className="!bg-blue-500" />
    </Card>
  )
})

AgentNode.displayName = 'AgentNode'
