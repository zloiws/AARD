'use client'

import { usePrompt, usePromptVersions, usePromptMetrics, useUpdatePrompt, useDeletePrompt, useCreatePromptVersion } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { formatDistanceToNow } from 'date-fns'
import { ArrowLeft, FileText, CheckCircle, XCircle, Clock, Edit, Trash2, Copy, TrendingUp, GitBranch } from 'lucide-react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { Progress } from '@/components/ui/progress'
import { useState, useEffect } from 'react'
import { toast } from 'sonner'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'

const getStatusConfig = (status: string) => {
  const statusLower = status?.toLowerCase() || ''
  if (statusLower === 'active') {
    return { label: 'Active', icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-100' }
  }
  if (statusLower === 'testing') {
    return { label: 'Testing', icon: Clock, color: 'text-yellow-500', bg: 'bg-yellow-100' }
  }
  if (statusLower === 'deprecated') {
    return { label: 'Deprecated', icon: XCircle, color: 'text-red-500', bg: 'bg-red-100' }
  }
  return { label: status || 'Unknown', icon: Clock, color: 'text-gray-500', bg: 'bg-gray-100' }
}

const getTypeConfig = (type: string) => {
  const typeLower = type?.toLowerCase() || ''
  const configs: Record<string, { label: string; color: string }> = {
    system: { label: 'System', color: 'bg-blue-500' },
    agent: { label: 'Agent', color: 'bg-purple-500' },
    tool: { label: 'Tool', color: 'bg-orange-500' },
    meta: { label: 'Meta', color: 'bg-pink-500' },
    context: { label: 'Context', color: 'bg-cyan-500' },
  }
  return configs[typeLower] || { label: type || 'Unknown', color: 'bg-gray-500' }
}

export default function PromptDetailPage() {
  const params = useParams()
  const router = useRouter()
  const promptId = params.id as string
  const { data: prompt, isLoading } = usePrompt(promptId)
  const { data: versions } = usePromptVersions(promptId)
  const { data: metrics } = usePromptMetrics(promptId)
  const updatePrompt = useUpdatePrompt()
  const deletePrompt = useDeletePrompt()
  const createVersion = useCreatePromptVersion()
  
  const [isDeleting, setIsDeleting] = useState(false)
  const [versionDialogOpen, setVersionDialogOpen] = useState(false)
  const [newVersionText, setNewVersionText] = useState('')

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this prompt? This action cannot be undone.')) {
      return
    }

    setIsDeleting(true)
    try {
      await deletePrompt.mutateAsync(promptId)
      toast.success('Prompt deleted successfully')
      router.push('/prompts')
    } catch (error) {
      console.error('Failed to delete prompt:', error)
    } finally {
      setIsDeleting(false)
    }
  }

  const handleDeprecate = async () => {
    try {
      await updatePrompt.mutateAsync({
        id: promptId,
        data: { status: 'deprecated' },
      })
    } catch (error) {
      console.error('Failed to deprecate prompt:', error)
    }
  }

  const copyPromptText = () => {
    if (prompt?.prompt_text) {
      navigator.clipboard.writeText(prompt.prompt_text)
      toast.success('Prompt text copied to clipboard')
    }
  }

  const handleCreateVersion = async () => {
    if (!newVersionText.trim()) return
    
    try {
      const result = await createVersion.mutateAsync({
        id: promptId,
        prompt_text: newVersionText.trim(),
      })
      setVersionDialogOpen(false)
      setNewVersionText('')
      router.push(`/prompts/${result.id}`)
    } catch (error) {
      console.error('Failed to create version:', error)
    }
  }

  useEffect(() => {
    if (prompt) {
      setNewVersionText(prompt.prompt_text)
    }
  }, [prompt])

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

  if (!prompt) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card>
          <CardContent className="p-12 text-center">
            <p className="text-muted-foreground mb-4">Prompt not found</p>
            <Link href="/prompts">
              <Button variant="outline">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Prompts
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    )
  }

  const statusConfig = getStatusConfig(prompt.status)
  const typeConfig = getTypeConfig(prompt.prompt_type)
  const StatusIcon = statusConfig.icon

  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl">
      {/* Header */}
      <div className="mb-6">
        <Link href="/prompts">
          <Button variant="ghost" className="mb-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Prompts
          </Button>
        </Link>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className={`h-12 w-12 rounded-full ${typeConfig.color} flex items-center justify-center`}>
              <FileText className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">
                {prompt.name}
              </h1>
              <div className="flex items-center space-x-2 mt-2">
                <Badge variant="outline">{typeConfig.label}</Badge>
                <Badge variant={statusConfig.label === 'Active' ? 'default' : 'secondary'}>
                  {statusConfig.label}
                </Badge>
                {prompt.version > 1 && (
                  <Badge variant="outline">v{prompt.version}</Badge>
                )}
              </div>
            </div>
          </div>
          <div className="flex gap-2">
            <Link href={`/prompts/${promptId}/edit`}>
              <Button variant="outline">
                <Edit className="h-4 w-4 mr-2" />
                Edit
              </Button>
            </Link>
            <Dialog open={versionDialogOpen} onOpenChange={setVersionDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="outline">
                  <GitBranch className="h-4 w-4 mr-2" />
                  New Version
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>Create New Version</DialogTitle>
                  <DialogDescription>
                    Create a new version of this prompt. The new version will be based on the current prompt text.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div>
                    <Label htmlFor="versionText">Prompt Text</Label>
                    <Textarea
                      id="versionText"
                      value={newVersionText}
                      onChange={(e) => setNewVersionText(e.target.value)}
                      rows={12}
                      className="mt-1 resize-none font-mono text-sm"
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setVersionDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleCreateVersion} disabled={!newVersionText.trim() || createVersion.isPending}>
                    {createVersion.isPending ? 'Creating...' : 'Create Version'}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
            <Button variant="outline" onClick={copyPromptText}>
              <Copy className="h-4 w-4 mr-2" />
              Copy
            </Button>
            {prompt.status !== 'deprecated' && (
              <Button variant="outline" onClick={handleDeprecate}>
                Deprecate
              </Button>
            )}
            <Button variant="destructive" onClick={handleDelete} disabled={isDeleting}>
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </Button>
          </div>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Prompt Text */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Prompt Text</CardTitle>
            <CardDescription>
              The actual prompt content
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="bg-muted p-4 rounded-lg font-mono text-sm whitespace-pre-wrap break-words">
              {prompt.prompt_text}
            </div>
          </CardContent>
        </Card>

        {/* Prompt Info */}
        <Card>
          <CardHeader>
            <CardTitle>Prompt Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm text-muted-foreground">Type</p>
              <p className="font-medium">{typeConfig.label}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Level</p>
              <p className="font-medium">{prompt.level}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Version</p>
              <p className="font-medium">{prompt.version}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Status</p>
              <div className="flex items-center gap-2">
                <StatusIcon className={`h-4 w-4 ${statusConfig.color}`} />
                <p className="font-medium">{statusConfig.label}</p>
              </div>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Created</p>
              <p className="font-medium">
                {formatDistanceToNow(new Date(prompt.created_at), { addSuffix: true })}
              </p>
            </div>
            {prompt.parent_prompt_id && (
              <div>
                <p className="text-sm text-muted-foreground">Parent Prompt</p>
                <Link href={`/prompts/${prompt.parent_prompt_id}`}>
                  <Button variant="link" className="p-0 h-auto">
                    View Parent
                  </Button>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Metrics */}
        <Card>
          <CardHeader>
            <CardTitle>Metrics</CardTitle>
            <CardDescription>
              Performance and usage statistics
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm text-muted-foreground">Usage Count</span>
                <span className="text-sm font-medium">{prompt.usage_count || 0}</span>
              </div>
            </div>
            {metrics && (
              <>
                {metrics.success_rate !== null && metrics.success_rate !== undefined && (
                  <div>
                    <div className="flex justify-between mb-2">
                      <span className="text-sm text-muted-foreground">Success Rate</span>
                      <span className="text-sm font-medium">
                        {(metrics.success_rate * 100).toFixed(1)}%
                      </span>
                    </div>
                    <Progress value={metrics.success_rate * 100} />
                  </div>
                )}
                {metrics.avg_execution_time !== null && metrics.avg_execution_time !== undefined && (
                  <div>
                    <p className="text-sm text-muted-foreground">Avg Execution Time</p>
                    <p className="font-medium">{metrics.avg_execution_time.toFixed(2)}ms</p>
                  </div>
                )}
                {metrics.user_rating !== null && metrics.user_rating !== undefined && (
                  <div>
                    <p className="text-sm text-muted-foreground">User Rating</p>
                    <p className="font-medium">{metrics.user_rating.toFixed(1)}/5.0</p>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>

        {/* Versions */}
        {versions && versions.length > 1 && (
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle>Versions</CardTitle>
              <CardDescription>
                All versions of this prompt
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {versions
                  .sort((a, b) => b.version - a.version)
                  .map((version) => (
                    <div
                      key={version.id}
                      className={`flex items-center justify-between p-4 rounded-lg border ${
                        version.id === prompt.id ? 'border-primary bg-accent' : ''
                      }`}
                    >
                      <div className="flex items-center space-x-4">
                        <div>
                          <div className="flex items-center space-x-2">
                            <span className="font-medium">v{version.version}</span>
                            {version.id === prompt.id && (
                              <Badge variant="default">Current</Badge>
                            )}
                            <Badge variant="outline">{version.status}</Badge>
                          </div>
                          <p className="text-sm text-muted-foreground mt-1">
                            Created {formatDistanceToNow(new Date(version.created_at), { addSuffix: true })}
                          </p>
                        </div>
                      </div>
                      <Link href={`/prompts/${version.id}`}>
                        <Button variant="ghost" size="sm">
                          View
                        </Button>
                      </Link>
                    </div>
                  ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
