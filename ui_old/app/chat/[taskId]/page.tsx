'use client'

import { useState, useRef, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useTask, useServers, useServerModels, useChatSession } from '@/lib/hooks/use-api'
import { useSendMessage } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ArrowLeft, Send, Loader2, Bot, User, Server, Settings, ChevronDown, ChevronUp } from 'lucide-react'
import Link from 'next/link'
import { formatDistanceToNow } from 'date-fns'
import { toast } from 'sonner'
import { SimpleMarkdown } from '@/components/chat/simple-markdown'
import { WorkflowView } from '@/components/chat/workflow-view'

const getStorageKeySession = (taskId: string) => `chat_task_${taskId}_session_id`
const getStorageKeySettings = (taskId: string) => `chat_task_${taskId}_settings`

export default function ChatPage() {
  const params = useParams()
  const router = useRouter()
  const taskId = params.taskId as string
  const { data: task } = useTask(taskId)
  
  // Initialize with empty state to avoid hydration mismatch
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [selectedServerId, setSelectedServerId] = useState<string>('')
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [temperature, setTemperature] = useState<number>(0.7)
  const [systemPrompt, setSystemPrompt] = useState<string>('')
  const [isHydrated, setIsHydrated] = useState(false)
  
  // Load session ID and settings from localStorage after hydration
  useEffect(() => {
    const savedSessionId = localStorage.getItem(getStorageKeySession(taskId))
    if (savedSessionId) {
      setSessionId(savedSessionId)
    }
    
    const saved = localStorage.getItem(getStorageKeySettings(taskId))
    if (saved) {
      try {
        const settings = JSON.parse(saved)
        setSelectedServerId(settings.serverId || '')
        setSelectedModel(settings.model || '')
        setTemperature(settings.temperature ?? 0.7)
        setSystemPrompt(settings.systemPrompt || '')
      } catch {
        // Ignore parse errors
      }
    }
    
    setIsHydrated(true)
  }, [taskId])
  const [showSettings, setShowSettings] = useState(false)
  
  // Server and model selection
  const { data: servers } = useServers(true) // Only active servers
  const { data: models } = useServerModels(selectedServerId)
  
  // Load chat session history
  const { data: sessionData, isLoading: isLoadingHistory } = useChatSession(sessionId)
  
  const [messages, setMessages] = useState<Array<{ id: string; role: 'user' | 'assistant' | 'system'; content: string; created_at: string; model?: string; reasoning?: string; workflow_id?: string }>>([])
  const [message, setMessage] = useState('')
  const [isSending, setIsSending] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  
  // Load messages from session when session data is loaded
  useEffect(() => {
    if (sessionData?.messages) {
      const formattedMessages = sessionData.messages.map((msg) => ({
        id: msg.id,
        role: msg.role as 'user' | 'assistant' | 'system',
        content: msg.content,
        created_at: msg.timestamp,
        model: msg.model || undefined,
        reasoning: (msg.metadata as any)?.reasoning || undefined,
        workflow_id: (msg.metadata as any)?.workflow_id || undefined,
      }))
      setMessages(formattedMessages)
    }
  }, [sessionData])
  
  // Save settings to localStorage when they change
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(getStorageKeySettings(taskId), JSON.stringify({
        serverId: selectedServerId,
        model: selectedModel,
        temperature,
        systemPrompt,
      }))
    }
  }, [taskId, selectedServerId, selectedModel, temperature, systemPrompt])
  
  const sendMessage = useSendMessage()

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!message.trim() || isSending || !isHydrated) return

    const messageText = message.trim()
    setMessage('')
    setIsSending(true)

    try {
      // Add user message to local state immediately
      const userMessage = {
        id: `temp-${Date.now()}`,
        role: 'user' as const,
        content: messageText,
        created_at: new Date().toISOString(),
      }
      setMessages(prev => [...prev, userMessage])

      const result = await sendMessage.mutateAsync({
        taskId,
        content: messageText,
        sessionId: sessionId || undefined,
        model: selectedModel || undefined,
        serverId: selectedServerId || undefined,
        temperature: temperature,
        systemPrompt: systemPrompt || undefined,
      }) as any
      
      // Update session ID if provided and save to localStorage
      if (result.session_id && isHydrated) {
        if (result.session_id !== sessionId) {
          setSessionId(result.session_id)
          localStorage.setItem(getStorageKeySession(taskId), result.session_id)
        }
      }

      // Add assistant response if available
      // API returns ChatResponse with 'response' field
      if (result.response) {
        const assistantMessage = {
          id: `msg-${Date.now()}`,
          role: 'assistant' as const,
          content: result.response,
          created_at: new Date().toISOString(),
          model: result.model,
          reasoning: result.reasoning,
          workflow_id: result.workflow_id,
        }
        setMessages(prev => [...prev, assistantMessage])
        
        // Show notification if workflow was created
        if (result.workflow_id) {
          toast.success('Workflow created', {
            description: `Workflow ID: ${result.workflow_id.slice(0, 8)}...`,
            action: {
              label: 'View',
              onClick: () => window.open(`/workflows/${result.workflow_id}`, '_blank'),
            },
          })
        }
      } else {
        // If no response, show error
        console.warn('No response from API:', result)
        toast.error('No response received from the agent')
        // Remove the user message if there's no response
        setMessages(prev => prev.filter(m => m.id !== userMessage.id))
      }
    } catch (error) {
      console.error('Failed to send message:', error)
      toast.error('Failed to send message. Please try again.')
    } finally {
      setIsSending(false)
      // Focus textarea after sending
      setTimeout(() => {
        textareaRef.current?.focus()
      }, 100)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e as any)
    }
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-[95%]">
      {/* Header */}
      <div className="mb-6">
        <Link href={taskId ? `/tasks/${taskId}` : '/tasks'}>
          <Button variant="ghost" className="mb-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            {taskId ? 'Back to Task' : 'Back to Tasks'}
          </Button>
        </Link>
        <div className="flex items-center space-x-4">
          <div className="h-12 w-12 rounded-full bg-primary flex items-center justify-center">
            <Bot className="h-6 w-6 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              Chat with Agent
            </h1>
            {task && (
              <p className="text-muted-foreground mt-1">
                Task: {task.description || 'Untitled Task'}
              </p>
            )}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowSettings(!showSettings)}
          >
            <Settings className="h-4 w-4 mr-2" />
            {showSettings ? 'Hide' : 'Show'} Settings
            {showSettings ? <ChevronUp className="h-4 w-4 ml-2" /> : <ChevronDown className="h-4 w-4 ml-2" />}
          </Button>
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <Card className="mb-4">
          <CardHeader>
            <CardTitle className="text-lg">Chat Settings</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              {/* Server Selection */}
              <div className="space-y-2">
                <Label htmlFor="server">Server</Label>
                <Select
                  value={selectedServerId}
                  onValueChange={(value) => {
                    setSelectedServerId(value)
                    setSelectedModel('') // Reset model when server changes
                  }}
                >
                  <SelectTrigger id="server">
                    <SelectValue placeholder="Auto-select (default)" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Auto-select (default)</SelectItem>
                    {(servers || []).map((server: any) => (
                      <SelectItem key={server.id} value={server.id}>
                        <div className="flex items-center gap-2">
                          <Server className="h-4 w-4" />
                          {server.name}
                          {server.is_default && (
                            <span className="text-xs text-muted-foreground">(default)</span>
                          )}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Model Selection */}
              <div className="space-y-2">
                <Label htmlFor="model">Model</Label>
                <Select
                  value={selectedModel}
                  onValueChange={setSelectedModel}
                  disabled={!selectedServerId}
                >
                  <SelectTrigger id="model">
                    <SelectValue placeholder={selectedServerId ? "Select model" : "Select server first"} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Auto-select (default)</SelectItem>
                    {(models || [])
                      .filter((model: any) => model.is_active)
                      .map((model: any) => (
                        <SelectItem key={model.id} value={model.model_name}>
                          <div className="flex flex-col">
                            <span>{model.name || model.model_name}</span>
                            {model.capabilities && model.capabilities.length > 0 && (
                              <span className="text-xs text-muted-foreground">
                                {model.capabilities.join(', ')}
                              </span>
                            )}
                          </div>
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
                {!selectedServerId && (
                  <p className="text-xs text-muted-foreground">
                    Select a server first to choose a model
                  </p>
                )}
              </div>

              {/* Temperature */}
              <div className="space-y-2">
                <Label htmlFor="temperature">
                  Temperature: {temperature.toFixed(1)}
                </Label>
                <div className="flex items-center gap-2">
                  <Input
                    id="temperature"
                    type="range"
                    min="0"
                    max="2"
                    step="0.1"
                    value={temperature}
                    onChange={(e) => setTemperature(parseFloat(e.target.value))}
                    className="flex-1"
                  />
                  <Input
                    type="number"
                    min="0"
                    max="2"
                    step="0.1"
                    value={temperature}
                    onChange={(e) => setTemperature(parseFloat(e.target.value) || 0.7)}
                    className="w-20"
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Higher = more creative, Lower = more focused
                </p>
              </div>
            </div>
            
            {/* System Prompt */}
            <div className="mt-4 space-y-2">
              <Label htmlFor="system-prompt">System Prompt</Label>
              <Textarea
                id="system-prompt"
                placeholder="Enter system prompt to provide context to the model (e.g., 'You are a helpful assistant specialized in Python programming')"
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                rows={4}
                className="font-mono text-sm"
              />
              <p className="text-xs text-muted-foreground">
                This prompt will be sent to the model to provide context and instructions for all messages in this chat.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Chat Messages */}
      <Card className="mb-4" style={{ height: 'calc(100vh - 300px)', minHeight: '400px' }}>
        <CardContent className="p-0 h-full flex flex-col">
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {isLoadingHistory ? (
              <div className="flex items-center justify-center h-full">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : !messages || messages.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <Bot className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                  <p className="text-muted-foreground">
                    No messages yet. Start a conversation!
                  </p>
                </div>
              </div>
            ) : (
              <>
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex gap-3 ${
                      msg.role === 'user' ? 'justify-end' : 'justify-start'
                    }`}
                  >
                    {msg.role === 'assistant' && (
                      <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                        <Bot className="h-4 w-4 text-primary-foreground" />
                      </div>
                    )}
                    <div
                      className={`max-w-[85%] rounded-lg px-4 py-2 ${
                        msg.role === 'user'
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted'
                      }`}
                    >
                      {msg.role === 'assistant' && msg.reasoning && (
                        <details className="mb-3">
                          <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground mb-2">
                            💭 Размышления модели
                          </summary>
                          <div className="bg-muted/50 rounded p-2 text-xs text-muted-foreground break-words border-l-2 border-primary/30 pl-2">
                            <SimpleMarkdown content={msg.reasoning} />
                          </div>
                        </details>
                      )}
                      <SimpleMarkdown content={msg.content} />
                      
                      {/* Workflow View */}
                      {msg.role === 'assistant' && msg.workflow_id && (
                        <div className="mt-3">
                          <WorkflowView workflowId={msg.workflow_id} compact={true} />
                        </div>
                      )}
                      
                      <div className="flex items-center justify-between mt-1">
                        <p
                          className={`text-xs ${
                            msg.role === 'user'
                              ? 'text-primary-foreground/70'
                              : 'text-muted-foreground'
                          }`}
                        >
                          {formatDistanceToNow(new Date(msg.created_at), {
                            addSuffix: true,
                          })}
                        </p>
                        {msg.role === 'assistant' && msg.model && (
                          <p className="text-xs text-muted-foreground">
                            Model: {msg.model}
                          </p>
                        )}
                      </div>
                    </div>
                    {msg.role === 'user' && (
                      <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center flex-shrink-0">
                        <User className="h-4 w-4 text-muted-foreground" />
                      </div>
                    )}
                  </div>
                ))}
                {isSending && (
                  <div className="flex gap-3 justify-start">
                    <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                      <Bot className="h-4 w-4 text-primary-foreground" />
                    </div>
                    <div className="bg-muted rounded-lg px-4 py-2 flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                      <span className="text-xs text-muted-foreground">Processing... Workflow may be created</span>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* Message Input */}
          <div className="border-t p-4">
            <form onSubmit={handleSubmit} className="flex gap-2">
              <Textarea
                ref={textareaRef}
                placeholder="Type your message... (Enter to send, Shift+Enter for new line)"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={2}
                className="resize-none flex-1"
                disabled={isSending}
              />
              <Button
                type="submit"
                disabled={!message.trim() || isSending}
                size="icon"
                className="h-auto"
              >
                {isSending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </form>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
