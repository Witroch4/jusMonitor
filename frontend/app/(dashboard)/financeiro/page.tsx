'use client'

import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '@/lib/api-client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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
import {
  DollarSign,
  TrendingUp,
  AlertTriangle,
  Clock,
  ChevronLeft,
  ChevronRight,
  Search,
} from 'lucide-react'
import type { FinanceiroDashboard, FaturaListResponse } from '@/types'

const faturaStatusLabels: Record<string, string> = {
  pendente: 'Pendente',
  paga: 'Paga',
  vencida: 'Vencida',
  cancelada: 'Cancelada',
  parcial: 'Parcial',
}

const faturaStatusVariants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  pendente: 'outline',
  paga: 'default',
  vencida: 'destructive',
  cancelada: 'secondary',
  parcial: 'secondary',
}

function formatCurrency(value?: number): string {
  if (value == null) return 'R$ 0,00'
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value)
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('pt-BR')
}

export default function FinanceiroPage() {
  const [dashboard, setDashboard] = useState<FinanceiroDashboard | null>(null)
  const [faturas, setFaturas] = useState<FaturaListResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [faturaStatus, setFaturaStatus] = useState('all')
  const [page, setPage] = useState(0)
  const limit = 15

  const fetchData = useCallback(async () => {
    setIsLoading(true)
    try {
      const params: Record<string, any> = {
        skip: page * limit,
        limit,
      }
      if (faturaStatus !== 'all') params.status = faturaStatus

      const [dashboardRes, faturasRes] = await Promise.all([
        apiClient.get('/financeiro/dashboard'),
        apiClient.get('/financeiro/faturas', { params }),
      ])
      setDashboard(dashboardRes.data)
      setFaturas(faturasRes.data)
    } catch (error) {
      console.error('Error fetching financial data:', error)
    } finally {
      setIsLoading(false)
    }
  }, [page, faturaStatus])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const totalPages = faturas ? Math.ceil(faturas.total / limit) : 0

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Financeiro</h1>
        <p className="mt-2 text-sm text-gray-600">
          Visão geral financeira e gestão de faturas
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-green-100 rounded-lg">
                <DollarSign className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Receita Recebida</p>
                <p className="text-2xl font-bold">
                  {formatCurrency(dashboard?.resumo?.total_recebido)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-100 rounded-lg">
                <TrendingUp className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">A Receber</p>
                <p className="text-2xl font-bold">
                  {formatCurrency(dashboard?.resumo?.total_a_receber)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-red-100 rounded-lg">
                <AlertTriangle className="h-6 w-6 text-red-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Em Atraso</p>
                <p className="text-2xl font-bold text-red-600">
                  {formatCurrency(dashboard?.resumo?.total_em_atraso)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-purple-100 rounded-lg">
                <Clock className="h-6 w-6 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Contratos Ativos</p>
                <p className="text-2xl font-bold">
                  {dashboard?.contratos_ativos ?? 0}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Faturas Table */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">Faturas</h2>
          <Select
            value={faturaStatus}
            onValueChange={(value) => {
              setFaturaStatus(value)
              setPage(0)
            }}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos os status</SelectItem>
              <SelectItem value="pendente">Pendente</SelectItem>
              <SelectItem value="paga">Paga</SelectItem>
              <SelectItem value="vencida">Vencida</SelectItem>
              <SelectItem value="cancelada">Cancelada</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="rounded-lg border bg-white">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Número</TableHead>
                <TableHead>Contrato</TableHead>
                <TableHead>Cliente</TableHead>
                <TableHead>Vencimento</TableHead>
                <TableHead className="text-right">Valor</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Pagamento</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-gray-500">
                    Carregando faturas...
                  </TableCell>
                </TableRow>
              ) : !faturas?.items?.length ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-gray-500">
                    Nenhuma fatura encontrada
                  </TableCell>
                </TableRow>
              ) : (
                faturas.items.map((fatura) => (
                  <TableRow key={fatura.id}>
                    <TableCell className="font-mono text-sm">{fatura.numero}</TableCell>
                    <TableCell>{fatura.contrato_titulo || '-'}</TableCell>
                    <TableCell>{fatura.client_name || '-'}</TableCell>
                    <TableCell>{formatDate(fatura.data_vencimento)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(fatura.valor)}</TableCell>
                    <TableCell>
                      <Badge variant={faturaStatusVariants[fatura.status] || 'outline'}>
                        {faturaStatusLabels[fatura.status] || fatura.status}
                      </Badge>
                    </TableCell>
                    <TableCell>{formatDate(fatura.data_pagamento)}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>

          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t px-4 py-3">
              <p className="text-sm text-gray-600">
                {faturas?.total ?? 0} faturas no total
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
    </div>
  )
}
