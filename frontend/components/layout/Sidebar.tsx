'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { useState, useEffect } from 'react'

import { cn } from '@/lib/utils'
import {
  Sidebar as ShadcnSidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarTrigger,
  useSidebar,
} from '@/components/ui/sidebar'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: 'dashboard' },
  { name: 'Casos', href: '/processos', icon: 'work' },
  { name: 'Petições', href: '/peticoes', icon: 'gavel' },
  { name: 'Contratos', href: '/contratos', icon: 'description' },
  { name: 'Clientes', href: '/clientes', icon: 'group' },
  { name: 'Financeiro', href: '/financeiro', icon: 'account_balance_wallet' },
  { name: 'Central de IA', href: '/central', icon: 'smart_toy' },
  { name: 'Configurações', href: '/configuracoes', icon: 'settings' },
]

const superAdminNavigation = [
  { name: 'Provedores IA', href: '/admin/ia', icon: 'psychology' },
]

export function Sidebar() {
  const pathname = usePathname()
  const { logout, user } = useAuth()
  const [isDark, setIsDark] = useState(false)
  const { state } = useSidebar()
  const isCollapsed = state === 'collapsed'
  const isSuperAdmin = user?.role === 'super_admin'

  useEffect(() => {
    setIsDark(document.documentElement.classList.contains('dark'))
  }, [])

  function toggleTheme() {
    if (isDark) {
      document.documentElement.classList.remove('dark')
      setIsDark(false)
    } else {
      document.documentElement.classList.add('dark')
      setIsDark(true)
    }
  }

  return (
    // bg-sidebar agora funciona corretamente com @theme inline
    // Removido z-30 para não atropelar o layout e garantindo as bordas corretas
    <ShadcnSidebar collapsible="icon" className="border-r border-sidebar-border font-sans">


      <SidebarHeader className={cn("pt-6 pb-2 transition-all duration-200", isCollapsed ? "px-0 items-center justify-center" : "px-4")}>
        <SidebarMenu className={isCollapsed ? "items-center justify-center" : ""}>
          <SidebarMenuItem className={isCollapsed ? "flex items-center justify-center w-full" : ""}>
            <div className={cn("flex items-center transition-all", isCollapsed ? "justify-center" : "gap-2")}>
              <span className="material-symbols-outlined text-sidebar-primary text-3xl shrink-0">balance</span>
              {!isCollapsed && (
                <h1 className="font-display text-xl font-bold tracking-tight text-sidebar-primary leading-tight truncate whitespace-nowrap">
                  JusMonito<span className="text-sidebar-foreground">IA</span>
                </h1>
              )}
            </div>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent className="px-2 mt-4">
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu className="gap-1">
              {navigation.map((item) => {
                const isActive = pathname === item.href
                return (
                  <SidebarMenuItem key={item.name}>
                    <SidebarMenuButton
                      asChild
                      isActive={isActive}
                      tooltip={item.name}
                      className="h-11 rounded-lg transition-all"
                    >
                      <Link href={item.href}>
                        <span className="material-symbols-outlined shrink-0 text-xl">{item.icon}</span>
                        <span>{item.name}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {isSuperAdmin && (
          <SidebarGroup className="mt-2">
            {!isCollapsed && (
              <p className="px-2 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
                Super Admin
              </p>
            )}
            <SidebarGroupContent>
              <SidebarMenu className="gap-1">
                {superAdminNavigation.map((item) => {
                  const isActive = pathname === item.href
                  return (
                    <SidebarMenuItem key={item.name}>
                      <SidebarMenuButton
                        asChild
                        isActive={isActive}
                        tooltip={item.name}
                        className="h-11 rounded-lg transition-all text-amber-600 data-[active=true]:bg-amber-50 data-[active=true]:text-amber-700 dark:text-amber-400 dark:data-[active=true]:bg-amber-950/40"
                      >
                        <Link href={item.href}>
                          <span className="material-symbols-outlined shrink-0 text-xl">{item.icon}</span>
                          <span>{item.name}</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  )
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}
      </SidebarContent>

      <SidebarFooter className={cn("pb-6 mt-auto border-t border-sidebar-border transition-all duration-200", isCollapsed ? "px-0 py-4 items-center justify-center" : "p-4")}>
        <SidebarMenu className={cn("gap-1 w-full", isCollapsed ? "items-center justify-center" : "")}>
          <SidebarMenuItem className={isCollapsed ? "flex items-center justify-center w-full" : ""}>
            <SidebarMenuButton
              onClick={toggleTheme}
              tooltip={isDark ? 'Modo Claro' : 'Modo Escuro'}
              className={cn("h-10 rounded-lg", isCollapsed ? "justify-center" : "")}
            >
              <span className="material-symbols-outlined shrink-0 text-xl">
                {isDark ? 'light_mode' : 'dark_mode'}
              </span>
              {!isCollapsed && <span>{isDark ? 'Modo Claro' : 'Modo Escuro'}</span>}
            </SidebarMenuButton>
          </SidebarMenuItem>

          <SidebarMenuItem className={isCollapsed ? "flex items-center justify-center w-full" : ""}>
            <SidebarMenuButton
              onClick={logout}
              tooltip="Sair"
              className={cn("h-10 rounded-lg hover:bg-destructive/10 hover:text-destructive transition-colors", isCollapsed ? "justify-center" : "")}
            >
              <span className="material-symbols-outlined shrink-0 text-xl">logout</span>
              {!isCollapsed && <span>Sair</span>}
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </ShadcnSidebar>
  )
}
