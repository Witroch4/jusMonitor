import { Sidebar } from '@/components/layout/Sidebar'
import { SidebarProvider, SidebarTrigger, SidebarInset } from '@/components/ui/sidebar'
import { UserNav } from '@/components/layout/UserNav'
import { NotificationsNav } from '@/components/layout/NotificationsNav'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <SidebarProvider>
      <Sidebar />
      <div className="flex flex-col min-h-svh w-full flex-1 min-w-0">
        <header className="sticky top-0 z-10 flex items-center justify-between h-14 px-4 border-b border-border bg-background/80 backdrop-blur-sm md:px-6">
          <div className="flex items-center gap-2">
            <SidebarTrigger />
            <div className="hidden md:flex relative ml-4">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-xl">
                search
              </span>
              <input
                id="header-search"
                className="pl-10 pr-4 py-1.5 w-64 rounded-full border border-border bg-card text-sm text-foreground focus:ring-primary focus:border-primary placeholder:text-muted-foreground transition-all"
                placeholder="Buscar..."
                type="text"
              />
            </div>
          </div>

          <div className="flex items-center gap-4">
            <NotificationsNav />
            <UserNav />
          </div>
        </header>
        <SidebarInset>
          <main className="flex-1 overflow-y-auto px-4 pb-12 pt-6 md:px-8 bg-background">
            {children}
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  )
}
