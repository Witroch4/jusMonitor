'use client'

import { useState, useEffect, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api-client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  ChevronLeft,
  FileText,
  Download,
  CheckCircle,
  Clock,
  DollarSign,
  AlertTriangle,
} from 'lucide-react'
import type { Contrato, FaturaListResponse } from '@/types'

const statusLabels: Record<string, string> = {
  rascunho: 'Rascunho',
  ativo: 'Ativo',
  suspenso: 'Suspenso',
  encerrado: 'Encerrado',
  cancelado: 'Cancelado',
  vencido: 'Vencido',
}

const statusBadgeClasses: Record<string, string> = {
  rascunho: 'bg-gray-500 hover:bg-gray-600 text-white',
  ativo: 'bg-green-500 hover:bg-green-600 text-white',
  suspenso: 'bg-yellow-500 hover:bg-yellow-600 text-white',
  encerrado: 'bg-blue-500 hover:bg-blue-600 text-white',
  cancelado: 'bg-red-500 hover:bg-red-600 text-white',
  vencido: 'bg-orange-500 hover:bg-orange-600 text-white',
}

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

const tipoLabels: Record<string, string> = {
  prestacao_servicos: 'Prestação de Serviços',
  honorarios_exito: 'Honorários de Êxito',
  misto: 'Misto',
  consultoria: 'Consultoria',
  contencioso: 'Contencioso',
}

const indiceLabels: Record<string, string> = {
  igpm: 'IGP-M',
  ipca: 'IPCA',
  inpc: 'INPC',
  selic: 'SELIC',
  fixo: 'Fixo',
}

function formatCurrency(value?: number): string {
  if (value == null) return '-'
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value)
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('pt-BR')
}

export default function ContratoDetalhesPage() {
  const router = useRouter()
  const params = useParams()
  const id = params.id as string

  const [contrato, setContrato] = useState<Contrato | null>(null)
  const [faturas, setFaturas] = useState<FaturaListResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchContrato = useCallback(async () => {
    if (!id) return
    setIsLoading(true)
    try {
      const [contratoRes, faturasRes] = await Promise.all([
        apiClient.get<Contrato>(`/contratos/${id}`),
        apiClient.get<FaturaListResponse>(`/contratos/${id}/faturas`),
      ])
      setContrato(contratoRes.data)
      setFaturas(faturasRes.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao carregar contrato')
    } finally {
      setIsLoading(false)
    }
  }, [id])

  useEffect(() => {
    fetchContrato()
  }, [fetchContrato])

  if (isLoading) {
    return (
      <div className="flex-1 p-8 lg:p-12">
        <div className="text-center py-12 text-gray-500">Carregando contrato...</div>
      </div>
    )
  }

  if (error || !contrato) {
    return (
      <div className="flex-1 p-8 lg:p-12">
        <div className="text-center py-12">
          <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <p className="text-red-600">{error || 'Contrato não encontrado'}</p>
          <Button variant="outline" className="mt-4" onClick={() => router.push('/contratos')}>
            Voltar para Contratos
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 p-8 lg:p-12 overflow-y-auto bg-background transition-colors duration-300">
      <div className="mb-6 flex justify-between items-center">
        <button
          onClick={() => router.push('/contratos')}
          className="inline-flex items-center text-accent hover:text-accent/80 text-sm font-medium transition-colors"
        >
          <ChevronLeft className="w-4 h-4 mr-1" /> Voltar
        </button>
      </div>

      <header className="flex flex-col md:flex-row md:items-start justify-between mb-8 gap-4 border-b border-border/40 pb-6">
        <div>
          <div className="flex items-center gap-4 mb-2">
            <h1 className="text-3xl md:text-4xl font-serif font-bold text-foreground tracking-tight">
              {contrato.titulo}
            </h1>
          </div>
          <div className="flex items-center gap-3 mt-3">
            <Badge className={statusBadgeClasses[contrato.status] || 'bg-gray-500 text-white'}>
              {statusLabels[contrato.status] || contrato.status}
            </Badge>
            <span className="text-sm font-medium text-muted-foreground tracking-wide flex items-center gap-1.5">
              <FileText className="w-4 h-4" /> {contrato.numero_contrato}
            </span>
            <span className="text-sm text-muted-foreground">
              {tipoLabels[contrato.tipo] || contrato.tipo}
            </span>
          </div>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" className="border-border/60 shadow-sm hover:bg-muted/30">
            Editar Dados
          </Button>
          {contrato.documento_url && (
            <Button className="bg-primary hover:bg-primary/90 text-primary-foreground font-medium shadow-sm">
              <Download className="w-4 h-4 mr-2" />
              Baixar PDF
            </Button>
          )}
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Metadata */}
        <div className="lg:col-span-4 space-y-6">
          <Card className="border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)] transition-all duration-300">
            <CardHeader className="border-b border-border/40 pb-4 bg-muted/10">
              <CardTitle className="font-serif text-xl tracking-tight text-primary">Resumo Financeiro</CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <div className="space-y-6">
                <div>
                  <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-1">Valor Mensal (Fee)</p>
                  <p className="font-serif font-semibold text-3xl text-foreground">{formatCurrency(contrato.valor_mensal)}</p>
                </div>
                {contrato.valor_total && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase">Valor Total</p>
                    <p className="font-medium text-foreground mt-1">{formatCurrency(contrato.valor_total)}</p>
                  </div>
                )}
                {contrato.valor_entrada && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase">Entrada</p>
                    <p className="font-medium text-foreground mt-1">{formatCurrency(contrato.valor_entrada)}</p>
                  </div>
                )}
                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-border/40">
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase">Índice Reajuste</p>
                    <p className="font-medium text-foreground mt-1">
                      {contrato.indice_reajuste ? indiceLabels[contrato.indice_reajuste] || contrato.indice_reajuste : '-'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase">Término/Renovação</p>
                    <p className="font-medium text-foreground mt-1">{formatDate(contrato.data_vencimento)}</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)] transition-all duration-300">
            <CardHeader className="border-b border-border/40 pb-4 bg-muted/10">
              <CardTitle className="font-serif text-xl tracking-tight text-primary">Partes do Contrato</CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <div className="space-y-5">
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase">Contratante</p>
                  <p className="font-serif font-semibold text-lg text-foreground mt-1">
                    {contrato.client_name || '-'}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase">Advogado Responsável</p>
                  <p className="font-medium text-foreground mt-1">
                    {contrato.assigned_user_name || '-'}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase">Data de Assinatura</p>
                  <p className="font-medium text-foreground mt-1 flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5" /> {formatDate(contrato.data_assinatura)}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase">Data de Início</p>
                  <p className="font-medium text-foreground mt-1">{formatDate(contrato.data_inicio)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Clauses & Faturas */}
        <div className="lg:col-span-8 space-y-6">
          {contrato.clausulas && contrato.clausulas.length > 0 && (
            <Card className="border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)] transition-all duration-300">
              <CardHeader className="border-b border-border/40 pb-4 bg-muted/10">
                <CardTitle className="font-serif text-xl tracking-tight text-primary">Termos e Cláusulas Chave</CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <div className="space-y-6">
                  {contrato.clausulas.map((clausula, idx) => (
                    <div key={idx} className="p-5 border border-border/40 rounded-xl bg-card hover:bg-muted/30 transition-all duration-300 group shadow-sm">
                      <div className="flex items-start gap-4">
                        <div className="mt-0.5">
                          <CheckCircle className="w-5 h-5 text-accent" />
                        </div>
                        <div>
                          <h3 className="font-serif font-semibold text-lg text-foreground group-hover:text-primary transition-colors">{clausula.titulo}</h3>
                          <p className="text-sm font-medium text-muted-foreground mt-2 leading-relaxed">
                            {clausula.descricao}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Faturas */}
          <Card className="border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden">
            <CardHeader className="border-b border-border/40 pb-4 bg-muted/10">
              <div className="flex items-center justify-between">
                <CardTitle className="font-serif text-xl tracking-tight text-primary flex items-center gap-2">
                  <DollarSign className="w-5 h-5" />
                  Faturas
                </CardTitle>
                <span className="text-sm text-muted-foreground">
                  {faturas?.total || 0} faturas
                </span>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Número</TableHead>
                    <TableHead>Referência</TableHead>
                    <TableHead>Vencimento</TableHead>
                    <TableHead className="text-right">Valor</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Pagamento</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {!faturas?.items?.length ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center py-8 text-gray-500">
                        Nenhuma fatura encontrada
                      </TableCell>
                    </TableRow>
                  ) : (
                    faturas.items.map((fatura) => (
                      <TableRow key={fatura.id}>
                        <TableCell className="font-mono text-sm">{fatura.numero}</TableCell>
                        <TableCell>{fatura.referencia || '-'}</TableCell>
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
            </CardContent>
          </Card>

          {contrato.observacoes && (
            <Card className="border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden">
              <CardHeader className="border-b border-border/40 pb-4 bg-muted/10">
                <CardTitle className="font-serif text-xl tracking-tight text-primary">Observações</CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">{contrato.observacoes}</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
