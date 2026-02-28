'use client'

import { useDraggable } from '@dnd-kit/core'
import { Lead } from '@/hooks/api/useLeads'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'
import {
  Phone,
  Mail,
  MoreVertical,
  TrendingUp,
  Clock,
  AlertCircle,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'

interface LeadCardProps {
  lead: Lead
  onClick: () => void
  isDragging?: boolean
}

export function LeadCard({ lead, onClick, isDragging = false }: LeadCardProps) {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({
    id: lead.id,
  })

  const style = transform
    ? {
      transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
    }
    : undefined

  // Determine urgency badge
  const getUrgencyBadge = () => {
    if (lead.score >= 80) {
      return (
        <Badge variant="destructive" className="flex items-center gap-1">
          <AlertCircle className="h-3 w-3" />
          Urgente
        </Badge>
      )
    } else if (lead.score >= 60) {
      return (
        <Badge variant="default" className="flex items-center gap-1 bg-orange-500">
          <TrendingUp className="h-3 w-3" />
          Alta prioridade
        </Badge>
      )
    }
    return null
  }

  // Format source
  const getSourceLabel = (source: string) => {
    const sourceMap: Record<string, string> = {
      chatwit: 'Chatwit',
      website: 'Website',
      referral: 'Indicação',
      other: 'Outro',
    }
    return sourceMap[source] || source
  }

  // Calculate time since last update
  const lastInteraction = formatDistanceToNow(new Date(lead.updated_at), {
    addSuffix: true,
    locale: ptBR,
  })

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`
        group relative cursor-grab rounded-xl border border-border/40 bg-card p-5 shadow-sm
        transition-all duration-300 hover:shadow-[0_8px_30px_rgb(0,0,0,0.06)] hover:border-primary/20 active:cursor-grabbing
        ${isDragging ? 'opacity-50 ring-2 ring-primary/30' : 'opacity-100'}
      `}
      onClick={(e) => {
        // Only trigger onClick if not clicking on the menu
        if (!(e.target as HTMLElement).closest('[data-menu]')) {
          onClick()
        }
      }}
    >
      {/* Header */}
      <div className="mb-4 flex items-start justify-between">
        <div className="flex-1 pr-6">
          <h4 className="font-serif font-semibold text-lg text-foreground line-clamp-1 group-hover:text-primary transition-colors">
            {lead.full_name}
          </h4>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <Badge variant="secondary" className="text-[10px] tracking-wider uppercase bg-muted/50 text-muted-foreground font-semibold">
              {getSourceLabel(lead.source)}
            </Badge>
            {getUrgencyBadge()}
          </div>
        </div>

        {/* Actions Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild data-menu>
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100"
              onClick={(e) => e.stopPropagation()}
            >
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" data-menu>
            <DropdownMenuItem onClick={(e) => {
              e.stopPropagation()
              onClick()
            }}>
              Ver detalhes
            </DropdownMenuItem>
            <DropdownMenuItem onClick={(e) => {
              e.stopPropagation()
              if (lead.phone) {
                window.open(`tel:${lead.phone}`, '_blank')
              }
            }}>
              Ligar
            </DropdownMenuItem>
            <DropdownMenuItem onClick={(e) => {
              e.stopPropagation()
              if (lead.email) {
                window.open(`mailto:${lead.email}`, '_blank')
              }
            }}>
              Enviar email
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Contact Info */}
      <div className="space-y-2.5 text-sm text-muted-foreground bg-muted/5 p-3 rounded-lg border border-border/20">
        {lead.phone && (
          <div className="flex items-center gap-2.5">
            <Phone className="h-4 w-4 text-primary/70" />
            <span className="truncate font-medium">{lead.phone}</span>
          </div>
        )}
        {lead.email && (
          <div className="flex items-center gap-2.5">
            <Mail className="h-4 w-4 text-primary/70" />
            <span className="truncate font-medium">{lead.email}</span>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="mt-5 flex items-center justify-between border-t border-border/40 pt-4">
        <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
          <Clock className="h-3.5 w-3.5 text-muted-foreground/70" />
          {lastInteraction}
        </div>
        <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-primary/5 border border-primary/10">
          <TrendingUp className="h-3.5 w-3.5 text-primary" />
          <span className="text-xs font-bold text-primary">
            {lead.score}
          </span>
        </div>
      </div>
    </div>
  )
}
