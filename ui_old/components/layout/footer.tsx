'use client'

export function Footer() {
  return (
    <footer className="border-t mt-auto">
      <div className="container mx-auto px-4 py-6">
        <div className="flex flex-col md:flex-row items-center justify-between space-y-2 md:space-y-0">
          <div className="text-sm text-muted-foreground">
            © {new Date().getFullYear()} AARD - AI Agent Research Dashboard
          </div>
          <div className="flex items-center space-x-4 text-sm text-muted-foreground">
            <span>Version 0.1.0</span>
            <span>•</span>
            <span>Next.js 15 + React 19</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
