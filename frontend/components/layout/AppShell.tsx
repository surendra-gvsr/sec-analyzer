import { Sidebar } from './Sidebar'
import { MobileHeader } from './MobileHeader'

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <div className="hidden md:flex md:w-60 md:flex-col md:fixed md:inset-y-0">
        <Sidebar />
      </div>
      <div className="flex flex-1 flex-col md:pl-60">
        <MobileHeader />
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  )
}
