'use client'

import { useState } from 'react'
import { useApprovals, useApproveRequest, useRejectRequest } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { formatDistanceToNow } from 'date-fns'
import { CheckCircle2, XCircle, Loader2, Clock, AlertCircle } from 'lucide-react'
import Link from 'next/link'
import { toast } from 'sonner'

const getStatusConfig = (status: string) => {
  switch (status) {
    case 'approved':
      return { label: 'Approved', icon: CheckCircle2, color: 'text-green-500', variant: 'default' as const }
    case 'rejected':
      return { label: 'Rejected', icon: XCircle, color: 'text-red-500', variant: 'destructive' as const }
    case 'pending':
      return { label: 'Pending', icon: Clock, color: 'text-yellow-500', variant: 'secondary' as const }
    default:
      return { label: status, icon: AlertCircle, color: 'text-gray-500', variant: 'secondary' as const }
  }
}

export default function ApprovalsPage() {
  const { data: approvals, isLoading } = useApprovals()
  const approveRequest = useApproveRequest()
  const rejectRequest = useRejectRequest()

  const pendingApprovals = approvals?.filter(a => a.status === 'pending') || []
  const allApprovals = approvals || []

  const handleApprove = async (approvalId: string) => {
    if (!confirm('Approve this request?')) return

    try {
      await approveRequest.mutateAsync(approvalId)
    } catch (error) {
      console.error('Failed to approve:', error)
    }
  }

  const handleReject = async (approvalId: string) => {
    if (!confirm('Reject this request?')) return

    try {
      await rejectRequest.mutateAsync(approvalId)
    } catch (error) {
      console.error('Failed to reject:', error)
    }
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold tracking-tight">Approvals</h1>
        <p className="text-muted-foreground mt-2">
          Review and approve requests
        </p>
      </div>

      {/* Pending Approvals */}
      {pendingApprovals.length > 0 && (
        <Card className="mb-6 border-yellow-200 bg-yellow-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-yellow-600" />
              Pending Approvals ({pendingApprovals.length})
            </CardTitle>
            <CardDescription>
              Requests waiting for your approval
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {pendingApprovals.map((approval) => (
                <Card key={approval.id} className="border-l-4 border-l-yellow-500">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="font-semibold mb-2">{approval.request_type || 'Approval Request'}</h3>
                        {(approval as any).description && (
                          <p className="text-sm text-muted-foreground mb-2">{(approval as any).description}</p>
                        )}
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                          {(approval as any).requested_by && (
                            <span>Requested by: {(approval as any).requested_by}</span>
                          )}
                          {approval.created_at && (
                            <span>
                              {formatDistanceToNow(new Date(approval.created_at), { addSuffix: true })}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="default"
                          size="sm"
                          onClick={() => handleApprove(approval.id)}
                          disabled={approveRequest.isPending}
                        >
                          <CheckCircle2 className="h-4 w-4 mr-2" />
                          Approve
                        </Button>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleReject(approval.id)}
                          disabled={rejectRequest.isPending}
                        >
                          <XCircle className="h-4 w-4 mr-2" />
                          Reject
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* All Approvals */}
      <Card>
        <CardHeader>
          <CardTitle>All Approvals</CardTitle>
          <CardDescription>
            {allApprovals.length} approval request(s)
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : allApprovals.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <AlertCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No approval requests found</p>
            </div>
          ) : (
            <div className="space-y-3">
              {allApprovals.map((approval) => {
                const config = getStatusConfig(approval.status)
                const Icon = config.icon

                return (
                  <Card key={approval.id} className={`border-l-4 ${
                    approval.status === 'approved' ? 'border-l-green-500' :
                    approval.status === 'rejected' ? 'border-l-red-500' :
                    'border-l-yellow-500'
                  }`}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <Icon className={`h-4 w-4 ${config.color}`} />
                            <h3 className="font-semibold">{approval.request_type || 'Approval Request'}</h3>
                            <Badge variant={config.variant}>{config.label}</Badge>
                          </div>
                          {(approval as any).description && (
                            <p className="text-sm text-muted-foreground mb-2">{(approval as any).description}</p>
                          )}
                          <div className="flex items-center gap-4 text-sm text-muted-foreground">
                            {(approval as any).requested_by && (
                              <span>Requested by: {(approval as any).requested_by}</span>
                            )}
                            {approval.created_at && (
                              <span>
                                {formatDistanceToNow(new Date(approval.created_at), { addSuffix: true })}
                              </span>
                            )}
                            {(approval as any).approved_by && (
                              <span>Approved by: {(approval as any).approved_by}</span>
                            )}
                          </div>
                        </div>
                        {approval.status === 'pending' && (
                          <div className="flex gap-2">
                            <Button
                              variant="default"
                              size="sm"
                              onClick={() => handleApprove(approval.id)}
                              disabled={approveRequest.isPending}
                            >
                              <CheckCircle2 className="h-4 w-4 mr-2" />
                              Approve
                            </Button>
                            <Button
                              variant="destructive"
                              size="sm"
                              onClick={() => handleReject(approval.id)}
                              disabled={rejectRequest.isPending}
                            >
                              <XCircle className="h-4 w-4 mr-2" />
                              Reject
                            </Button>
                          </div>
                        )}
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
