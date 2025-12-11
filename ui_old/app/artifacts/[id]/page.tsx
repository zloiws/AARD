'use client'

import { use, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api/client'
import { useDeleteArtifact } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { formatDistanceToNow, format } from 'date-fns'
import { ArrowLeft, Loader2, Package, Code, FileText, CheckCircle, Clock, XCircle, AlertCircle, Copy, Trash2 } from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export default function ArtifactDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const router = useRouter()

  const { data: artifact, isLoading, error } = useQuery({
    queryKey: ['artifacts', id],
    queryFn: () => api.artifacts.get(id),
  })
  const deleteArtifact = useDeleteArtifact()
  const [isDeleting, setIsDeleting] = useState(false)

  const getStatusConfig = (status: string) => {
    const statusLower = status.toLowerCase()
    switch (statusLower) {
      case 'active':
        return { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-100', variant: 'default' as const }
      case 'draft':
        return { icon: FileText, color: 'text-gray-500', bg: 'bg-gray-100', variant: 'secondary' as const }
      case 'waiting_approval':
        return { icon: Clock, color: 'text-yellow-500', bg: 'bg-yellow-100', variant: 'secondary' as const }
      case 'deprecated':
        return { icon: XCircle, color: 'text-red-500', bg: 'bg-red-100', variant: 'destructive' as const }
      default:
        return { icon: AlertCircle, color: 'text-gray-500', bg: 'bg-gray-100', variant: 'secondary' as const }
    }
  }

  const handleCopy = (text: string, label: string) => {
    navigator.clipboard.writeText(text)
    toast.success(`${label} copied to clipboard`)
  }

  const handleDelete = async () => {
    if (!confirm(`Are you sure you want to delete artifact "${artifact?.name}"? This action cannot be undone.`)) {
      return
    }

    setIsDeleting(true)
    try {
      await deleteArtifact.mutateAsync(id)
      router.push('/artifacts')
    } catch (error: any) {
      console.error('Failed to delete artifact:', error)
      toast.error(`Failed to delete artifact: ${error?.message || 'Unknown error'}`)
    } finally {
      setIsDeleting(false)
    }
  }

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-center items-center min-h-[400px]">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </div>
    )
  }

  if (error || !artifact) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card>
          <CardContent className="p-6">
            <div className="text-center">
              <XCircle className="h-12 w-12 mx-auto mb-4 text-destructive" />
              <h2 className="text-2xl font-bold mb-2">Artifact Not Found</h2>
              <p className="text-muted-foreground mb-4">
                The artifact with ID {id} could not be found.
              </p>
              <Button onClick={() => router.push('/artifacts')} variant="outline">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Artifacts
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  const statusConfig = getStatusConfig(artifact.status)
  const StatusIcon = statusConfig.icon

  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl">
      <div className="mb-6">
        <Button
          variant="ghost"
          onClick={() => router.push('/artifacts')}
          className="mb-4"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Artifacts
        </Button>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{artifact.name}</h1>
            <p className="text-muted-foreground mt-2">
              {artifact.description || 'No description'}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={statusConfig.variant} className="flex items-center gap-2">
              <StatusIcon className="h-4 w-4" />
              {artifact.status}
            </Badge>
            <Badge variant="outline">{artifact.type}</Badge>
          </div>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {/* Main Content */}
        <div className="md:col-span-2 space-y-6">
          {/* Code/Prompt */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  {artifact.type === 'tool' ? (
                    <>
                      <Code className="h-5 w-5" />
                      Code
                    </>
                  ) : (
                    <>
                      <FileText className="h-5 w-5" />
                      Prompt
                    </>
                  )}
                </CardTitle>
                {(artifact.code || artifact.prompt) && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleCopy(artifact.code || artifact.prompt || '', 'Content')}
                  >
                    <Copy className="h-4 w-4 mr-2" />
                    Copy
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {artifact.code ? (
                <pre className="bg-muted p-4 rounded-md overflow-auto text-sm font-mono">
                  <code>{artifact.code}</code>
                </pre>
              ) : artifact.prompt ? (
                <div className="bg-muted p-4 rounded-md">
                  <p className="text-sm whitespace-pre-wrap">{artifact.prompt}</p>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Package className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No {artifact.type === 'tool' ? 'code' : 'prompt'} available</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Test Results */}
          {artifact.test_results && (
            <Card>
              <CardHeader>
                <CardTitle>Test Results</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="bg-muted p-4 rounded-md overflow-auto text-sm">
                  {JSON.stringify(artifact.test_results, null, 2)}
                </pre>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Details */}
          <Card>
            <CardHeader>
              <CardTitle>Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="text-sm font-medium text-muted-foreground">Type</div>
                <div className="text-sm mt-1">
                  <Badge variant="outline">{artifact.type}</Badge>
                </div>
              </div>
              <div>
                <div className="text-sm font-medium text-muted-foreground">Version</div>
                <div className="text-sm mt-1">{artifact.version}</div>
              </div>
              <div>
                <div className="text-sm font-medium text-muted-foreground">Status</div>
                <div className="text-sm mt-1">
                  <Badge variant={statusConfig.variant} className="flex items-center gap-2 w-fit">
                    <StatusIcon className="h-3 w-3" />
                    {artifact.status}
                  </Badge>
                </div>
              </div>
              {artifact.security_rating !== null && artifact.security_rating !== undefined && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground">Security Rating</div>
                  <div className="text-sm mt-1">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-muted rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${
                            artifact.security_rating >= 0.8
                              ? 'bg-green-500'
                              : artifact.security_rating >= 0.5
                              ? 'bg-yellow-500'
                              : 'bg-red-500'
                          }`}
                          style={{ width: `${artifact.security_rating * 100}%` }}
                        />
                      </div>
                      <span className="text-xs">{(artifact.security_rating * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                </div>
              )}
              {artifact.created_at && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground">Created</div>
                  <div className="text-sm mt-1">
                    {format(new Date(artifact.created_at), 'PPpp')}
                    <span className="text-muted-foreground ml-2">
                      ({formatDistanceToNow(new Date(artifact.created_at), { addSuffix: true })})
                    </span>
                  </div>
                </div>
              )}
              {artifact.created_by && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground">Created By</div>
                  <div className="text-sm mt-1">{artifact.created_by}</div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button variant="outline" className="w-full" disabled>
                Edit Artifact
              </Button>
              <Button variant="outline" className="w-full" disabled>
                Run Tests
              </Button>
              <Button variant="outline" className="w-full" disabled>
                View Dependencies
              </Button>
              <Button
                variant="destructive"
                className="w-full"
                onClick={handleDelete}
                disabled={isDeleting || deleteArtifact.isPending}
              >
                {isDeleting || deleteArtifact.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <Trash2 className="h-4 w-4 mr-2" />
                    Delete Artifact
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
