'use client'

import { useState } from 'react'
import { useCreatePrompt } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { ArrowLeft, Loader2 } from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

const PROMPT_TYPES = [
  { value: 'system', label: 'System' },
  { value: 'agent', label: 'Agent' },
  { value: 'tool', label: 'Tool' },
  { value: 'meta', label: 'Meta' },
  { value: 'context', label: 'Context' },
]

export default function NewPromptPage() {
  const router = useRouter()
  const createPrompt = useCreatePrompt()
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  // Form state
  const [name, setName] = useState('')
  const [promptText, setPromptText] = useState('')
  const [promptType, setPromptType] = useState('system')
  const [level, setLevel] = useState(0)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || !promptText.trim()) return

    setIsSubmitting(true)
    try {
      const result = await createPrompt.mutateAsync({
        name: name.trim(),
        prompt_text: promptText.trim(),
        prompt_type: promptType,
        level: level || 0,
      })
      router.push(`/prompts/${result.id}`)
    } catch (error) {
      console.error('Failed to create prompt:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-3xl">
      <div className="mb-6">
        <Link href="/prompts">
          <Button variant="ghost" className="mb-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Prompts
          </Button>
        </Link>
        <h1 className="text-3xl font-bold tracking-tight">Create New Prompt</h1>
        <p className="text-muted-foreground mt-2">
          Create a new AI prompt with custom configuration
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Prompt Information</CardTitle>
            <CardDescription>
              Define the prompt name, type, and content
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="name">Prompt Name *</Label>
              <Input
                id="name"
                placeholder="e.g., Code Review System Prompt"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="mt-1"
              />
              <p className="text-xs text-muted-foreground mt-1">
                A descriptive name for this prompt
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="promptType">Prompt Type *</Label>
                <select
                  id="promptType"
                  value={promptType}
                  onChange={(e) => setPromptType(e.target.value)}
                  className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  required
                >
                  {PROMPT_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <Label htmlFor="level">Level (0-4)</Label>
                <Input
                  id="level"
                  type="number"
                  min="0"
                  max="4"
                  value={level}
                  onChange={(e) => setLevel(parseInt(e.target.value) || 0)}
                  className="mt-1"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Prompt complexity level
                </p>
              </div>
            </div>

            <div>
              <Label htmlFor="promptText">Prompt Text *</Label>
              <Textarea
                id="promptText"
                placeholder="Enter your prompt text here..."
                value={promptText}
                onChange={(e) => setPromptText(e.target.value)}
                rows={12}
                className="mt-1 resize-none font-mono text-sm"
                required
              />
              <p className="text-xs text-muted-foreground mt-1">
                The actual prompt text that will be used by the AI
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex justify-end space-x-2">
          <Link href="/prompts">
            <Button type="button" variant="outline">
              Cancel
            </Button>
          </Link>
          <Button type="submit" disabled={!name.trim() || !promptText.trim() || isSubmitting}>
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Creating...
              </>
            ) : (
              'Create Prompt'
            )}
          </Button>
        </div>
      </form>
    </div>
  )
}
