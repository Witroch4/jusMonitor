'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { useAuth } from '@/hooks/useAuth'
import { useState, useEffect } from 'react'

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

export function Sidebar() {
  const pathname = usePathname()
  const { logout } = useAuth()
  const [isDark, setIsDark] = useState(false)

  useEffect(() => {
    // Check initial theme
    if (document.documentElement.classList.contains('dark')) {
      setIsDark(true)
    }
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

  function handleLogout() {
    logout()
  }

  return (
    <aside className="w-64 bg-sidebar border-r border-sidebar-border hidden md:flex flex-col h-full z-10 shrink-0">
      <div className="p-8">
        <div className="flex items-center gap-2 mb-10">
          <span className="material-symbols-outlined text-primary text-3xl">balance</span>
          <h1 className="font-display text-xl font-bold tracking-tight text-sidebar-foreground leading-tight">
            JusMonito<span className="text-primary">IA</span>
          </h1>
        </div>

        <nav className="space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  'flex items-center gap-3 px-4 py-3 rounded-xl transition-all text-sidebar-foreground',
                  isActive
                    ? 'text-primary bg-primary/10 font-semibold border-l-4 border-primary'
                    : 'opacity-60 hover:opacity-100 hover:bg-black/5 dark:hover:bg-white/5 font-medium'
                )}
              >
                <span className="material-symbols-outlined">{item.icon}</span>
                {item.name}
              </Link>
            )
          })}
        </nav>
      </div>

      <div className="mt-auto p-8 flex flex-col gap-2">
        <button
          onClick={toggleTheme}
          className="flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-semibold uppercase tracking-widest text-sidebar-foreground transition-all duration-200 opacity-60 hover:opacity-100 hover:bg-black/10 dark:hover:bg-white/10 active:scale-95 text-left w-full"
        >
          <span className="material-symbols-outlined text-lg">
            {isDark ? 'light_mode' : 'dark_mode'}
          </span>
          {isDark ? 'Modo Claro' : 'Modo Escuro'}
        </button>

        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-semibold uppercase tracking-widest text-sidebar-foreground transition-all duration-200 opacity-60 hover:opacity-100 hover:bg-destructive/20 hover:text-destructive active:scale-95 text-left w-full"
        >
          <span className="material-symbols-outlined text-lg">logout</span>
          Sair
        </button>
      </div>
    </aside>
  )
}
