'use client'

import { useState, useRef, useEffect, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Send, Loader2, Bot, User, Server, Settings, ChevronDown, ChevronUp } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { toast } from 'sonner'
import Link from 'next/link'
import { useSendMessage, useServers, useServerModels, useChatSession } from '@/lib/hooks/use-api'
import { api } from '@/lib/api/client'
import { SimpleMarkdown } from '@/components/chat/simple-markdown'
import { WorkflowView } from '@/components/chat/workflow-view'
import { ChatTabs, type ChatTab } from '@/components/chat/chat-tabs'
import { Trash2, X } from 'lucide-react'

const STORAGE_KEY_TABS = 'chat_tabs'
const STORAGE_KEY_ACTIVE_TAB = 'chat_active_tab_id'

export default function ChatPage() {
  const router = useRouter()
  const sendMessage = useSendMessage()
  
  // Initialize with empty state to avoid hydration mismatch
  const [tabs, setTabs] = useState<ChatTab[]>([])
  const [activeTabId, setActiveTabId] = useState<string>('')
  const [isHydrated, setIsHydrated] = useState(false)
  
  // Load tabs from localStorage after hydration
  useEffect(() => {
    const loadTabs = (): ChatTab[] => {
      const saved = localStorage.getItem(STORAGE_KEY_TABS)
      if (saved) {
        try {
          return JSON.parse(saved)
        } catch {
          return []
        }
      }
      return []
    }
    
    const loadedTabs = loadTabs()
    if (loadedTabs.length === 0) {
      // Create default tab
      const defaultTab: ChatTab = {
        id: `tab-${Date.now()}`,
        title: 'New Chat',
        sessionId: null,
        settings: {
          serverId: '',
          model: '',
          temperature: 0.7,
          systemPrompt: '',
        }
      }
      setTabs([defaultTab])
      setActiveTabId(defaultTab.id)
    } else {
      setTabs(loadedTabs)
      const savedActiveTabId = localStorage.getItem(STORAGE_KEY_ACTIVE_TAB)
      if (savedActiveTabId && loadedTabs.some(t => t.id === savedActiveTabId)) {
        setActiveTabId(savedActiveTabId)
      } else {
        setActiveTabId(loadedTabs[0]?.id || '')
      }
    }
    setIsHydrated(true)
  }, [])
  
  // Memoize activeTab to prevent unnecessary re-renders
  const activeTab = useMemo(() => {
    if (!isHydrated || !activeTabId || tabs.length === 0) return null
    return tabs.find(t => t.id === activeTabId) || tabs[0] || null
  }, [isHydrated, activeTabId, tabs])
  
  const sessionId = activeTab?.sessionId || null
  
  // Use active tab settings
  const [selectedServerId, setSelectedServerId] = useState<string>('')
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [temperature, setTemperature] = useState<number>(0.7)
  const [systemPrompt, setSystemPrompt] = useState<string>('')
  const [showSettings, setShowSettings] = useState(false)
  
  // Update settings when active tab changes (only after hydration)
  useEffect(() => {
    if (isHydrated && activeTab) {
      const settings = activeTab.settings || {}
      setSelectedServerId(settings.serverId || '')
      setSelectedModel(settings.model || '')
      setTemperature(settings.temperature ?? 0.7)
      setSystemPrompt(settings.systemPrompt || '')
    }
  }, [activeTabId, isHydrated]) // Removed activeTab from dependencies, use activeTabId instead
  
  // Server and model selection
  const { data: servers } = useServers(true) // Only active servers
  const { data: models } = useServerModels(selectedServerId)
  
  // Load chat session history for active tab (only after hydration)
  const { data: sessionData, isLoading: isLoadingHistory } = useChatSession(
    isHydrated && activeTab?.sessionId ? activeTab.sessionId : null
  )
  
  const [messages, setMessages] = useState<Array<{ id: string; role: 'user' | 'assistant' | 'system'; content: string; created_at: string; model?: string; reasoning?: string; workflow_id?: string }>>([])
  const [message, setMessage] = useState('')
  const [isSending, setIsSending] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  
  // Load messages from session when session data is loaded or tab changes (only after hydration)
  useEffect(() => {
    if (!isHydrated) return
    
    const currentSessionId = activeTab?.sessionId
    if (sessionData?.messages && currentSessionId === sessionData.session_id) {
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
    } else if (!currentSessionId) {
      // Clear messages if no session
      setMessages([])
    }
  }, [sessionData, activeTabId, isHydrated]) // Removed activeTab, use activeTabId instead
  
  // Save tab settings when they change (only after hydration)
  useEffect(() => {
    if (!isHydrated || !activeTabId) return
    
    setTabs(prevTabs => {
      const updatedTabs = prevTabs.map(tab => 
        tab.id === activeTabId 
          ? { ...tab, settings: { serverId: selectedServerId, model: selectedModel, temperature, systemPrompt } }
          : tab
      )
      localStorage.setItem(STORAGE_KEY_TABS, JSON.stringify(updatedTabs))
      localStorage.setItem(STORAGE_KEY_ACTIVE_TAB, activeTabId)
      return updatedTabs
    })
  }, [selectedServerId, selectedModel, temperature, systemPrompt, activeTabId, isHydrated])
  
  // Save tabs when they change (only after hydration)
  useEffect(() => {
    if (isHydrated && tabs.length > 0) {
      localStorage.setItem(STORAGE_KEY_TABS, JSON.stringify(tabs))
      if (activeTabId) {
        localStorage.setItem(STORAGE_KEY_ACTIVE_TAB, activeTabId)
      }
    }
  }, [tabs, activeTabId, isHydrated])

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

      // Use a dummy task ID for general chat
      const result = await sendMessage.mutateAsync({
        taskId: 'general',
        content: messageText,
        sessionId: (isHydrated && activeTab?.sessionId) || undefined,
        model: selectedModel || undefined,
        serverId: selectedServerId || undefined,
        temperature: temperature,
        systemPrompt: systemPrompt || undefined,
      }) as any
      
      // Update session ID if provided and update active tab
      if (result.session_id && isHydrated && activeTabId) {
        if (result.session_id !== sessionId) {
          setTabs(prevTabs => prevTabs.map(tab =>
            tab.id === activeTabId
              ? { ...tab, sessionId: result.session_id }
              : tab
          ))
        }
      }

      // Add assistant response if available
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
        console.warn('No response from API:', result)
        toast.error('No response received from the agent')
        setMessages(prev => prev.filter(m => m.id !== userMessage.id))
      }
    } catch (error: any) {
      console.error('Failed to send message:', error)
      
      // Show more informative error message
      let errorMessage = 'Failed to send message. Please try again.'
      
      if (error?.message) {
        errorMessage = error.message
      } else if (error?.data?.message) {
        errorMessage = error.data.message
      } else if (error?.data?.detail) {
        // FastAPI error format
        if (typeof error.data.detail === 'string') {
          errorMessage = error.data.detail
        } else {
          errorMessage = JSON.stringify(error.data.detail)
        }
      }
      
      // Make error messages more user-friendly
      if (errorMessage.includes('has no attribute')) {
        errorMessage = 'Backend error: ' + errorMessage + '. Please contact support.'
      } else if (errorMessage.includes('Network error') || errorMessage.includes('Unable to connect')) {
        errorMessage = 'Cannot connect to the server. Please check if the backend is running.'
      } else if (errorMessage.includes('Failed to fetch')) {
        errorMessage = 'Network error. Please check your connection and server status.'
      }
      
      toast.error(errorMessage)
      // Remove user message on error
      setMessages(prev => prev.filter(m => !m.id.startsWith('temp-')))
    } finally {
      setIsSending(false)
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
  
  // Tab management functions
  const handleNewTab = () => {
    const newTab: ChatTab = {
      id: `tab-${Date.now()}`,
      title: 'New Chat',
      sessionId: null,
      settings: {
        serverId: '',
        model: '',
        temperature: 0.7,
        systemPrompt: '',
      }
    }
    setTabs(prevTabs => [...prevTabs, newTab])
    setActiveTabId(newTab.id)
  }
  
  const handleTabChange = (tabId: string) => {
    setActiveTabId(tabId)
  }
  
  const handleTabClose = async (tabId: string) => {
    setTabs(prevTabs => {
      if (prevTabs.length === 1) {
        // Don't close the last tab, just reset it
        const resetTab: ChatTab = {
          id: tabId,
          title: 'New Chat',
          sessionId: null,
          settings: prevTabs[0].settings
        }
        setActiveTabId(tabId)
        setMessages([])
        return [resetTab]
      }
      
      const tabToClose = prevTabs.find(t => t.id === tabId)
      if (tabToClose?.sessionId) {
        // Delete session from backend (fire and forget)
        api.chat.deleteSession(tabToClose.sessionId).catch(error => {
          // Silently fail - session deletion is not critical
          // Only log in dev mode
          if (process.env.NODE_ENV === 'development') {
            console.warn('Failed to delete session:', error)
          }
        })
      }
      
      const updatedTabs = prevTabs.filter(t => t.id !== tabId)
      
      // Switch to another tab if closing active one
      if (activeTabId === tabId) {
        const newActiveTab = updatedTabs[0]
        if (newActiveTab) {
          setActiveTabId(newActiveTab.id)
        }
      }
      
      return updatedTabs
    })
  }
  
  const handleDeleteChat = async () => {
    if (!activeTab?.sessionId || !activeTabId) return
    
    try {
      await api.chat.deleteSession(activeTab.sessionId)
      toast.success('Chat deleted')
      
      // Reset tab
      setTabs(prevTabs => prevTabs.map(tab => 
        tab.id === activeTabId 
          ? { ...tab, sessionId: null, title: 'New Chat' }
          : tab
      ))
      setMessages([])
    } catch (error: any) {
      console.error('Failed to delete chat:', error)
      toast.error(`Failed to delete chat: ${error.message || 'Unknown error'}`)
    }
  }
  
  const handleDeleteMessage = (messageId: string) => {
    setMessages(prev => prev.filter(m => m.id !== messageId))
    // Note: Backend doesn't support deleting individual messages yet
    // This only removes from UI
    toast.info('Message removed from view (not deleted from server)')
  }
  
  // Update tab title when first message is sent (only after hydration)
  useEffect(() => {
    if (!isHydrated || !activeTabId) return
    
    if (messages.length > 0) {
      const firstUserMessage = messages.find(m => m.role === 'user')
      if (firstUserMessage) {
        setTabs(prevTabs => {
          const currentTab = prevTabs.find(t => t.id === activeTabId)
          if (currentTab && (!currentTab.title || currentTab.title === 'New Chat')) {
            const newTitle = firstUserMessage.content.slice(0, 50)
            return prevTabs.map(tab =>
              tab.id === activeTabId
                ? { ...tab, title: newTitle }
                : tab
            )
          }
          return prevTabs
        })
      }
    }
  }, [messages.length, activeTabId, isHydrated])

  return (
    <div className="container mx-auto px-4 py-8 max-w-[95%]">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="h-12 w-12 rounded-full bg-primary flex items-center justify-center">
              <Bot className="h-6 w-6 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">
                Chat with AI Agent
              </h1>
              <p className="text-muted-foreground mt-1">
                General conversation with AI agents
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isHydrated && activeTab?.sessionId && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleDeleteChat}
                title="Delete chat"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete Chat
              </Button>
            )}
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
      </div>
      
      {/* Chat Tabs */}
      {isHydrated && (
        <ChatTabs
          tabs={tabs}
          activeTabId={activeTabId}
          onTabChange={handleTabChange}
          onTabClose={handleTabClose}
          onNewTab={handleNewTab}
        />
      )}

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
                <div className="text-center">
                  <Loader2 className="h-12 w-12 mx-auto mb-4 text-muted-foreground animate-spin" />
                  <p className="text-muted-foreground">
                    Loading chat history...
                  </p>
                </div>
              </div>
            ) : messages.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <Bot className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                  <p className="text-muted-foreground">
                    Start a conversation with the AI agent!
                  </p>
                  <p className="text-sm text-muted-foreground mt-2">
                    You can ask questions, request help, or discuss tasks.
                  </p>
                </div>
              </div>
            ) : (
              <>
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex gap-3 group ${
                      msg.role === 'user' ? 'justify-end' : 'justify-start'
                    }`}
                  >
                    {msg.role === 'assistant' && (
                      <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                        <Bot className="h-4 w-4 text-primary-foreground" />
                      </div>
                    )}
                    <div className="relative">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="absolute -top-2 -right-2 opacity-0 group-hover:opacity-100 h-6 w-6 p-0 z-10"
                        onClick={() => handleDeleteMessage(msg.id)}
                        title="Delete message"
                      >
                        <X className="h-3 w-3" />
                      </Button>
                      <div
                        className={`max-w-[85%] rounded-lg px-4 py-2 ${
                          msg.role === 'user'
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-muted'
                        }`}
                      >
                      {/* Message content */}
                      <SimpleMarkdown content={msg.content} />
                      
                      {/* Reasoning - collapsed by default */}
                      {msg.role === 'assistant' && msg.reasoning && (
                        <details className="mt-2">
                          <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground">
                            💭 Размышления модели
                          </summary>
                          <div className="bg-muted/50 rounded p-2 text-xs text-muted-foreground break-words border-l-2 border-primary/30 pl-2 mt-1">
                            <SimpleMarkdown content={msg.reasoning} />
                          </div>
                        </details>
                      )}
                      
                      {/* Workflow View - simplified */}
                      {msg.role === 'assistant' && msg.workflow_id && (
                        <div className="mt-2 pt-2 border-t">
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
