import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { PeticaoStatus } from '@/types/peticoes'
import { STATUS_LABELS } from '@/types/peticoes'

const statusStyles: Record<PeticaoStatus, string> = {
  rascunho: 'border-border text-muted-foreground bg-transparent',
  validando: 'bg-blue-500/10 text-blue-600 border-blue-200 dark:text-blue-400 dark:border-blue-800',
  assinando: 'bg-violet-500/10 text-violet-600 border-violet-200 dark:text-violet-400 dark:border-violet-800',
  protocolando: 'bg-primary/15 text-primary border-primary/30',
  protocolada: 'bg-primary/20 text-primary border-primary/40 font-semibold',
  aceita: 'bg-emerald-500/15 text-emerald-700 border-emerald-200 dark:text-emerald-400 dark:border-emerald-800',
  rejeitada: 'bg-destructive/10 text-destructive border-destructive/30',
}

const statusIcons: Record<PeticaoStatus, string> = {
  rascunho: 'edit_note',
  validando: 'policy',
  assinando: 'draw',
  protocolando: 'sync',
  protocolada: 'task_alt',
  aceita: 'check_circle',
  rejeitada: 'cancel',
}

interface PeticaoStatusBadgeProps {
  status: PeticaoStatus
  showIcon?: boolean
  className?: string
}

export function PeticaoStatusBadge({ status, showIcon = false, className }: PeticaoStatusBadgeProps) {
  return (
    <Badge
      variant="outline"
      className={cn('gap-1 font-medium', statusStyles[status], className)}
    >
      {showIcon && (
        <span className={cn('material-symbols-outlined text-sm', status === 'protocolando' && 'animate-spin')}>
          {statusIcons[status]}
        </span>
      )}
      {STATUS_LABELS[status]}
    </Badge>
  )
}
