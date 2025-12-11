'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { X, Plus, MessageSquare } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface ChatTab {
  id: string
  title: string
  sessionId: string | null
  settings: {
    serverId?: string
    model?: string
    temperature?: number
    systemPrompt?: string
  }
}

interface ChatTabsProps {
  tabs: ChatTab[]
  activeTabId: string
  onTabChange: (tabId: string) => void
  onTabClose: (tabId: string) => void
  onNewTab: () => void
}

export function ChatTabs({ tabs, activeTabId, onTabChange, onTabClose, onNewTab }: ChatTabsProps) {
  return (
    <div className="flex items-center gap-1 border-b overflow-x-auto">
      {tabs.map((tab) => (
        <div
          key={tab.id}
          className={cn(
            "flex items-center gap-2 px-3 py-2 border-b-2 transition-colors cursor-pointer min-w-0",
            activeTabId === tab.id
              ? "border-primary bg-primary/5"
              : "border-transparent hover:bg-muted/50"
          )}
          onClick={() => onTabChange(tab.id)}
        >
          <MessageSquare className="h-4 w-4 flex-shrink-0" />
          <span className="text-sm font-medium truncate max-w-[150px]">
            {tab.title}
          </span>
          {tabs.length > 1 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-5 w-5 p-0 hover:bg-destructive hover:text-destructive-foreground"
              onClick={(e) => {
                e.stopPropagation()
                onTabClose(tab.id)
              }}
            >
              <X className="h-3 w-3" />
            </Button>
          )}
        </div>
      ))}
      <Button
        variant="ghost"
        size="sm"
        className="h-8 px-3 flex-shrink-0"
        onClick={onNewTab}
      >
        <Plus className="h-4 w-4 mr-1" />
        New
      </Button>
    </div>
  )
}
