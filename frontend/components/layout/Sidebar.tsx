'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: '📊' },
  { name: 'Funil', href: '/funil', icon: '🎯' },
  { name: 'Clientes', href: '/clientes', icon: '👥' },
  { name: 'Processos', href: '/processos', icon: '⚖️' },
  { name: 'Central', href: '/central', icon: '💬' },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <div className="flex w-64 flex-col bg-gray-900">
      <div className="flex h-16 items-center px-6">
        <h1 className="text-xl font-bold text-white">JusMonitor</h1>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {navigation.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-gray-800 text-white'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              )}
            >
              <span className="text-lg">{item.icon}</span>
              {item.name}
            </Link>
          )
        })}
      </nav>
    </div>
  )
}
