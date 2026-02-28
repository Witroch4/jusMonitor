'use client'

import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '@/lib/api-client'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Search, ChevronLeft, ChevronRight } from 'lucide-react'
import type { LegalCase } from '@/types'

interface CaseListData {
  items: LegalCase[]
  total: number
  skip: number
  limit: number
}

const statusLabels: Record<string, string> = {
  active: 'Ativo',
  archived: 'Arquivado',
  suspended: 'Suspenso',
  closed: 'Encerrado',
}

const statusVariants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  active: 'default',
  archived: 'secondary',
  suspended: 'outline',
  closed: 'destructive',
}

export default function ProcessosPage() {
  const [data, setData] = useState<CaseListData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [page, setPage] = useState(0)
  const limit = 20

  const fetchCases = useCallback(async () => {
    setIsLoading(true)
    try {
      const params: Record<string, any> = {
        skip: page * limit,
        limit,
        sort_by: 'created_at',
        sort_order: 'desc',
      }
      if (search) params.search = search
      if (statusFilter !== 'all') params.status = statusFilter

      const res = await apiClient.get('/cases', { params })
      setData(res.data)
    } catch (error) {
      console.error('Error fetching cases:', error)
      // If the endpoint doesn't exist yet, show empty state
      setData({ items: [], total: 0, skip: 0, limit })
    } finally {
      setIsLoading(false)
    }
  }, [page, search, statusFilter])

  useEffect(() => {
    fetchCases()
  }, [fetchCases])

  const totalPages = data ? Math.ceil(data.total / limit) : 0

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleDateString('pt-BR')
  }

  return (
    <div className="flex-1 p-8 lg:p-12 overflow-y-auto bg-background transition-colors duration-300">
      <header className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4 border-b border-border/40 pb-6">
        <div>
          <h1 className="text-3xl md:text-4xl font-serif font-bold text-foreground tracking-tight">Processos</h1>
          <p className="mt-2 text-sm font-medium text-muted-foreground tracking-wide">
            Acompanhamento centralizado de matérias jurídicas
          </p>
        </div>
        <Button className="bg-primary hover:bg-primary/90 text-primary-foreground font-medium shadow-sm transition-all duration-300">
          <span className="material-icons-outlined text-sm mr-2">add</span>
          Novo Processo
        </Button>
      </header>

      {/* Filters */}
      <div className="flex flex-wrap gap-4 mb-8">
        <div className="relative flex-1 min-w-[300px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Buscar por número CNJ, tribunal ou assunto..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(0)
            }}
            className="pl-10 border-border/60 bg-white shadow-sm focus-visible:ring-primary/20 transition-all rounded-lg"
          />
        </div>
        <Select
          value={statusFilter}
          onValueChange={(value) => {
            setStatusFilter(value)
            setPage(0)
          }}
        >
          <SelectTrigger className="w-[220px] bg-white border-border/60 shadow-sm rounded-lg hover:bg-muted/30 transition-colors">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos os status</SelectItem>
            <SelectItem value="active">Ativo</SelectItem>
            <SelectItem value="archived">Arquivado</SelectItem>
            <SelectItem value="suspended">Suspenso</SelectItem>
            <SelectItem value="closed">Encerrado</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <div className="border border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden bg-card transition-all duration-300">
        <Table>
          <TableHeader className="bg-muted/30">
            <TableRow className="hover:bg-transparent border-b-border/40">
              <TableHead className="font-semibold text-xs uppercase tracking-wider text-muted-foreground h-12">Número CNJ</TableHead>
              <TableHead className="font-semibold text-xs uppercase tracking-wider text-muted-foreground h-12">Tribunal</TableHead>
              <TableHead className="font-semibold text-xs uppercase tracking-wider text-muted-foreground h-12">Tipo</TableHead>
              <TableHead className="font-semibold text-xs uppercase tracking-wider text-muted-foreground h-12">Status</TableHead>
              <TableHead className="font-semibold text-xs uppercase tracking-wider text-muted-foreground h-12">Última Movimentação</TableHead>
              <TableHead className="font-semibold text-xs uppercase tracking-wider text-muted-foreground h-12">Próximo Prazo</TableHead>
              <TableHead className="font-semibold text-xs uppercase tracking-wider text-muted-foreground h-12">Monitoramento</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-12 text-muted-foreground">
                  <div className="flex flex-col items-center justify-center gap-2">
                    <span className="material-icons-outlined animate-spin text-primary">sync</span>
                    <span className="font-medium">Carregando processos...</span>
                  </div>
                </TableCell>
              </TableRow>
            ) : !data?.items?.length ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-12 text-muted-foreground">
                  <div className="flex flex-col items-center justify-center gap-2">
                    <span className="material-icons-outlined text-4xl text-muted-foreground/50">folder_open</span>
                    <span className="font-medium">Nenhum processo encontrado</span>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              data.items.map((legalCase) => (
                <TableRow key={legalCase.id} className="hover:bg-muted/20 transition-colors border-b-border/40 group">
                  <TableCell className="font-serif font-semibold text-foreground group-hover:text-primary transition-colors">
                    {legalCase.cnjNumber}
                  </TableCell>
                  <TableCell className="text-sm font-medium text-muted-foreground">{legalCase.court || '-'}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{legalCase.caseType || '-'}</TableCell>
                  <TableCell>
                    <Badge variant={statusVariants[legalCase.status || ''] || 'outline'} className="font-medium shadow-sm">
                      {statusLabels[legalCase.status || ''] || legalCase.status || '-'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm font-medium text-foreground">{formatDate(legalCase.lastMovementDate)}</TableCell>
                  <TableCell className="text-sm font-medium text-foreground">{formatDate(legalCase.nextDeadline)}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${legalCase.monitoringEnabled ? 'bg-green-500' : 'bg-muted-foreground'}`} />
                      <span className="text-sm font-medium text-muted-foreground">{legalCase.monitoringEnabled ? 'Ativo' : 'Inativo'}</span>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-border/40 px-6 py-4 bg-muted/10">
            <p className="text-sm font-medium text-muted-foreground">
              Mostrando página <span className="text-foreground font-semibold">{page + 1}</span> de <span className="text-foreground font-semibold">{totalPages}</span>
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="shadow-sm hover:bg-white transition-colors"
              >
                <ChevronLeft className="h-4 w-4 mr-1" /> Anterior
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="shadow-sm hover:bg-white transition-colors"
              >
                Próxima <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
