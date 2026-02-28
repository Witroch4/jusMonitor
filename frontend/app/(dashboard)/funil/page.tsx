'use client'

import { useState, useEffect } from 'react'
import { useLeads, useUpdateLeadStage } from '@/hooks/api/useLeads'
import dynamic from 'next/dynamic'

const KanbanBoard = dynamic(() => import('@/components/funil/KanbanBoard').then(m => m.KanbanBoard), {
  loading: () => <div className="flex h-full items-center justify-center"><div className="text-gray-500">Carregando quadro...</div></div>,
})
const LeadDetailsModal = dynamic(() => import('@/components/funil/LeadDetailsModal').then(m => m.LeadDetailsModal))
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
      <div className="flex-none p-8 lg:px-12 pb-6 border-b border-border/40 bg-background transition-colors duration-300">
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl md:text-4xl font-serif font-bold text-foreground tracking-tight">Funil de Leads</h1>
            <p className="mt-2 text-sm font-medium text-muted-foreground tracking-wide">
              Gestão estratégica e acompanhamento da jornada do cliente
            </p>
          </div>
          <Button className="bg-primary hover:bg-primary/90 text-primary-foreground font-medium shadow-sm transition-all duration-300">
            <span className="material-icons-outlined text-sm mr-2">add</span>
            Novo Lead
          </Button>
        </header>
      </div>

      {/* Filters */}
      <div className="flex-none border-b border-border/40 bg-muted/10 p-4 lg:px-12">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-4 flex-1">
            {/* Search */}
            <div className="relative flex-1 min-w-[250px] max-w-md">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Buscar por nome, telefone ou email..."
                value={filters.searchQuery}
                onChange={(e) => setFilters({ ...filters, searchQuery: e.target.value })}
                className="pl-10 border-border/60 bg-white shadow-sm focus-visible:ring-primary/20 transition-all rounded-lg"
              />
            </div>

            {/* Source Filter */}
            <Select
              value={filters.sourceFilter}
              onValueChange={(value) => setFilters({ ...filters, sourceFilter: value })}
            >
              <SelectTrigger className="w-[180px] bg-white border-border/60 shadow-sm rounded-lg hover:bg-muted/30 transition-colors">
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
              <SelectTrigger className="w-[180px] bg-white border-border/60 shadow-sm rounded-lg hover:bg-muted/30 transition-colors">
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
              <Button variant="ghost" onClick={clearFilters} className="text-muted-foreground hover:text-foreground">
                Limpar filtros
              </Button>
            )}
          </div>

          {/* Filter Summary */}
          {hasActiveFilters && (
            <div className="text-sm font-medium text-muted-foreground bg-white px-3 py-1.5 rounded-md border border-border/40 shadow-sm">
              Mostrando <span className="text-foreground font-semibold">{filteredLeads?.length || 0}</span> de {leads?.length || 0} leads
            </div>
          )}
        </div>
      </div>

      {/* Kanban Board */}
      <div className="flex-1 overflow-hidden bg-background">
        {isLoading ? (
          <div className="flex h-full items-center justify-center">
            <div className="flex flex-col items-center justify-center gap-2">
              <span className="material-icons-outlined animate-spin text-primary">sync</span>
              <span className="font-medium text-muted-foreground">Carregando quadro...</span>
            </div>
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
