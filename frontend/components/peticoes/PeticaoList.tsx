'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'
import { PeticaoStatusBadge } from './PeticaoStatusBadge'
import { usePeticoes } from '@/hooks/api/usePeticoes'
import { TRIBUNAIS } from '@/lib/data/tribunais'
import { TIPO_PETICAO_LABELS, STATUS_LABELS } from '@/types/peticoes'
import type { PeticaoStatus, TribunalId, PeticaoFilters } from '@/types/peticoes'
import { Search, Plus, ChevronLeft, ChevronRight } from 'lucide-react'

interface PeticaoListProps {
  onNovaPeticao: () => void
}

const PAGE_SIZE = 8

export function PeticaoList({ onNovaPeticao }: PeticaoListProps) {
  const router = useRouter()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<PeticaoStatus | 'all'>('all')
  const [tribunalFilter, setTribunalFilter] = useState<TribunalId | 'all'>('all')
  const [page, setPage] = useState(1)

  const filters: PeticaoFilters = {
    search: search || undefined,
    status: statusFilter,
    tribunalId: tribunalFilter,
  }

  const { data, isLoading } = usePeticoes(filters)
  const items = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)
  const pageItems = items.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  const tribunalNome = (id: TribunalId) => TRIBUNAIS.find((t) => t.id === id)?.nome ?? id

  function formatDate(iso: string) {
    return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl md:text-4xl font-bold text-foreground tracking-tight">
            Petições
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Gerencie e protocole petições nos tribunais
          </p>
        </div>
        <Button onClick={onNovaPeticao} className="shrink-0 gap-2">
          <Plus className="h-4 w-4" />
          Nova Petição
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-3">
        <div className="relative flex-1 min-w-[250px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Buscar por processo, protocolo ou assunto..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            className="pl-10"
          />
        </div>
        <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v as PeticaoStatus | 'all'); setPage(1) }}>
          <SelectTrigger className="w-full md:w-[180px]">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos os Status</SelectItem>
            {(Object.keys(STATUS_LABELS) as PeticaoStatus[]).map((s) => (
              <SelectItem key={s} value={s}>{STATUS_LABELS[s]}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={tribunalFilter} onValueChange={(v) => { setTribunalFilter(v as TribunalId | 'all'); setPage(1) }}>
          <SelectTrigger className="w-full md:w-[180px]">
            <SelectValue placeholder="Tribunal" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos os Tribunais</SelectItem>
            {TRIBUNAIS.map((t) => (
              <SelectItem key={t.id} value={t.id}>{t.nome}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30">
              <TableHead className="text-xs uppercase tracking-wider font-semibold">Protocolo</TableHead>
              <TableHead className="text-xs uppercase tracking-wider font-semibold">Processo</TableHead>
              <TableHead className="text-xs uppercase tracking-wider font-semibold hidden md:table-cell">Tipo</TableHead>
              <TableHead className="text-xs uppercase tracking-wider font-semibold hidden lg:table-cell">Tribunal</TableHead>
              <TableHead className="text-xs uppercase tracking-wider font-semibold">Status</TableHead>
              <TableHead className="text-xs uppercase tracking-wider font-semibold hidden md:table-cell">Data</TableHead>
              <TableHead className="text-xs uppercase tracking-wider font-semibold text-center">Docs</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  {Array.from({ length: 7 }).map((_, j) => (
                    <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                  ))}
                </TableRow>
              ))
            ) : pageItems.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-16">
                  <div className="flex flex-col items-center gap-3">
                    <span className="material-symbols-outlined text-4xl text-muted-foreground/40">
                      folder_open
                    </span>
                    <p className="text-sm text-muted-foreground">
                      Nenhuma petição encontrada
                    </p>
                    <Button variant="outline" size="sm" onClick={onNovaPeticao}>
                      <Plus className="h-3 w-3 mr-1" />
                      Criar primeira petição
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              pageItems.map((item) => (
                <TableRow
                  key={item.id}
                  className="cursor-pointer hover:bg-muted/20 transition-colors"
                  onClick={() => router.push(`/peticoes/${item.id}`)}
                >
                  <TableCell className="font-mono text-xs text-primary font-medium">
                    {item.numeroProtocolo ?? '—'}
                  </TableCell>
                  <TableCell>
                    <div>
                      <p className="text-sm font-medium text-foreground truncate max-w-[200px]">
                        {item.assunto}
                      </p>
                      <p className="text-xs text-muted-foreground font-mono mt-0.5">
                        {item.processoNumero}
                      </p>
                    </div>
                  </TableCell>
                  <TableCell className="hidden md:table-cell text-sm text-muted-foreground">
                    {TIPO_PETICAO_LABELS[item.tipoPeticao]}
                  </TableCell>
                  <TableCell className="hidden lg:table-cell">
                    <span className="text-xs font-medium bg-muted/50 px-2 py-1 rounded-md">
                      {tribunalNome(item.tribunalId)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <PeticaoStatusBadge status={item.status} />
                  </TableCell>
                  <TableCell className="hidden md:table-cell text-sm text-muted-foreground">
                    {formatDate(item.protocoladoEm ?? item.criadoEm)}
                  </TableCell>
                  <TableCell className="text-center">
                    <span className="text-xs font-medium text-muted-foreground">
                      {item.quantidadeDocumentos}
                    </span>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {total} petição{total !== 1 ? 'ões' : ''} encontrada{total !== 1 ? 's' : ''}
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-sm text-muted-foreground">
              {page} de {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage(page + 1)}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
