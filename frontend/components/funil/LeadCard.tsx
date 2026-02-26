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
        group relative cursor-grab rounded-lg border bg-white p-4 shadow-sm
        transition-all hover:shadow-md active:cursor-grabbing
        ${isDragging ? 'opacity-50' : 'opacity-100'}
      `}
      onClick={(e) => {
        // Only trigger onClick if not clicking on the menu
        if (!(e.target as HTMLElement).closest('[data-menu]')) {
          onClick()
        }
      }}
    >
      {/* Header */}
      <div className="mb-3 flex items-start justify-between">
        <div className="flex-1">
          <h4 className="font-semibold text-gray-900 line-clamp-1">
            {lead.full_name}
          </h4>
          <div className="mt-1 flex items-center gap-2">
            <Badge variant="outline" className="text-xs">
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
      <div className="space-y-2 text-sm text-gray-600">
        {lead.phone && (
          <div className="flex items-center gap-2">
            <Phone className="h-4 w-4 text-gray-400" />
            <span className="truncate">{lead.phone}</span>
          </div>
        )}
        {lead.email && (
          <div className="flex items-center gap-2">
            <Mail className="h-4 w-4 text-gray-400" />
            <span className="truncate">{lead.email}</span>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="mt-4 flex items-center justify-between border-t pt-3">
        <div className="flex items-center gap-1 text-xs text-gray-500">
          <Clock className="h-3 w-3" />
          {lastInteraction}
        </div>
        <div className="flex items-center gap-1">
          <TrendingUp className="h-4 w-4 text-blue-500" />
          <span className="text-sm font-semibold text-blue-600">
            {lead.score}
          </span>
        </div>
      </div>
    </div>
  )
}
