'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Button } from '@/components/ui/button'
import {
  LayoutDashboard,
  FileText,
  Users,
  Settings,
  Workflow,
  Search,
  Menu,
  X,
  Sparkles,
  MessageSquare,
  Server,
  BarChart3,
  TestTube,
  Activity,
  Package,
  CheckCircle2,
} from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/lib/utils'

// Grouped navigation items for better organization
const navGroups = [
  {
    label: 'Core',
    items: [
      { href: '/', label: 'Dashboard', icon: LayoutDashboard },
      { href: '/tasks', label: 'Tasks', icon: FileText },
      { href: '/agents', label: 'Agents', icon: Users },
      { href: '/plans', label: 'Plans', icon: Workflow },
    ]
  },
  {
    label: 'Configuration',
    items: [
      { href: '/prompts', label: 'Prompts', icon: Sparkles },
      { href: '/servers', label: 'Servers', icon: Server },
      { href: '/settings', label: 'Settings', icon: Settings },
    ]
  },
  {
    label: 'Testing',
    items: [
      { href: '/benchmarks', label: 'Benchmarks', icon: BarChart3 },
      { href: '/agent-gym', label: 'Agent Gym', icon: TestTube },
    ]
  },
  {
    label: 'Monitoring',
    items: [
      { href: '/traces', label: 'Traces', icon: Activity },
      { href: '/artifacts', label: 'Artifacts', icon: Package },
      { href: '/approvals', label: 'Approvals', icon: CheckCircle2 },
    ]
  },
  {
    label: 'Tools',
    items: [
      { href: '/chat', label: 'Chat', icon: MessageSquare },
    ]
  }
]

// Flatten for mobile menu
const navItems = navGroups.flatMap(group => group.items)

export function Navbar() {
  const pathname = usePathname()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <nav className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <div className="flex items-center space-x-4">
            <Link href="/" className="flex items-center space-x-2">
              <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
                <span className="text-primary-foreground font-bold text-sm">A</span>
              </div>
              <div className="hidden sm:block">
                <span className="text-xl font-bold">AARD</span>
                <span className="text-xs text-muted-foreground block">AI Agent Research Dashboard</span>
              </div>
            </Link>
          </div>

          {/* Desktop Navigation - Grouped */}
          <div className="hidden lg:flex items-center space-x-2">
            {navGroups.map((group, groupIdx) => (
              <div key={group.label} className="flex items-center space-x-1">
                {group.items.map((item) => {
                  const Icon = item.icon
                  const isActive = pathname === item.href || 
                    (item.href !== '/' && pathname?.startsWith(item.href))
                  
                  return (
                    <Link key={item.href} href={item.href}>
                      <Button
                        variant={isActive ? 'secondary' : 'ghost'}
                        size="sm"
                        className={cn(
                          'flex items-center space-x-2',
                          isActive && 'bg-accent'
                        )}
                        title={item.label}
                      >
                        <Icon className="h-4 w-4" />
                        <span className="hidden xl:inline">{item.label}</span>
                      </Button>
                    </Link>
                  )
                })}
                {groupIdx < navGroups.length - 1 && (
                  <div className="h-6 w-px bg-border mx-1" />
                )}
              </div>
            ))}
          </div>

          {/* Desktop Navigation - Compact (lg only) */}
          <div className="hidden md:flex lg:hidden items-center space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon
              const isActive = pathname === item.href || 
                (item.href !== '/' && pathname?.startsWith(item.href))
              
              return (
                <Link key={item.href} href={item.href}>
                  <Button
                    variant={isActive ? 'secondary' : 'ghost'}
                    size="sm"
                    className={cn(
                      'flex items-center space-x-2',
                      isActive && 'bg-accent'
                    )}
                    title={item.label}
                  >
                    <Icon className="h-4 w-4" />
                  </Button>
                </Link>
              )
            })}
          </div>

          {/* Right side actions */}
          <div className="flex items-center space-x-2">
            <Button variant="ghost" size="icon" asChild>
              <Link href="/search">
                <Search className="h-4 w-4" />
              </Link>
            </Button>
            
            {/* Mobile menu button */}
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? (
                <X className="h-4 w-4" />
              ) : (
                <Menu className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t py-2">
            {navItems.map((item) => {
              const Icon = item.icon
              const isActive = pathname === item.href || 
                (item.href !== '/' && pathname?.startsWith(item.href))
              
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                >
                  <div
                    className={cn(
                      'flex items-center space-x-2 px-4 py-2 rounded-md transition-colors',
                      isActive
                        ? 'bg-accent text-accent-foreground'
                        : 'hover:bg-accent/50'
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    <span>{item.label}</span>
                  </div>
                </Link>
              )
            })}
          </div>
        )}
      </div>
    </nav>
  )
}
