'use client'

import { cn } from '@/lib/utils'
import { Skeleton } from '@/components/ui/skeleton'
import { usePeticaoEventos } from '@/hooks/api/usePeticoes'
import { STATUS_LABELS } from '@/types/peticoes'
import type { PeticaoStatus } from '@/types/peticoes'

interface Props {
  peticaoId: string
}

const statusColors: Record<PeticaoStatus, string> = {
  rascunho: 'bg-muted-foreground',
  validando: 'bg-blue-500',
  assinando: 'bg-violet-500',
  protocolando: 'bg-primary',
  protocolada: 'bg-primary',
  aceita: 'bg-emerald-500',
  rejeitada: 'bg-destructive',
}

export function PeticaoStatusTimeline({ peticaoId }: Props) {
  const { data: eventos, isLoading } = usePeticaoEventos(peticaoId)

  if (isLoading) {
    return (
      <div className="space-y-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex gap-4">
            <Skeleton className="h-4 w-4 rounded-full shrink-0 mt-1" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-3 w-48" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (!eventos || eventos.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <span className="material-symbols-outlined text-3xl mb-2 block">history</span>
        <p className="text-sm">Nenhum evento registrado</p>
      </div>
    )
  }

  return (
    <div className="relative">
      {/* Vertical line */}
      <div className="absolute left-[7px] top-2 bottom-2 w-0.5 bg-border" />

      <div className="space-y-6">
        {eventos.map((evento, idx) => {
          const isLast = idx === eventos.length - 1

          return (
            <div key={evento.id} className="relative flex gap-4">
              {/* Dot */}
              <div className={cn(
                'w-4 h-4 rounded-full shrink-0 mt-1 border-2 border-card z-10',
                statusColors[evento.status]
              )} />

              {/* Content */}
              <div className="flex-1 pb-2">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className={cn(
                    'text-sm font-semibold',
                    isLast ? 'text-foreground' : 'text-muted-foreground'
                  )}>
                    {STATUS_LABELS[evento.status]}
                  </span>
                  {isLast && (
                    <span className="text-[10px] bg-primary/15 text-primary px-1.5 py-0.5 rounded font-medium">
                      Atual
                    </span>
                  )}
                </div>
                <p className="text-sm text-muted-foreground">{evento.descricao}</p>
                {evento.detalhes && (
                  <div className="mt-2 p-3 rounded-lg bg-destructive/5 border border-destructive/20">
                    <p className="text-xs text-destructive">{evento.detalhes}</p>
                  </div>
                )}
                <p className="text-xs text-muted-foreground/60 mt-1">
                  {new Date(evento.criadoEm).toLocaleString('pt-BR')}
                </p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
