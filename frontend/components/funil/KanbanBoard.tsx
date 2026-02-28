'use client'

import { useState } from 'react'
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  useDroppable,
} from '@dnd-kit/core'
import { LeadCard } from './LeadCard'
import { Lead } from '@/hooks/api/useLeads'

interface KanbanBoardProps {
  leads: Lead[]
  onLeadMove: (leadId: string, newStage: string) => Promise<void>
  onLeadClick: (leadId: string) => void
}

const COLUMNS = [
  { id: 'novo', title: 'Novo', color: 'bg-blue-100 border-blue-300' },
  { id: 'qualificado', title: 'Qualificado', color: 'bg-yellow-100 border-yellow-300' },
  { id: 'convertido', title: 'Convertido', color: 'bg-green-100 border-green-300' },
]

function DroppableColumn({
  id,
  title,
  color,
  leads,
  onLeadClick,
  isDragging,
  activeId,
}: {
  id: string
  title: string
  color: string
  leads: Lead[]
  onLeadClick: (leadId: string) => void
  isDragging: boolean
  activeId: string | null
}) {
  const { setNodeRef, isOver } = useDroppable({ id })

  return (
    <div className="flex min-w-[320px] flex-1 flex-col">
      {/* Column Header */}
      <div className={`mb-4 rounded-xl border-l-[6px] shadow-sm ${color} bg-white p-4`}>
        <h3 className="text-xl font-serif text-foreground">{title}</h3>
        <p className="text-sm font-medium text-muted-foreground mt-1 tracking-wide">
          {leads.length} {leads.length === 1 ? 'LEAD' : 'LEADS'}
        </p>
      </div>

      {/* Droppable Area */}
      <div
        ref={setNodeRef}
        className={`
          flex-1 space-y-4 rounded-xl p-4 min-h-[200px] transition-all duration-300
          ${isOver ? 'bg-primary/5 border-2 border-primary/20 border-dashed' : 'bg-muted/10 border border-transparent'}
        `}
      >
        {leads.map((lead) => (
          <LeadCard
            key={lead.id}
            lead={lead}
            onClick={() => onLeadClick(lead.id)}
            isDragging={isDragging && activeId === lead.id}
          />
        ))}

        {leads.length === 0 && (
          <div className="flex h-32 items-center justify-center text-sm text-gray-400">
            {isOver ? 'Solte aqui' : 'Nenhum lead nesta etapa'}
          </div>
        )}
      </div>
    </div>
  )
}

export function KanbanBoard({ leads, onLeadMove, onLeadClick }: KanbanBoardProps) {
  const [activeId, setActiveId] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  )

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string)
    setIsDragging(true)
  }

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event
    setActiveId(null)
    setIsDragging(false)

    if (!over) return

    const leadId = active.id as string
    const newStage = over.id as string

    // Find the lead to check if stage actually changed
    const lead = leads.find((l) => l.id === leadId)
    if (!lead || lead.stage === newStage) return

    // Validate stage transition
    const validTransitions: Record<string, string[]> = {
      novo: ['qualificado'],
      qualificado: ['novo', 'convertido'],
      convertido: [], // Cannot move from convertido
    }

    if (!validTransitions[lead.stage]?.includes(newStage)) {
      console.warn(`Invalid transition from ${lead.stage} to ${newStage}`)
      return
    }

    await onLeadMove(leadId, newStage)
  }

  const getLeadsByStage = (stage: string) => {
    return leads.filter((lead) => lead.stage === stage)
  }

  const activeLead = activeId ? leads.find((lead) => lead.id === activeId) : null

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="flex h-full gap-4 overflow-x-auto p-6">
        {COLUMNS.map((column) => {
          const columnLeads = getLeadsByStage(column.id)

          return (
            <DroppableColumn
              key={column.id}
              id={column.id}
              title={column.title}
              color={column.color}
              leads={columnLeads}
              onLeadClick={onLeadClick}
              isDragging={isDragging}
              activeId={activeId}
            />
          )
        })}
      </div>

      {/* Drag Overlay */}
      <DragOverlay>
        {activeLead ? (
          <div className="rotate-3 opacity-80">
            <LeadCard lead={activeLead} onClick={() => { }} isDragging={true} />
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  )
}
