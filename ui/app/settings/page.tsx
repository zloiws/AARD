'use client'

import { useState, useEffect } from 'react'
import { useFeatureFlags, useSetFeatureFlag, useLogLevels, useSetLogLevel, useAllModules, useSettings } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Settings as SettingsIcon, Save, Server, Database, Flag, FileText, Search } from 'lucide-react'
import { toast } from 'sonner'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Checkbox } from '@/components/ui/checkbox'

const LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('api')
  const [apiUrl, setApiUrl] = useState(
    typeof window !== 'undefined' ? process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000' : 'http://localhost:8000'
  )
  const [wsUrl, setWsUrl] = useState(
    typeof window !== 'undefined' ? process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/api/ws/events' : 'ws://localhost:8000/api/ws/events'
  )

  // Feature Flags
  const { data: featureFlags, isLoading: flagsLoading } = useFeatureFlags()
  const setFeatureFlag = useSetFeatureFlag()
  const [pendingFeatureFlags, setPendingFeatureFlags] = useState<Record<string, boolean>>({})

  // Logging Levels
  const { data: logLevels, isLoading: levelsLoading } = useLogLevels()
  const setLogLevel = useSetLogLevel()
  const { data: modules } = useAllModules()
  const [pendingLogLevels, setPendingLogLevels] = useState<Record<string, string>>({})
  const [moduleSearch, setModuleSearch] = useState('')

  // System Settings
  const { data: allSettings } = useSettings()
  const [pendingSystemSettings, setPendingSystemSettings] = useState<Record<string, any>>({})

  // Initialize pending changes
  useEffect(() => {
    if (featureFlags) {
      setPendingFeatureFlags({ ...featureFlags })
    }
  }, [featureFlags])

  useEffect(() => {
    if (logLevels) {
      setPendingLogLevels({ ...logLevels })
    }
  }, [logLevels])

  const handleFeatureFlagChange = (feature: string, enabled: boolean) => {
    setPendingFeatureFlags({ ...pendingFeatureFlags, [feature]: enabled })
  }

  const handleLogLevelChange = (module: string, level: string) => {
    setPendingLogLevels({ ...pendingLogLevels, [module]: level })
  }

  const handleApplyFeatureFlags = async () => {
    const changes = Object.entries(pendingFeatureFlags).filter(
      ([key, value]) => featureFlags?.[key] !== value
    )

    for (const [feature, enabled] of changes) {
      try {
        await setFeatureFlag.mutateAsync({
          feature,
          enabled,
        })
      } catch (error) {
        console.error(`Failed to update feature ${feature}:`, error)
      }
    }
  }

  const handleApplyLogLevels = async () => {
    const changes = Object.entries(pendingLogLevels).filter(
      ([key, value]) => logLevels?.[key] !== value
    )

    for (const [module, level] of changes) {
      try {
        await setLogLevel.mutateAsync({
          module: module === '_global' ? undefined : module,
          level,
        })
      } catch (error) {
        console.error(`Failed to update log level for ${module}:`, error)
      }
    }
  }

  const hasFeatureFlagChanges = Object.keys(pendingFeatureFlags).some(
    key => featureFlags?.[key] !== pendingFeatureFlags[key]
  )
  const hasLogLevelChanges = Object.keys(pendingLogLevels).some(
    key => logLevels?.[key] !== pendingLogLevels[key]
  )

  const filteredModules = modules?.filter(m => 
    !moduleSearch || m.toLowerCase().includes(moduleSearch.toLowerCase())
  ) || []

  const globalLogLevel = pendingLogLevels._global || logLevels?._global || 'INFO'

  const handleSave = () => {
    // In a real app, this would save to localStorage or backend
    toast.success('Settings saved (Note: Changes require page reload)')
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-2">
          Configure application settings and preferences
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="api">API Config</TabsTrigger>
          <TabsTrigger value="features">Feature Flags</TabsTrigger>
          <TabsTrigger value="logging">Logging</TabsTrigger>
          <TabsTrigger value="system">System</TabsTrigger>
        </TabsList>

        {/* API Configuration */}
        <TabsContent value="api" className="mt-6">
          <Card>
            <CardHeader>
              <div className="flex items-center space-x-2">
                <Server className="h-5 w-5" />
                <CardTitle>API Configuration</CardTitle>
              </div>
              <CardDescription>
                Configure backend API endpoints
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="api-url">API URL</Label>
                <Input
                  id="api-url"
                  value={apiUrl}
                  onChange={(e) => setApiUrl(e.target.value)}
                  placeholder="http://localhost:8000"
                />
                <p className="text-xs text-muted-foreground">
                  Base URL for the backend API
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="ws-url">WebSocket URL</Label>
                <Input
                  id="ws-url"
                  value={wsUrl}
                  onChange={(e) => setWsUrl(e.target.value)}
                  placeholder="ws://localhost:8000/api/ws/events"
                />
                <p className="text-xs text-muted-foreground">
                  WebSocket endpoint for real-time updates
                </p>
              </div>
              <Button onClick={handleSave}>
                <Save className="h-4 w-4 mr-2" />
                Save Settings
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Feature Flags */}
        <TabsContent value="features" className="mt-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Flag className="h-5 w-5" />
                  <CardTitle>Feature Flags</CardTitle>
                </div>
                {hasFeatureFlagChanges && (
                  <Button onClick={handleApplyFeatureFlags} disabled={setFeatureFlag.isPending}>
                    {setFeatureFlag.isPending ? (
                      <>
                        <Save className="h-4 w-4 mr-2 animate-spin" />
                        Applying...
                      </>
                    ) : (
                      <>
                        <Save className="h-4 w-4 mr-2" />
                        Apply Changes
                      </>
                    )}
                  </Button>
                )}
              </div>
              <CardDescription>
                Enable or disable features
              </CardDescription>
            </CardHeader>
            <CardContent>
              {flagsLoading ? (
                <div className="text-center py-8">
                  <p className="text-muted-foreground">Loading feature flags...</p>
                </div>
              ) : !featureFlags || Object.keys(featureFlags).length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No feature flags configured
                </div>
              ) : (
                <div className="space-y-3">
                  {Object.entries(pendingFeatureFlags).map(([feature, enabled]) => (
                    <div key={feature} className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex-1">
                        <Label htmlFor={`flag-${feature}`} className="font-medium cursor-pointer">
                          {feature.replace(/_/g, ' ').toUpperCase()}
                        </Label>
                        <p className="text-xs text-muted-foreground mt-1">
                          Enable or disable {feature.replace(/_/g, ' ')} feature
                        </p>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="text-sm text-muted-foreground">
                          {enabled ? 'Enabled' : 'Disabled'}
                        </span>
                        <Checkbox
                          id={`flag-${feature}`}
                          checked={enabled}
                          onCheckedChange={(checked) => handleFeatureFlagChange(feature, checked as boolean)}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Logging Levels */}
        <TabsContent value="logging" className="mt-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <FileText className="h-5 w-5" />
                  <CardTitle>Logging Levels</CardTitle>
                </div>
                {hasLogLevelChanges && (
                  <Button onClick={handleApplyLogLevels} disabled={setLogLevel.isPending}>
                    {setLogLevel.isPending ? (
                      <>
                        <Save className="h-4 w-4 mr-2 animate-spin" />
                        Applying...
                      </>
                    ) : (
                      <>
                        <Save className="h-4 w-4 mr-2" />
                        Apply Changes
                      </>
                    )}
                  </Button>
                )}
              </div>
              <CardDescription>
                Configure log levels for global and module-specific logging
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Global Log Level */}
              <div>
                <Label className="text-base font-semibold mb-3 block">Global Log Level</Label>
                <div className="flex items-center justify-between p-3 border rounded-lg">
                  <div>
                    <p className="font-medium">Global Log Level</p>
                    <p className="text-xs text-muted-foreground">Default log level for all modules</p>
                  </div>
                  <Select
                    value={globalLogLevel}
                    onValueChange={(value) => handleLogLevelChange('_global', value)}
                  >
                    <SelectTrigger className="w-40">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {LOG_LEVELS.map((level) => (
                        <SelectItem key={level} value={level}>
                          {level}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <Separator />

              {/* Module Log Levels */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <Label className="text-base font-semibold">Module Log Levels</Label>
                  <div className="relative w-64">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Search modules..."
                      value={moduleSearch}
                      onChange={(e) => setModuleSearch(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                </div>
                {levelsLoading ? (
                  <div className="text-center py-8">
                    <p className="text-muted-foreground">Loading log levels...</p>
                  </div>
                ) : filteredModules.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    {moduleSearch ? 'No modules found' : 'No module-specific log levels configured'}
                  </div>
                ) : (
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {filteredModules.map((module) => {
                      const currentLevel = pendingLogLevels[module] || logLevels?.[module] || 'INFO'
                      return (
                        <div key={module} className="flex items-center justify-between p-3 border rounded-lg">
                          <div className="flex-1">
                            <p className="font-medium text-sm">{module}</p>
                          </div>
                          <Select
                            value={currentLevel}
                            onValueChange={(value) => handleLogLevelChange(module, value)}
                          >
                            <SelectTrigger className="w-40">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {LOG_LEVELS.map((level) => (
                                <SelectItem key={level} value={level}>
                                  {level}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* System Settings */}
        <TabsContent value="system" className="mt-6">
          <Card>
            <CardHeader>
              <div className="flex items-center space-x-2">
                <Database className="h-5 w-5" />
                <CardTitle>System Settings</CardTitle>
              </div>
              <CardDescription>
                All settings by module
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!allSettings || allSettings.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No system settings found
                </div>
              ) : (
                <div className="space-y-6">
                  {Object.entries(
                    allSettings.reduce((acc: Record<string, any[]>, setting) => {
                      const category = setting.category || 'other'
                      if (!acc[category]) acc[category] = []
                      acc[category].push(setting)
                      return acc
                    }, {})
                  ).map(([category, settings]) => (
                    <div key={category}>
                      <h3 className="font-semibold mb-3 text-primary">{category.toUpperCase()}</h3>
                      <div className="space-y-2">
                        {settings.map((setting) => (
                          <div key={setting.key} className="flex items-center justify-between p-3 border rounded-lg">
                            <div className="flex-1">
                              <p className="font-medium text-sm">{setting.key}</p>
                              {setting.description && (
                                <p className="text-xs text-muted-foreground mt-1">{setting.description}</p>
                              )}
                            </div>
                            <div className="text-sm font-mono text-muted-foreground">
                              {typeof setting.value === 'object' 
                                ? JSON.stringify(setting.value)
                                : String(setting.value)}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
