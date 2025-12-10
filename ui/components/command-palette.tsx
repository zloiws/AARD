'use client'

import * as React from 'react'
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { useRouter } from 'next/navigation'
import {
  Home,
  FileText,
  Users,
  Settings,
  Plus,
  Search,
  Workflow,
} from 'lucide-react'

interface Command {
  id: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  action: () => void
  group: string
}

export function CommandPalette() {
  const [open, setOpen] = React.useState(false)
  const router = useRouter()

  React.useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setOpen((open) => !open)
      }
    }

    document.addEventListener('keydown', down)
    return () => document.removeEventListener('keydown', down)
  }, [])

  const commands: Command[] = [
    {
      id: 'home',
      label: 'Go to Dashboard',
      icon: Home,
      action: () => router.push('/'),
      group: 'Navigation',
    },
    {
      id: 'tasks',
      label: 'View All Tasks',
      icon: FileText,
      action: () => router.push('/tasks'),
      group: 'Navigation',
    },
    {
      id: 'agents',
      label: 'View Agents',
      icon: Users,
      action: () => router.push('/agents'),
      group: 'Navigation',
    },
    {
      id: 'plans',
      label: 'View Plans',
      icon: Workflow,
      action: () => router.push('/plans'),
      group: 'Navigation',
    },
    {
      id: 'prompts',
      label: 'View Prompts',
      icon: FileText,
      action: () => router.push('/prompts'),
      group: 'Navigation',
    },
    {
      id: 'chat',
      label: 'Open Chat',
      icon: Search,
      action: () => router.push('/chat'),
      group: 'Navigation',
    },
    {
      id: 'servers',
      label: 'View Servers',
      icon: Users,
      action: () => router.push('/servers'),
      group: 'Navigation',
    },
    {
      id: 'new-agent',
      label: 'Create New Agent',
      icon: Plus,
      action: () => router.push('/agents/new'),
      group: 'Create',
    },
    {
      id: 'new-prompt',
      label: 'Create New Prompt',
      icon: Plus,
      action: () => router.push('/prompts/new'),
      group: 'Create',
    },
    {
      id: 'settings',
      label: 'Settings',
      icon: Settings,
      action: () => router.push('/settings'),
      group: 'Navigation',
    },
    {
      id: 'new-task',
      label: 'Create New Task',
      icon: Plus,
      action: () => router.push('/tasks/new'),
      group: 'Actions',
    },
    {
      id: 'search',
      label: 'Search',
      icon: Search,
      action: () => router.push('/search'),
      group: 'Actions',
    },
  ]

  const groupedCommands = commands.reduce((acc, command) => {
    if (!acc[command.group]) {
      acc[command.group] = []
    }
    acc[command.group].push(command)
    return acc
  }, {} as Record<string, Command[]>)

  const handleSelect = (command: Command) => {
    setOpen(false)
    command.action()
  }

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Type a command or search..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        {Object.entries(groupedCommands).map(([group, commands]) => (
          <CommandGroup key={group} heading={group}>
            {commands.map((command) => {
              const Icon = command.icon
              return (
                <CommandItem
                  key={command.id}
                  onSelect={() => handleSelect(command)}
                >
                  <Icon className="mr-2 h-4 w-4" />
                  <span>{command.label}</span>
                </CommandItem>
              )
            })}
          </CommandGroup>
        ))}
      </CommandList>
    </CommandDialog>
  )
}
