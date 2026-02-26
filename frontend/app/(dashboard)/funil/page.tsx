'use client'

import { useState, useEffect } from 'react'
import { useLeads, useUpdateLeadStage } from '@/hooks/api/useLeads'
import { KanbanBoard } from '@/components/funil/KanbanBoard'
import { LeadDetailsModal } from '@/components/funil/LeadDetailsModal'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Search, Filter } from 'lucide-react'

interface FilterState {
  searchQuery: string
  sourceFilter: string
  scoreFilter: string
}

const FILTER_STORAGE_KEY = 'funil-filters'

export default function FunilPage() {
  // Load saved filters from localStorage
  const [filters, setFilters] = useState<FilterState>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(FILTER_STORAGE_KEY)
      if (saved) {
        try {
          return JSON.parse(saved)
        } catch {
          return { searchQuery: '', sourceFilter: 'all', scoreFilter: 'all' }
        }
      }
    }
    return { searchQuery: '', sourceFilter: 'all', scoreFilter: 'all' }
  })

  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null)

  const { data: leads, isLoading } = useLeads()
  const updateLeadStage = useUpdateLeadStage()

  // Save filters to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(filters))
  }, [filters])

  // Filter leads based on search and filters
  const filteredLeads = leads?.filter((lead) => {
    const matchesSearch =
      filters.searchQuery === '' ||
      lead.full_name.toLowerCase().includes(filters.searchQuery.toLowerCase()) ||
      lead.phone?.includes(filters.searchQuery) ||
      lead.email?.toLowerCase().includes(filters.searchQuery.toLowerCase())

    const matchesSource = filters.sourceFilter === 'all' || lead.source === filters.sourceFilter

    const matchesScore =
      filters.scoreFilter === 'all' ||
      (filters.scoreFilter === 'high' && lead.score >= 70) ||
      (filters.scoreFilter === 'medium' && lead.score >= 40 && lead.score < 70) ||
      (filters.scoreFilter === 'low' && lead.score < 40)

    return matchesSearch && matchesSource && matchesScore
  })

  const handleLeadMove = async (leadId: string, newStage: string) => {
    try {
      await updateLeadStage.mutateAsync({ id: leadId, stage: newStage })
    } catch (error) {
      console.error('Failed to update lead stage:', error)
    }
  }

  const handleLeadClick = (leadId: string) => {
    setSelectedLeadId(leadId)
  }

  const handleCloseModal = () => {
    setSelectedLeadId(null)
  }

  const clearFilters = () => {
    setFilters({ searchQuery: '', sourceFilter: 'all', scoreFilter: 'all' })
  }

  const hasActiveFilters =
    filters.searchQuery !== '' || filters.sourceFilter !== 'all' || filters.scoreFilter !== 'all'

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b bg-white p-6">
        <h1 className="text-2xl font-bold text-gray-900">Funil de Leads</h1>
        <p className="mt-1 text-sm text-gray-500">
          Gerencie seus leads através do funil de vendas
        </p>
      </div>

      {/* Filters */}
      <div className="border-b bg-white p-4">
        <div className="flex flex-wrap gap-4">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input
              placeholder="Buscar por nome, telefone ou email..."
              value={filters.searchQuery}
              onChange={(e) => setFilters({ ...filters, searchQuery: e.target.value })}
              className="pl-10"
            />
          </div>

          {/* Source Filter */}
          <Select
            value={filters.sourceFilter}
            onValueChange={(value) => setFilters({ ...filters, sourceFilter: value })}
          >
            <SelectTrigger className="w-[180px]">
              <Filter className="mr-2 h-4 w-4" />
              <SelectValue placeholder="Fonte" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todas as fontes</SelectItem>
              <SelectItem value="chatwit">Chatwit</SelectItem>
              <SelectItem value="website">Website</SelectItem>
              <SelectItem value="referral">Indicação</SelectItem>
              <SelectItem value="other">Outro</SelectItem>
            </SelectContent>
          </Select>

          {/* Score Filter */}
          <Select
            value={filters.scoreFilter}
            onValueChange={(value) => setFilters({ ...filters, scoreFilter: value })}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Score" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos os scores</SelectItem>
              <SelectItem value="high">Alto (70+)</SelectItem>
              <SelectItem value="medium">Médio (40-69)</SelectItem>
              <SelectItem value="low">Baixo (&lt;40)</SelectItem>
            </SelectContent>
          </Select>

          {/* Clear Filters */}
          {hasActiveFilters && (
            <Button variant="outline" onClick={clearFilters}>
              Limpar filtros
            </Button>
          )}
        </div>

        {/* Filter Summary */}
        {hasActiveFilters && (
          <div className="mt-3 text-sm text-gray-600">
            Mostrando {filteredLeads?.length || 0} de {leads?.length || 0} leads
          </div>
        )}
      </div>

      {/* Kanban Board */}
      <div className="flex-1 overflow-hidden bg-gray-50">
        {isLoading ? (
          <div className="flex h-full items-center justify-center">
            <div className="text-gray-500">Carregando leads...</div>
          </div>
        ) : (
          <KanbanBoard
            leads={filteredLeads || []}
            onLeadMove={handleLeadMove}
            onLeadClick={handleLeadClick}
          />
        )}
      </div>

      {/* Lead Details Modal */}
      {selectedLeadId && (
        <LeadDetailsModal leadId={selectedLeadId} onClose={handleCloseModal} />
      )}
    </div>
  )
}
