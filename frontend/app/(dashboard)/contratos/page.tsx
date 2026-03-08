'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
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
import { Search, ChevronLeft, ChevronRight, Plus } from 'lucide-react'
import type { ContratoListResponse } from '@/types'

const statusLabels: Record<string, string> = {
  rascunho: 'Rascunho',
  ativo: 'Ativo',
  suspenso: 'Suspenso',
  encerrado: 'Encerrado',
  cancelado: 'Cancelado',
  vencido: 'Vencido',
}

const statusVariants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  rascunho: 'outline',
  ativo: 'default',
  suspenso: 'secondary',
  encerrado: 'secondary',
  cancelado: 'destructive',
  vencido: 'destructive',
}

const tipoLabels: Record<string, string> = {
  prestacao_servicos: 'Prestação de Serviços',
  honorarios_exito: 'Honorários de Êxito',
  misto: 'Misto',
  consultoria: 'Consultoria',
  contencioso: 'Contencioso',
}

function formatCurrency(value?: number): string {
  if (value == null) return '-'
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value)
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('pt-BR')
}

export default function ContratosPage() {
  const router = useRouter()
  const [data, setData] = useState<ContratoListResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [tipoFilter, setTipoFilter] = useState('all')
  const [page, setPage] = useState(0)
  const limit = 20

  const fetchContratos = useCallback(async () => {
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
      if (tipoFilter !== 'all') params.tipo = tipoFilter

      const res = await apiClient.get('/contratos', { params })
      setData(res.data)
    } catch (error) {
      console.error('Error fetching contratos:', error)
    } finally {
      setIsLoading(false)
    }
  }, [page, search, statusFilter, tipoFilter])

  useEffect(() => {
    fetchContratos()
  }, [fetchContratos])

  const totalPages = data ? Math.ceil(data.total / limit) : 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Contratos</h1>
          <p className="mt-2 text-sm text-gray-600">
            Gerencie os contratos jurídicos dos seus clientes
          </p>
        </div>
        <Button onClick={() => router.push('/contratos/novo')}>
          <Plus className="h-4 w-4 mr-2" />
          Novo Contrato
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <Input
            placeholder="Buscar por título, número ou cliente..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(0)
            }}
            className="pl-10"
          />
        </div>
        <Select
          value={statusFilter}
          onValueChange={(value) => {
            setStatusFilter(value)
            setPage(0)
          }}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos os status</SelectItem>
            <SelectItem value="rascunho">Rascunho</SelectItem>
            <SelectItem value="ativo">Ativo</SelectItem>
            <SelectItem value="suspenso">Suspenso</SelectItem>
            <SelectItem value="encerrado">Encerrado</SelectItem>
            <SelectItem value="cancelado">Cancelado</SelectItem>
            <SelectItem value="vencido">Vencido</SelectItem>
          </SelectContent>
        </Select>
        <Select
          value={tipoFilter}
          onValueChange={(value) => {
            setTipoFilter(value)
            setPage(0)
          }}
        >
          <SelectTrigger className="w-[220px]">
            <SelectValue placeholder="Tipo" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos os tipos</SelectItem>
            <SelectItem value="prestacao_servicos">Prestação de Serviços</SelectItem>
            <SelectItem value="honorarios_exito">Honorários de Êxito</SelectItem>
            <SelectItem value="misto">Misto</SelectItem>
            <SelectItem value="consultoria">Consultoria</SelectItem>
            <SelectItem value="contencioso">Contencioso</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <div className="rounded-lg border bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Número</TableHead>
              <TableHead>Título</TableHead>
              <TableHead>Cliente</TableHead>
              <TableHead>Tipo</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Valor Mensal</TableHead>
              <TableHead>Vencimento</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-gray-500">
                  Carregando contratos...
                </TableCell>
              </TableRow>
            ) : !data?.items?.length ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-gray-500">
                  Nenhum contrato encontrado
                </TableCell>
              </TableRow>
            ) : (
              data.items.map((contrato) => (
                <TableRow
                  key={contrato.id}
                  className="cursor-pointer hover:bg-gray-50"
                  onClick={() => router.push(`/contratos/${contrato.id}`)}
                >
                  <TableCell className="font-mono text-sm">
                    {contrato.numero_contrato}
                  </TableCell>
                  <TableCell className="font-medium max-w-[300px] truncate">
                    {contrato.titulo}
                  </TableCell>
                  <TableCell>{contrato.client_name || '-'}</TableCell>
                  <TableCell>
                    {tipoLabels[contrato.tipo] || contrato.tipo}
                  </TableCell>
                  <TableCell>
                    <Badge variant={statusVariants[contrato.status] || 'outline'}>
                      {statusLabels[contrato.status] || contrato.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    {formatCurrency(contrato.valor_mensal)}
                  </TableCell>
                  <TableCell>{formatDate(contrato.data_vencimento)}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t px-4 py-3">
            <p className="text-sm text-gray-600">
              {data?.total ?? 0} contratos no total
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="text-sm text-gray-600">
                Página {page + 1} de {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
