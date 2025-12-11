'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useCreateArtifact } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ArrowLeft, Loader2, Sparkles } from 'lucide-react'
import Link from 'next/link'
import { toast } from 'sonner'

export default function NewArtifactPage() {
  const router = useRouter()
  const createArtifact = useCreateArtifact()

  const [description, setDescription] = useState('')
  const [artifactType, setArtifactType] = useState<'agent' | 'tool'>('agent')
  const [context, setContext] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!description.trim()) {
      toast.error('Please provide a description')
      return
    }

    setIsSubmitting(true)
    try {
      let contextData = {}
      if (context.trim()) {
        try {
          contextData = JSON.parse(context)
        } catch {
          toast.error('Invalid JSON in context field')
          setIsSubmitting(false)
          return
        }
      }

      const result = await createArtifact.mutateAsync({
        description: description.trim(),
        artifact_type: artifactType,
        context: contextData,
      })

      toast.success('Artifact created successfully!')
      router.push(`/artifacts/${result.id}`)
    } catch (error: any) {
      console.error('Failed to create artifact:', error)
      toast.error(`Failed to create artifact: ${error?.message || 'Unknown error'}`)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-3xl">
      <div className="mb-6">
        <Link href="/artifacts">
          <Button variant="ghost" className="mb-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Artifacts
          </Button>
        </Link>
        <h1 className="text-3xl font-bold tracking-tight">Create New Artifact</h1>
        <p className="text-muted-foreground mt-2">
          Generate a new agent or tool artifact using AI
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Artifact Details</CardTitle>
          <CardDescription>
            Describe what you want the artifact to do. The AI will generate the code or prompt.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Artifact Type */}
            <div className="space-y-2">
              <Label htmlFor="artifact_type">Artifact Type</Label>
              <Select
                value={artifactType}
                onValueChange={(value) => setArtifactType(value as 'agent' | 'tool')}
              >
                <SelectTrigger id="artifact_type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="agent">
                    <div className="flex items-center gap-2">
                      <Sparkles className="h-4 w-4" />
                      Agent - AI-powered agent with prompt
                    </div>
                  </SelectItem>
                  <SelectItem value="tool">
                    <div className="flex items-center gap-2">
                      <Sparkles className="h-4 w-4" />
                      Tool - Executable code/function
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {artifactType === 'agent'
                  ? 'An agent uses a prompt to interact with LLM and perform tasks'
                  : 'A tool is executable code that performs specific operations'}
              </p>
            </div>

            {/* Description */}
            <div className="space-y-2">
              <Label htmlFor="description">
                Description <span className="text-destructive">*</span>
              </Label>
              <Textarea
                id="description"
                placeholder="Describe what the artifact should do. For example: 'A code review agent that analyzes Python code for bugs and suggests improvements' or 'A tool that validates JSON schemas'"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={6}
                required
                className="font-mono text-sm"
              />
              <p className="text-xs text-muted-foreground">
                Be specific about the artifact's purpose, capabilities, and requirements.
              </p>
            </div>

            {/* Context (Optional) */}
            <div className="space-y-2">
              <Label htmlFor="context">Additional Context (Optional JSON)</Label>
              <Textarea
                id="context"
                placeholder='{"language": "python", "framework": "fastapi", "requirements": ["validation", "error_handling"]}'
                value={context}
                onChange={(e) => setContext(e.target.value)}
                rows={4}
                className="font-mono text-sm"
              />
              <p className="text-xs text-muted-foreground">
                Provide additional context as JSON. This helps the AI generate more accurate artifacts.
              </p>
            </div>

            {/* Submit Button */}
            <div className="flex justify-end gap-4">
              <Link href="/artifacts">
                <Button type="button" variant="outline" disabled={isSubmitting}>
                  Cancel
                </Button>
              </Link>
              <Button type="submit" disabled={isSubmitting || !description.trim()}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4 mr-2" />
                    Create Artifact
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Info Card */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-lg">How it works</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            • The AI will analyze your description and generate the appropriate code (for tools) or prompt (for agents)
          </p>
          <p>
            • Generated artifacts start in "draft" status and require approval before use
          </p>
          <p>
            • You can review and edit the generated artifact before activating it
          </p>
          <p>
            • Artifacts can have dependencies on other artifacts
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
