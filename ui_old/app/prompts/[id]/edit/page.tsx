'use client'

import { useState, useEffect } from 'react'
import { usePrompt, useUpdatePrompt } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { ArrowLeft, Loader2 } from 'lucide-react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'

const PROMPT_TYPES = [
  { value: 'system', label: 'System' },
  { value: 'agent', label: 'Agent' },
  { value: 'tool', label: 'Tool' },
  { value: 'meta', label: 'Meta' },
  { value: 'context', label: 'Context' },
]

export default function EditPromptPage() {
  const params = useParams()
  const router = useRouter()
  const promptId = params.id as string
  const { data: prompt, isLoading } = usePrompt(promptId)
  const updatePrompt = useUpdatePrompt()
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  // Form state
  const [name, setName] = useState('')
  const [promptText, setPromptText] = useState('')

  // Load prompt data
  useEffect(() => {
    if (prompt) {
      setName(prompt.name)
      setPromptText(prompt.prompt_text)
    }
  }, [prompt])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || !promptText.trim() || !prompt) return

    setIsSubmitting(true)
    try {
      await updatePrompt.mutateAsync({
        id: promptId,
        data: {
          name: name.trim(),
          prompt_text: promptText.trim(),
        },
      })
      router.push(`/prompts/${promptId}`)
    } catch (error) {
      console.error('Failed to update prompt:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

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

  return (
    <div className="container mx-auto px-4 py-8 max-w-3xl">
      <div className="mb-6">
        <Link href={`/prompts/${promptId}`}>
          <Button variant="ghost" className="mb-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Prompt
          </Button>
        </Link>
        <h1 className="text-3xl font-bold tracking-tight">Edit Prompt: {prompt.name}</h1>
        <p className="text-muted-foreground mt-2">
          Update prompt name and text
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Prompt Information</CardTitle>
            <CardDescription>
              Update the prompt name and text. Type and level cannot be changed.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="name">Prompt Name *</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="mt-1"
              />
            </div>

            <div>
              <Label>Prompt Type</Label>
              <Input
                value={PROMPT_TYPES.find(t => t.value === prompt.prompt_type)?.label || prompt.prompt_type}
                disabled
                className="mt-1"
              />
            </div>

            <div>
              <Label>Level</Label>
              <Input
                value={prompt.level}
                disabled
                className="mt-1"
              />
            </div>

            <div>
              <Label htmlFor="promptText">Prompt Text *</Label>
              <Textarea
                id="promptText"
                value={promptText}
                onChange={(e) => setPromptText(e.target.value)}
                rows={12}
                className="mt-1 resize-none font-mono text-sm"
                required
              />
            </div>
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex justify-end space-x-2">
          <Link href={`/prompts/${promptId}`}>
            <Button type="button" variant="outline">
              Cancel
            </Button>
          </Link>
          <Button type="submit" disabled={!name.trim() || !promptText.trim() || isSubmitting}>
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              'Save Changes'
            )}
          </Button>
        </div>
      </form>
    </div>
  )
}
