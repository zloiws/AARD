import { MissionControlDashboard } from '@/components/dashboard/mission-control'

export default function Home() {
  return (
    <main className="flex-1 container mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold tracking-tight">Mission Control</h1>
        <p className="text-muted-foreground mt-2">
          Monitor and manage your AI agent workflows
        </p>
      </div>
      <MissionControlDashboard />
    </main>
  )
}
