'use client'

import { Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { User, Shield, FileKey, Plug, Bell } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Skeleton } from '@/components/ui/skeleton'
import { PerfilTab } from '@/components/configuracoes/PerfilTab'
import { SegurancaTab } from '@/components/configuracoes/SegurancaTab'
import { AssinaturaTab } from '@/components/configuracoes/AssinaturaTab'
import { IntegracoesTab } from '@/components/configuracoes/IntegracoesTab'
import { NotificacoesTab } from '@/components/configuracoes/NotificacoesTab'

const TABS = [
  { id: 'perfil', label: 'Perfil', Icon: User },
  { id: 'seguranca', label: 'Segurança', Icon: Shield },
  { id: 'assinatura', label: 'Assinatura Digital', Icon: FileKey },
  { id: 'integracoes', label: 'Integrações', Icon: Plug },
  { id: 'notificacoes', label: 'Notificações', Icon: Bell },
] as const

function ConfiguracoesContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const activeTab = searchParams.get('tab') || 'perfil'

  const setTab = (id: string) => {
    router.push(`/configuracoes?tab=${id}`, { scroll: false })
  }

  return (
    <div className="flex-1 p-6 lg:p-10 overflow-y-auto bg-background transition-colors duration-300">
      <header className="mb-8 border-b border-border/40 pb-6">
        <h1 className="text-3xl md:text-4xl font-serif font-bold text-foreground tracking-tight">
          Configurações
        </h1>
        <p className="mt-2 text-sm font-medium text-muted-foreground tracking-wide">
          Gerencie suas preferências de conta, segurança e integrações.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-[240px_1fr] gap-8">
        {/* Settings sidebar navigation */}
        <nav className="space-y-1">
          {TABS.map(({ id, label, Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={cn(
                'w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left',
                'font-serif font-medium text-[15px] transition-all duration-200',
                activeTab === id
                  ? 'bg-primary/10 text-primary font-semibold shadow-sm'
                  : 'text-muted-foreground hover:bg-muted/40 hover:text-foreground'
              )}
            >
              <Icon
                className={cn(
                  'w-[18px] h-[18px] shrink-0',
                  activeTab === id ? 'text-primary' : ''
                )}
              />
              {label}
            </button>
          ))}
        </nav>

        {/* Tab content area */}
        <div className="min-w-0 space-y-6">
          {activeTab === 'perfil' && <PerfilTab />}
          {activeTab === 'seguranca' && <SegurancaTab />}
          {activeTab === 'assinatura' && <AssinaturaTab />}
          {activeTab === 'integracoes' && <IntegracoesTab />}
          {activeTab === 'notificacoes' && <NotificacoesTab />}
        </div>
      </div>
    </div>
  )
}

export default function ConfiguracoesPage() {
  return (
    <Suspense
      fallback={
        <div className="flex-1 p-6 lg:p-10">
          <Skeleton className="h-12 w-64 mb-4" />
          <Skeleton className="h-6 w-96 mb-8" />
          <div className="grid grid-cols-1 lg:grid-cols-[240px_1fr] gap-8">
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-11 w-full rounded-lg" />
              ))}
            </div>
            <Skeleton className="h-96 w-full rounded-xl" />
          </div>
        </div>
      }
    >
      <ConfiguracoesContent />
    </Suspense>
  )
}
