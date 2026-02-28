'use client'

import { use } from 'react'
import Link from 'next/link'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Skeleton } from '@/components/ui/skeleton'
import { PeticaoStatusBadge } from '@/components/peticoes/PeticaoStatusBadge'
import { PeticaoStatusTimeline } from '@/components/peticoes/PeticaoStatusTimeline'
import { PeticaoDocumentos } from '@/components/peticoes/PeticaoDocumentos'
import { PeticaoAnaliseIA } from '@/components/peticoes/PeticaoAnaliseIA'
import { usePeticao } from '@/hooks/api/usePeticoes'
import { TRIBUNAIS } from '@/lib/data/tribunais'
import { TIPO_PETICAO_LABELS } from '@/types/peticoes'
import { ChevronLeft } from 'lucide-react'

export default function PeticaoDetalhePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const { data: peticao, isLoading } = usePeticao(id)

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-6 w-96" />
        <Skeleton className="h-[400px] w-full rounded-xl" />
      </div>
    )
  }

  if (!peticao) {
    return (
      <div className="text-center py-16">
        <span className="material-symbols-outlined text-4xl text-muted-foreground/40 mb-3 block">search_off</span>
        <p className="text-lg font-medium text-foreground mb-1">Petição não encontrada</p>
        <p className="text-sm text-muted-foreground mb-4">A petição solicitada não existe ou foi removida.</p>
        <Link href="/peticoes" className="text-sm text-primary hover:underline">
          Voltar para Petições
        </Link>
      </div>
    )
  }

  const tribunal = TRIBUNAIS.find((t) => t.id === peticao.tribunalId)

  return (
    <div className="space-y-6">
      {/* Back + Header */}
      <div>
        <Link
          href="/peticoes"
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors mb-4"
        >
          <ChevronLeft className="h-4 w-4" />
          Voltar para Petições
        </Link>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="font-display text-2xl md:text-3xl font-bold text-foreground">
                {peticao.numeroProtocolo ?? 'Petição em Rascunho'}
              </h1>
              <PeticaoStatusBadge status={peticao.status} showIcon />
            </div>
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <span className="font-mono">{peticao.processoNumero}</span>
              <span>•</span>
              <span className="bg-muted/50 px-2 py-0.5 rounded text-xs font-medium">
                {tribunal?.nome ?? peticao.tribunalId}
              </span>
              <span>•</span>
              <span>{TIPO_PETICAO_LABELS[peticao.tipoPeticao]}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Rejection banner */}
      {peticao.status === 'rejeitada' && peticao.motivoRejeicao && (
        <div className="flex items-start gap-3 p-4 rounded-xl bg-destructive/5 border border-destructive/20">
          <span className="material-symbols-outlined text-destructive text-xl shrink-0">error</span>
          <div>
            <p className="text-sm font-semibold text-destructive mb-1">Motivo da Rejeição</p>
            <p className="text-sm text-destructive/80">{peticao.motivoRejeicao}</p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <Tabs defaultValue="detalhes">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="detalhes">Detalhes</TabsTrigger>
          <TabsTrigger value="documentos">
            Documentos ({peticao.documentos.length})
          </TabsTrigger>
          <TabsTrigger value="historico">Histórico</TabsTrigger>
        </TabsList>

        {/* Details Tab */}
        <TabsContent value="detalhes" className="mt-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              {/* Process info card */}
              <div className="bg-card border border-border rounded-xl p-6">
                <h3 className="text-xs font-bold text-muted-foreground tracking-widest uppercase mb-4">
                  Informações do Processo
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Tribunal</p>
                    <p className="text-sm font-medium">{tribunal?.nomeCompleto ?? peticao.tribunalId}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Sistema</p>
                    <p className="text-sm font-medium">{tribunal?.sistema ?? '—'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Número do Processo</p>
                    <p className="text-sm font-medium font-mono">{peticao.processoNumero}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Tipo de Petição</p>
                    <p className="text-sm font-medium">{TIPO_PETICAO_LABELS[peticao.tipoPeticao]}</p>
                  </div>
                  <div className="col-span-2">
                    <p className="text-xs text-muted-foreground mb-1">Assunto</p>
                    <p className="text-sm font-medium">{peticao.assunto}</p>
                  </div>
                  {peticao.descricao && (
                    <div className="col-span-2">
                      <p className="text-xs text-muted-foreground mb-1">Descrição</p>
                      <p className="text-sm text-muted-foreground">{peticao.descricao}</p>
                    </div>
                  )}
                  {peticao.protocoloRecibo && (
                    <div className="col-span-2">
                      <p className="text-xs text-muted-foreground mb-1">Recibo de Protocolo</p>
                      <p className="text-sm font-medium font-mono text-primary">{peticao.protocoloRecibo}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Dates card */}
              <div className="bg-card border border-border rounded-xl p-6">
                <h3 className="text-xs font-bold text-muted-foreground tracking-widest uppercase mb-4">
                  Datas
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Criado em</p>
                    <p className="text-sm font-medium">{new Date(peticao.criadoEm).toLocaleString('pt-BR')}</p>
                  </div>
                  {peticao.protocoladoEm && (
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Protocolado em</p>
                      <p className="text-sm font-medium">{new Date(peticao.protocoladoEm).toLocaleString('pt-BR')}</p>
                    </div>
                  )}
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Atualizado em</p>
                    <p className="text-sm font-medium">{new Date(peticao.atualizadoEm).toLocaleString('pt-BR')}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Right panel - AI Analysis */}
            <div>
              {peticao.analiseIA ? (
                <PeticaoAnaliseIA
                  analise={peticao.analiseIA}
                  isAnalyzing={false}
                  hasDocuments={peticao.documentos.length > 0}
                  onReanalisar={() => {}}
                />
              ) : (
                <div className="bg-card border border-border rounded-xl p-6 text-center">
                  <span className="material-symbols-outlined text-3xl text-muted-foreground/40 mb-2 block">analytics</span>
                  <p className="text-sm text-muted-foreground">Análise IA não disponível</p>
                </div>
              )}
            </div>
          </div>
        </TabsContent>

        {/* Documents Tab */}
        <TabsContent value="documentos" className="mt-6">
          <PeticaoDocumentos documentos={peticao.documentos} />
        </TabsContent>

        {/* History Tab */}
        <TabsContent value="historico" className="mt-6">
          <div className="bg-card border border-border rounded-xl p-6">
            <h3 className="text-xs font-bold text-muted-foreground tracking-widest uppercase mb-6">
              Linha do Tempo
            </h3>
            <PeticaoStatusTimeline peticaoId={peticao.id} />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
