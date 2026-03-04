'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
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
import {
  Search,
  Loader2,
  ChevronDown,
  ChevronRight,
  FileText,
  Users,
  Scale,
  Building,
  Activity,
  AlertCircle,
  CheckCircle2,
  Code2,
  Database,
  Shield,
  Plus,
  ArrowLeft,
  Clock,
  RefreshCw,
  Trash2,
  Bell,
  Tag,
  X,
  Briefcase,
  Paperclip,
  Download,
  Eye,
  FileSignature,
} from 'lucide-react'
import {
  useConsultarProcessoMNI,
  useConsultarOAB,
} from '@/hooks/api/useProcessos'
import type { DatajudResponse, DatajudMovimento } from '@/hooks/api/useProcessos'
import { useCertificados } from '@/hooks/api/useCertificados'
import { TRIBUNAIS } from '@/lib/data/tribunais'
import type {
  ProcessoConsultaResponse,
  ProcessoPolo,
  ProcessoMovimento,
  OABProcessoResumo,
} from '@/types/processos'
import {
  useProcessosMonitorados,
  type ProcessoMonitorado,
} from '@/hooks/useProcessosMonitorados'
import {
  useCasosOAB,
  useCasoDetalhe,
  useSyncCasos,
  useAdicionarCaso,
  useRemoverCaso,
  useMarcarCasoVisto,
  useSyncStatus,
} from '@/hooks/api/useCasosOAB'
import type { CasoOAB, CasoOABDetail } from '@/types/casos-oab'
import { useSyncProgress } from '@/hooks/useSyncProgress'
import { apiClient } from '@/lib/api-client'
import { normalizeProcessoNumero } from '@/lib/utils/processo'

/**
 * Fetch a pre-signed MinIO URL via the backend (authenticated) and open it.
 * Falls back to the raw URL in development if the presign request fails.
 */
async function downloadS3Document(rawUrl: string): Promise<void> {
  try {
    const { data } = await apiClient.get<{ presigned_url: string }>(
      `/storage/presign?url=${encodeURIComponent(rawUrl)}&redirect=false`,
    )
    window.open(data.presigned_url, '_blank', 'noopener,noreferrer')
  } catch (err) {
    console.error('presign_error', err)
    // Fallback: try direct URL (works only if bucket becomes public or credentials change)
    window.open(rawUrl, '_blank', 'noopener,noreferrer')
  }
}

const tribunaisMNI = TRIBUNAIS.filter((t) => t.suportaMNI && t.wsdlEndpoint)

function formatDate(dateStr?: string | null): string {
  if (!dateStr) return '-'
  if (/^\d{14}$/.test(dateStr)) {
    return `${dateStr.slice(6, 8)}/${dateStr.slice(4, 6)}/${dateStr.slice(0, 4)} ${dateStr.slice(8, 10)}:${dateStr.slice(10, 12)}`
  }
  try {
    return new Date(dateStr).toLocaleDateString('pt-BR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })
  } catch { return dateStr }
}

function formatRelativo(dateStr?: string | null): string {
  if (!dateStr) return 'Nunca consultado'
  const diff = Date.now() - new Date(dateStr).getTime()
  const h = Math.floor(diff / 3600000)
  if (h < 1) return 'Há poucos minutos'
  if (h < 24) return `Há ${h}h`
  const d = Math.floor(h / 24)
  return `Há ${d} dia${d > 1 ? 's' : ''}`
}

function formatCPF(doc?: string | null): string {
  if (!doc) return '-'
  if (doc.length === 11) return `${doc.slice(0, 3)}.${doc.slice(3, 6)}.${doc.slice(6, 9)}-${doc.slice(9)}`
  if (doc.length === 14) return `${doc.slice(0, 2)}.${doc.slice(2, 5)}.${doc.slice(5, 8)}/${doc.slice(8, 12)}-${doc.slice(12)}`
  return doc
}

function formatProcessoNumber(num?: string | null): string {
  if (!num) return '-'
  const normalized = normalizeProcessoNumero(num)
  return normalized || num
}

function Section({
  title, icon: Icon, badge, children, defaultOpen = true,
}: {
  title: string; icon: React.ElementType; badge?: string | number
  children: React.ReactNode; defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border border-border/40 rounded-xl overflow-hidden bg-card shadow-sm">
      <button onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-5 py-4 hover:bg-muted/20 transition-colors text-left">
        {open ? <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
          : <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />}
        <Icon className="h-5 w-5 text-primary shrink-0" />
        <span className="font-semibold text-foreground">{title}</span>
        {badge !== undefined && (
          <Badge variant="secondary" className="ml-auto font-mono text-xs">{badge}</Badge>
        )}
      </button>
      {open && <div className="px-5 pb-5 pt-0">{children}</div>}
    </div>
  )
}

function PoloCard({ polo }: { polo: ProcessoPolo }) {
  const colors: Record<string, string> = {
    AT: 'bg-blue-50 text-blue-700 border-blue-200', PA: 'bg-red-50 text-red-700 border-red-200',
    TC: 'bg-amber-50 text-amber-700 border-amber-200', FL: 'bg-purple-50 text-purple-700 border-purple-200',
  }
  const cls = colors[polo.polo] || 'bg-muted text-muted-foreground border-border'
  return (
    <div className={`rounded-lg border p-4 ${cls}`}>
      <div className="flex items-center gap-2 mb-3">
        <Badge variant="outline" className={cls}>{polo.polo}</Badge>
        <span className="font-semibold text-sm">{polo.poloLabel}</span>
        <span className="text-xs opacity-70">({polo.partes.length} parte{polo.partes.length !== 1 ? 's' : ''})</span>
      </div>
      <div className="space-y-3">
        {polo.partes.map((parte, i) => (
          <div key={i} className="bg-white/60 rounded-md p-3 border border-current/10">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-medium text-sm">{parte.nome}</span>
              {parte.tipoPessoa && <Badge variant="outline" className="text-xs capitalize">{parte.tipoPessoa}</Badge>}
            </div>
            {parte.documento && <div className="text-xs opacity-80">Doc: {formatCPF(parte.documento)}</div>}
            {parte.advogados.length > 0 && (
              <div className="mt-2 pl-3 border-l-2 border-current/20 space-y-1">
                {parte.advogados.map((adv, j) => (
                  <div key={j} className="text-xs">
                    <span className="font-medium">{adv.nome}</span>
                    {adv.inscricao && <span className="ml-2 opacity-70">OAB: {adv.inscricao}</span>}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function MovimentoItem({ dataHora, nome, codigo, complementos, index, orgaoJulgador, isNew }: {
  dataHora?: string; nome?: string; codigo?: number; complementos?: string[]; index: number; orgaoJulgador?: string; isNew?: boolean
}) {
  return (
    <div className="flex gap-3 group">
      <div className="flex flex-col items-center">
        <div className={`w-2.5 h-2.5 rounded-full mt-1.5 transition-colors ${
          isNew ? 'bg-primary animate-pulse' : 'bg-primary/60 group-hover:bg-primary'
        }`} />
        {index > 0 && <div className="w-px flex-1 bg-border/60" />}
      </div>
      <div className="pb-4 flex-1">
        <div className="flex items-baseline gap-2">
          <span className="text-xs font-mono text-muted-foreground">{formatDate(dataHora)}</span>
          {codigo && <Badge variant="outline" className="text-xs font-mono">#{codigo}</Badge>}
          {isNew && <Badge className="text-xs bg-primary/15 text-primary border-primary/30">Novo</Badge>}
        </div>
        <p className="text-sm font-medium text-foreground mt-0.5">{nome || 'Sem descrição'}</p>
        {orgaoJulgador && (
          <p className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1 opacity-80">
            <Building className="h-3 w-3" />
            {orgaoJulgador}
          </p>
        )}
        {complementos && complementos.length > 0 && (
          <div className="mt-1 text-xs text-muted-foreground">
            {complementos.map((c, i) => <span key={i} className="block">{c}</span>)}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── DataJud Detalhe ─────────────────────────────────────────────────────────

function DatajudDetalhe({
  resultado,
  processoMonitorado,
  onVoltar,
}: {
  resultado: DatajudResponse
  processoMonitorado?: ProcessoMonitorado
  onVoltar: () => void
}) {
  const router = useRouter()
  const [showRaw, setShowRaw] = useState(false)
  const proc = resultado.processo
  const ultimoConhecido = processoMonitorado?.movimentacoesConhecidas ?? 0
  const totalMovimentos = proc?.movimentos?.length ?? 0
  const novosCount = ultimoConhecido > 0 ? Math.max(0, totalMovimentos - ultimoConhecido) : 0

  const numeroParaPeticionar = normalizeProcessoNumero(
    processoMonitorado?.numero || proc?.numeroProcessoFormatado || ''
  ) || undefined

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-2">
        <button
          onClick={onVoltar}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Voltar à lista
        </button>
        {numeroParaPeticionar && (
          <Button
            size="sm"
            onClick={() => router.push(`/peticoes?processo=${encodeURIComponent(numeroParaPeticionar)}`)}
            className="gap-1.5"
          >
            <FileSignature className="h-4 w-4" />
            Peticionar
          </Button>
        )}
      </div>

      <div className={`flex items-center gap-3 rounded-xl px-5 py-4 ${resultado.sucesso ? 'bg-green-50 border border-green-200 text-green-800'
        : 'bg-red-50 border border-red-200 text-red-800'}`}>
        {resultado.sucesso ? <CheckCircle2 className="h-5 w-5 shrink-0" /> : <AlertCircle className="h-5 w-5 shrink-0" />}
        <div>
          <span className="font-semibold text-sm">{resultado.sucesso ? 'DataJud: consulta realizada' : 'Não encontrado no DataJud'}</span>
          {resultado.mensagem && <p className="text-xs mt-0.5 opacity-80">{resultado.mensagem}</p>}
        </div>
        {proc && (
          <div className="ml-auto flex items-center gap-2">
            <Badge variant="outline" className="font-mono text-xs">{proc.numeroProcessoFormatado}</Badge>
            {resultado.alias && <Badge variant="secondary" className="text-xs font-mono">{resultado.alias}</Badge>}
          </div>
        )}
      </div>

      {proc && resultado.sucesso && (
        <>
          <Section title="Dados Básicos" icon={FileText}>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div><span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Número</span>
                <p className="font-mono text-sm font-medium mt-0.5">{proc.numeroProcessoFormatado}</p></div>
              <div><span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Classe</span>
                <p className="text-sm font-medium mt-0.5">{proc.classe?.codigo ? `[${proc.classe.codigo}] ` : ''}{proc.classe?.nome || '-'}</p></div>
              <div><span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Tribunal / Grau</span>
                <p className="text-sm font-medium mt-0.5">{proc.tribunal} — {proc.grau}</p></div>
              <div><span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Data Ajuizamento</span>
                <p className="text-sm font-medium mt-0.5">{proc.dataAjuizamento || '-'}</p></div>
              <div><span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Sistema</span>
                <p className="text-sm font-medium mt-0.5">{proc.sistema || '-'}</p></div>
              <div><span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Formato</span>
                <p className="text-sm font-medium mt-0.5">{proc.formato || '-'}</p></div>
              <div><span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Nível Sigilo</span>
                <p className="text-sm font-medium mt-0.5">{proc.nivelSigilo ?? 0}</p></div>
              <div><span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Última Atualização</span>
                <p className="text-sm font-medium mt-0.5">{formatDate(proc.dataUltimaAtualizacao)}</p></div>
            </div>
            <div className="mt-3 flex items-center gap-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              <AlertCircle className="h-3.5 w-3.5 shrink-0" />
              DataJud não retorna partes (autor/réu). Para dados completos use MNI.
            </div>
          </Section>

          {proc.orgaoJulgador && (
            <Section title="Órgão Julgador" icon={Building}>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div><span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Código</span>
                  <p className="font-mono text-sm font-medium mt-0.5">{proc.orgaoJulgador.codigo || '-'}</p></div>
                <div><span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Nome</span>
                  <p className="text-sm font-medium mt-0.5">{proc.orgaoJulgador.nome || '-'}</p></div>
                <div><span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Município IBGE</span>
                  <p className="font-mono text-sm font-medium mt-0.5">{proc.orgaoJulgador.codigoMunicipioIbge || '-'}</p></div>
              </div>
            </Section>
          )}

          {proc.assuntos && proc.assuntos.length > 0 && (
            <Section title="Assuntos" icon={Scale} badge={proc.assuntos.length}>
              <Table>
                <TableHeader><TableRow>
                  <TableHead className="text-xs uppercase">Código</TableHead>
                  <TableHead className="text-xs uppercase">Descrição</TableHead>
                  <TableHead className="text-xs uppercase">Principal</TableHead>
                </TableRow></TableHeader>
                <TableBody>
                  {proc.assuntos.map((a, i) => (
                    <TableRow key={i}>
                      <TableCell className="font-mono text-sm">{a.codigo ?? '-'}</TableCell>
                      <TableCell className="text-sm">{a.nome || '-'}</TableCell>
                      <TableCell>{a.principal && <Badge className="bg-primary/10 text-primary text-xs">Principal</Badge>}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Section>
          )}

          {proc.movimentos && proc.movimentos.length > 0 && (
            <Section title="Movimentos" icon={Activity} badge={proc.movimentos.length} defaultOpen={proc.movimentos.length <= 20}>
              {novosCount > 0 && (
                <div className="mb-3 flex items-center gap-2 bg-primary/5 border border-primary/20 rounded-lg px-3 py-2">
                  <Bell className="h-3.5 w-3.5 text-primary" />
                  <span className="text-xs font-medium text-primary">
                    {novosCount} novo{novosCount > 1 ? 's' : ''} movimento{novosCount > 1 ? 's' : ''} desde a última visualização
                  </span>
                </div>
              )}
              <div className="max-h-125 overflow-y-auto pr-2">
                {proc.movimentos.map((mov: DatajudMovimento, i: number) => (
                  <MovimentoItem key={i} dataHora={mov.dataHora} nome={mov.nome}
                    codigo={mov.codigo} complementos={mov.complementos} orgaoJulgador={mov.orgaoJulgador}
                    index={i} isNew={novosCount > 0 && i < novosCount} />
                ))}
              </div>
            </Section>
          )}

          <Section title="Dados Brutos (DataJud)" icon={Code2} defaultOpen={false}>
            <Button variant="outline" size="sm" onClick={() => setShowRaw(!showRaw)} className="mb-3">
              {showRaw ? 'Ocultar JSON' : 'Mostrar JSON completo'}
            </Button>
            {showRaw && (
              <pre className="bg-muted/50 rounded-lg p-4 text-xs font-mono overflow-auto max-h-150 border border-border/40">
                {JSON.stringify(resultado, null, 2)}
              </pre>
            )}
          </Section>
        </>
      )}
    </div>
  )
}

// ─── DataJud Lista ────────────────────────────────────────────────────────────

function DatajudLista({
  processos,
  atualizando,
  onAbrir,
  onAtualizar,
  onRemover,
}: {
  processos: ProcessoMonitorado[]
  atualizando: Set<string>
  onAbrir: (p: ProcessoMonitorado) => void
  onAtualizar: (p: ProcessoMonitorado) => void
  onRemover: (id: string) => void
}) {
  const comNovas = processos.filter((p) => (p.novasMovimentacoes ?? 0) > 0)

  if (processos.length === 0) {
    return (
      <div className="border border-border/40 rounded-xl bg-card p-14 text-center">
        <Database className="h-12 w-12 text-muted-foreground/25 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-foreground mb-1">Nenhum processo monitorado</h3>
        <p className="text-sm text-muted-foreground max-w-xs mx-auto">
          Cadastre um número de processo para que ele seja monitorado automaticamente via DataJud.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {comNovas.length > 0 && (
        <div className="flex items-center gap-2 bg-primary/5 border border-primary/20 rounded-xl px-5 py-3">
          <Bell className="h-4 w-4 text-primary" />
          <span className="text-sm font-medium text-primary">
            {comNovas.length} processo{comNovas.length > 1 ? 's' : ''} com novos movimentos
          </span>
        </div>
      )}
      <div className="border border-border/40 rounded-xl overflow-hidden bg-card shadow-sm">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30">
              <TableHead className="text-xs uppercase pl-5">Processo</TableHead>
              <TableHead className="text-xs uppercase hidden md:table-cell">Classe</TableHead>
              <TableHead className="text-xs uppercase hidden md:table-cell">Tribunal</TableHead>
              <TableHead className="text-xs uppercase text-center">Movimentos</TableHead>
              <TableHead className="text-xs uppercase hidden sm:table-cell">Última consulta</TableHead>
              <TableHead className="text-xs uppercase text-right pr-4">Ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {processos.map((p) => {
              const proc = p.dados?.processo
              const total = proc?.movimentos?.length ?? 0
              const novas = p.novasMovimentacoes ?? 0
              const isUpdating = atualizando.has(p.id)
              const hasError = p.dados && !p.dados.sucesso
              return (
                <TableRow
                  key={p.id}
                  onClick={() => !isUpdating && onAbrir(p)}
                  className={`cursor-pointer transition-colors ${
                    novas > 0
                      ? 'bg-primary/3 hover:bg-primary/7 border-l-2 border-l-primary'
                      : 'hover:bg-muted/30'
                  }`}
                >
                  <TableCell className="pl-5">
                    <div className="flex flex-col gap-0.5">
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full shrink-0 ${
                          isUpdating ? 'bg-amber-400 animate-pulse'
                          : hasError ? 'bg-red-400'
                          : p.ultimaConsulta ? 'bg-emerald-400'
                          : 'bg-muted-foreground/30'
                        }`} />
                        <span className="font-mono text-sm font-medium">
                          {p.apelido || (proc?.numeroProcessoFormatado ?? formatProcessoNumber(p.numero))}
                        </span>
                      </div>
                      {p.origemPeticao && (
                        <Badge variant="outline" className="text-[10px] bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-400 dark:border-emerald-800 px-1.5 py-0 ml-1">
                          Protocolado
                        </Badge>
                      )}
                      {p.apelido && (
                        <span className="text-xs text-muted-foreground font-mono pl-4">
                          {formatProcessoNumber(p.numero)}
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-sm hidden md:table-cell">
                    {proc?.classe?.nome
                      ? <span className="text-xs text-muted-foreground">{proc.classe.codigo ? `[${proc.classe.codigo}] ` : ''}{proc.classe.nome}</span>
                      : <span className="text-xs text-muted-foreground/40">-</span>}
                  </TableCell>
                  <TableCell className="hidden md:table-cell">
                    {proc?.tribunal
                      ? <Badge variant="outline" className="text-xs font-mono">{proc.tribunal}{proc.grau ? ` — ${proc.grau}` : ''}</Badge>
                      : <span className="text-xs text-muted-foreground/40">-</span>}
                  </TableCell>
                  <TableCell className="text-center">
                    <div className="flex items-center justify-center gap-1.5">
                      {isUpdating
                        ? <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
                        : <>
                            <span className="text-sm font-medium tabular-nums">{total || '-'}</span>
                            {novas > 0 && (
                              <Badge className="text-xs bg-primary text-primary-foreground px-1.5 py-0 h-5 min-w-5 flex items-center justify-center">+{novas}</Badge>
                            )}
                          </>}
                    </div>
                  </TableCell>
                  <TableCell className="hidden sm:table-cell">
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                      <Clock className="h-3 w-3" />{formatRelativo(p.ultimaConsulta)}
                    </span>
                  </TableCell>
                  <TableCell className="text-right pr-4">
                    <div className="flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
                      <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-foreground"
                        onClick={() => onAtualizar(p)} disabled={isUpdating} title="Atualizar agora">
                        <RefreshCw className={`h-3.5 w-3.5 ${isUpdating ? 'animate-spin' : ''}`} />
                      </Button>
                      {!p.origemPeticao && (
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-destructive"
                          onClick={() => onRemover(p.id)} title="Remover">
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}

// ─── Formulário de Cadastro ───────────────────────────────────────────────────

function FormCadastro({ onCadastrar, onCancelar }: {
  onCadastrar: (numero: string, apelido?: string) => void
  onCancelar: () => void
}) {
  const [numero, setNumero] = useState('')
  const [apelido, setApelido] = useState('')
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!numero.trim()) return
    onCadastrar(numero.trim(), apelido.trim() || undefined)
  }
  return (
    <div className="border border-primary/20 rounded-xl bg-primary/2 p-5 mb-6 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <Plus className="h-4 w-4 text-primary" />
        <h3 className="font-semibold text-sm text-foreground">Cadastrar processo para monitorar</h3>
        <button onClick={onCancelar} className="ml-auto text-muted-foreground hover:text-foreground transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>
      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
          <div className="md:col-span-5">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">Número do Processo *</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input placeholder="0206561-11.2023.8.06.0001" value={numero}
                onChange={(e) => setNumero(e.target.value)} className="pl-10 font-mono" autoFocus />
            </div>
            <p className="text-xs text-muted-foreground mt-1">O tribunal será detectado automaticamente</p>
          </div>
          <div className="md:col-span-4">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">Apelido (opcional)</label>
            <div className="relative">
              <Tag className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input placeholder="ex: Trabalhista João Silva" value={apelido}
                onChange={(e) => setApelido(e.target.value)} className="pl-10" />
            </div>
          </div>
          <div className="md:col-span-3 flex items-end">
            <Button type="submit" disabled={!numero.trim()}
              className="flex-1 bg-primary hover:bg-primary/90 text-primary-foreground font-medium">
              <Plus className="h-4 w-4 mr-1.5" />Adicionar
            </Button>
          </div>
        </div>
      </form>
    </div>
  )
}

function MniResultado({ resultado }: { resultado: ProcessoConsultaResponse }) {
  const [showRaw, setShowRaw] = useState(false)
  return (
    <div className="space-y-4">
      <div className={`flex items-center gap-3 rounded-xl px-5 py-4 ${resultado.sucesso ? 'bg-green-50 border border-green-200 text-green-800'
        : 'bg-red-50 border border-red-200 text-red-800'}`}>
        {resultado.sucesso ? <CheckCircle2 className="h-5 w-5 shrink-0" /> : <AlertCircle className="h-5 w-5 shrink-0" />}
        <div>
          <span className="font-semibold text-sm">{resultado.sucesso ? 'MNI: consulta realizada com sucesso' : 'Falha na consulta MNI'}</span>
          {resultado.mensagem && <p className="text-xs mt-0.5 opacity-80">{resultado.mensagem}</p>}
        </div>
        {resultado.cabecalho?.numero && (
          <Badge variant="outline" className="ml-auto font-mono text-xs">{formatProcessoNumber(resultado.cabecalho.numero)}</Badge>
        )}
      </div>

      {resultado.sucesso && (
        <>
          {resultado.cabecalho && (
            <Section title="Dados Básicos" icon={FileText}>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div><span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Número</span>
                  <p className="font-mono text-sm font-medium mt-0.5">{formatProcessoNumber(resultado.cabecalho.numero)}</p></div>
                <div><span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Classe</span>
                  <p className="text-sm font-medium mt-0.5">{resultado.cabecalho.classeProcessual || '-'}</p></div>
                <div><span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Localidade</span>
                  <p className="text-sm font-medium mt-0.5">{resultado.cabecalho.codigoLocalidade || '-'}</p></div>
                <div><span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Data Ajuizamento</span>
                  <p className="text-sm font-medium mt-0.5">{formatDate(resultado.cabecalho.dataAjuizamento)}</p></div>
                {resultado.cabecalho.valorCausa != null && (
                  <div><span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Valor da Causa</span>
                    <p className="text-sm font-medium mt-0.5">
                      {resultado.cabecalho.valorCausa.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                    </p></div>
                )}
              </div>
            </Section>
          )}

          <Section title="Polos Processuais" icon={Users} badge={resultado.polos.length}>
            {resultado.polos.length === 0 ? (
              <p className="text-sm text-muted-foreground">Nenhum polo retornado</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {resultado.polos.map((polo: ProcessoPolo, i: number) => <PoloCard key={i} polo={polo} />)}
              </div>
            )}
          </Section>

          <Section title="Assuntos" icon={Scale} badge={resultado.assuntos.length}>
            {resultado.assuntos.length === 0 ? (
              <p className="text-sm text-muted-foreground">Nenhum assunto retornado</p>
            ) : (
              <Table>
                <TableHeader><TableRow>
                  <TableHead className="text-xs uppercase">Código Nacional</TableHead>
                  <TableHead className="text-xs uppercase">Descrição</TableHead>
                  <TableHead className="text-xs uppercase">Principal</TableHead>
                </TableRow></TableHeader>
                <TableBody>
                  {resultado.assuntos.map((a, i) => (
                    <TableRow key={i}>
                      <TableCell className="font-mono text-sm">{a.codigoNacional ?? a.codigoLocal ?? '-'}</TableCell>
                      <TableCell className="text-sm">{a.descricao || '-'}</TableCell>
                      <TableCell>{a.principal && <Badge className="bg-primary/10 text-primary text-xs">Principal</Badge>}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Section>

          {resultado.orgaoJulgador && (
            <Section title="Órgão Julgador" icon={Building}>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div><span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Código</span>
                  <p className="font-mono text-sm font-medium mt-0.5">{resultado.orgaoJulgador.codigoOrgao || '-'}</p></div>
                <div><span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Nome</span>
                  <p className="text-sm font-medium mt-0.5">{resultado.orgaoJulgador.nomeOrgao || '-'}</p></div>
                <div><span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Município IBGE</span>
                  <p className="font-mono text-sm font-medium mt-0.5">{resultado.orgaoJulgador.codigoMunicipioIbge || '-'}</p></div>
              </div>
            </Section>
          )}

          <Section title="Movimentos" icon={Activity} badge={resultado.movimentos.length}
            defaultOpen={resultado.movimentos.length <= 20}>
            {resultado.movimentos.length === 0 ? (
              <p className="text-sm text-muted-foreground">Nenhum movimento retornado</p>
            ) : (
              <div className="max-h-125 overflow-y-auto pr-2">
                {resultado.movimentos.map((mov: ProcessoMovimento, i: number) => (
                  <MovimentoItem key={i} dataHora={mov.dataHora ?? undefined} nome={mov.descricao ?? undefined}
                    codigo={mov.codigoNacional ?? undefined} complementos={mov.complementos ?? undefined} index={i} />
                ))}
              </div>
            )}
          </Section>

          <Section title="Resposta Completa (Debug MNI)" icon={Code2} defaultOpen={false}>
            <Button variant="outline" size="sm" onClick={() => setShowRaw(!showRaw)} className="mb-3">
              {showRaw ? 'Ocultar JSON' : 'Mostrar JSON completo'}
            </Button>
            {showRaw && (
              <pre className="bg-muted/50 rounded-lg p-4 text-xs font-mono overflow-auto max-h-150 border border-border/40">
                {JSON.stringify(resultado.raw, null, 2)}
              </pre>
            )}
          </Section>
        </>
      )}
    </div>
  )
}

// ─── Caso OAB Detalhe ─────────────────────────────────────────────────────────

function CasoOABDetalhe({
  caso,
  onVoltar,
}: {
  caso: CasoOABDetail
  onVoltar: () => void
}) {
  const router = useRouter()
  const partes = caso.partesJson || []
  const movimentacoes = caso.movimentacoesJson || []
  const documentos = caso.documentosJson || []

  // Group partes by polo
  const poloGroups: Record<string, typeof partes> = {}
  for (const p of partes) {
    const polo = p.polo || 'Outros'
    if (!poloGroups[polo]) poloGroups[polo] = []
    poloGroups[polo].push(p)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-2">
        <button
          onClick={onVoltar}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Voltar à lista
        </button>
        <Button
          size="sm"
          onClick={() => router.push(`/peticoes?processo=${encodeURIComponent(normalizeProcessoNumero(caso.numero))}`)}
          className="gap-1.5"
        >
          <FileSignature className="h-4 w-4" />
          Peticionar
        </Button>
      </div>

      <div className="flex items-center gap-3 rounded-xl px-5 py-4 bg-green-50 border border-green-200 text-green-800">
        <CheckCircle2 className="h-5 w-5 shrink-0" />
        <div>
          <span className="font-semibold text-sm">Processo encontrado via OAB</span>
          <p className="text-xs mt-0.5 opacity-80">
            Última sincronização: {caso.ultimaSincronizacao ? formatDate(caso.ultimaSincronizacao) : 'Nunca'}
          </p>
        </div>
        <Badge variant="outline" className="ml-auto font-mono text-xs">{formatProcessoNumber(caso.numero)}</Badge>
      </div>

      <Section title="Dados Básicos" icon={FileText}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Número</span>
            <p className="font-mono text-sm font-medium mt-0.5">{formatProcessoNumber(caso.numero)}</p>
          </div>
          <div>
            <span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Classe</span>
            <p className="text-sm font-medium mt-0.5">{caso.classe || '-'}</p>
          </div>
          <div>
            <span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Assunto</span>
            <p className="text-sm font-medium mt-0.5">{caso.assunto || '-'}</p>
          </div>
          <div>
            <span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Tribunal</span>
            <p className="text-sm font-medium mt-0.5">{caso.tribunal?.toUpperCase() || 'TRF1'}</p>
          </div>
        </div>
      </Section>

      {Object.keys(poloGroups).length > 0 && (
        <Section title="Partes" icon={Users} badge={partes.length}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(poloGroups).map(([polo, partesGrupo]) => {
              const colors: Record<string, string> = {
                'AUTOR': 'bg-blue-50 text-blue-700 border-blue-200',
                'RÉU': 'bg-red-50 text-red-700 border-red-200',
                'Ativo': 'bg-blue-50 text-blue-700 border-blue-200',
                'Passivo': 'bg-red-50 text-red-700 border-red-200',
              }
              const cls = colors[polo] || 'bg-muted text-muted-foreground border-border'
              return (
                <div key={polo} className={`rounded-lg border p-4 ${cls}`}>
                  <div className="flex items-center gap-2 mb-3">
                    <Badge variant="outline" className={cls}>{polo}</Badge>
                    <span className="text-xs opacity-70">({partesGrupo.length} parte{partesGrupo.length !== 1 ? 's' : ''})</span>
                  </div>
                  <div className="space-y-2">
                    {partesGrupo.map((parte, i) => (
                      <div key={i} className="bg-white/60 rounded-md p-2.5 border border-current/10">
                        <span className="font-medium text-sm">{parte.nome}</span>
                        {parte.papel && <span className="text-xs ml-2 opacity-70">{parte.papel}</span>}
                        {parte.oab && <span className="text-xs ml-2 opacity-70">OAB: {parte.oab}</span>}
                        {parte.documento && <span className="text-xs ml-2 opacity-70">Doc: {parte.documento}</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </Section>
      )}

      {movimentacoes.length > 0 && (
        <Section title="Movimentações" icon={Activity} badge={movimentacoes.length} defaultOpen={movimentacoes.length <= 30}>
          <div className="max-h-125 overflow-y-auto pr-2">
            {movimentacoes.map((mov, i) => (
              <div key={i} className="flex gap-3 group">
                <div className="flex flex-col items-center">
                  <div className="w-2.5 h-2.5 rounded-full mt-1.5 bg-primary/60 group-hover:bg-primary transition-colors" />
                  {i < movimentacoes.length - 1 && <div className="w-px flex-1 bg-border/60" />}
                </div>
                <div className="pb-4 flex-1">
                  <p className="text-sm font-medium text-foreground">{mov.descricao || 'Sem descrição'}</p>
                  {mov.documento_vinculado && (
                    <p className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1">
                      <Paperclip className="h-3 w-3" />
                      {mov.documento_vinculado}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {documentos.length > 0 && (
        <Section title="Documentos / Anexos" icon={Paperclip} badge={documentos.length}>
          <div className="border border-border/40 rounded-lg overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/30">
                  <TableHead className="text-xs uppercase pl-4">Nome</TableHead>
                  <TableHead className="text-xs uppercase">Tipo</TableHead>
                  <TableHead className="text-xs uppercase text-right pr-4">Ação</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {documentos.map((doc, i) => {
                  const url = doc.s3Url || doc.s3_url || ''
                  const tamanho = doc.tamanhoBytes || doc.tamanho_bytes
                  return (
                    <TableRow key={i} className="hover:bg-muted/20">
                      <TableCell className="pl-4">
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                          <span className="text-sm font-medium">{doc.nome || `Documento ${i + 1}`}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="text-xs text-muted-foreground">
                          {doc.tipo || 'PDF'}
                          {tamanho ? ` (${(tamanho / 1024).toFixed(0)} KB)` : ''}
                        </span>
                      </TableCell>
                      <TableCell className="text-right pr-4">
                        {url ? (
                          <button
                            type="button"
                            onClick={() => downloadS3Document(url)}
                            className="inline-flex items-center gap-1.5 text-xs font-medium text-primary hover:text-primary/80 transition-colors"
                          >
                            <Download className="h-3.5 w-3.5" />
                            Baixar
                          </button>
                        ) : (
                          <span className="text-xs text-muted-foreground">Indisponível</span>
                        )}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>
        </Section>
      )}
    </div>
  )
}

// ─── Casos OAB Lista ──────────────────────────────────────────────────────────

function CasosOABLista({
  casos,
  onAbrir,
  onRemover,
}: {
  casos: CasoOAB[]
  onAbrir: (c: CasoOAB) => void
  onRemover: (id: string) => void
}) {
  if (casos.length === 0) return null

  const comNovas = casos.filter((c) => c.novasMovimentacoes > 0)

  return (
    <div className="space-y-3">
      {comNovas.length > 0 && (
        <div className="flex items-center gap-2 bg-primary/5 border border-primary/20 rounded-xl px-5 py-3">
          <Bell className="h-4 w-4 text-primary" />
          <span className="text-sm font-medium text-primary">
            {comNovas.length} processo{comNovas.length > 1 ? 's' : ''} com novas movimentações
          </span>
        </div>
      )}
      <div className="border border-border/40 rounded-xl overflow-hidden bg-card shadow-sm">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30">
              <TableHead className="text-xs uppercase pl-5">Processo</TableHead>
              <TableHead className="text-xs uppercase hidden md:table-cell">Classe / Assunto</TableHead>
              <TableHead className="text-xs uppercase hidden lg:table-cell">Partes</TableHead>
              <TableHead className="text-xs uppercase text-center">Movimentações</TableHead>
              <TableHead className="text-xs uppercase text-center hidden sm:table-cell">Docs</TableHead>
              <TableHead className="text-xs uppercase hidden sm:table-cell">Última Sync</TableHead>
              <TableHead className="text-xs uppercase text-right pr-4">Ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {casos.map((c) => (
              <TableRow
                key={c.id}
                onClick={() => onAbrir(c)}
                className={`cursor-pointer transition-colors ${
                  c.novasMovimentacoes > 0
                    ? 'bg-primary/3 hover:bg-primary/7 border-l-2 border-l-primary'
                    : 'hover:bg-muted/30'
                }`}
              >
                <TableCell className="pl-5">
                  <span className="font-mono text-sm font-medium">{formatProcessoNumber(c.numero)}</span>
                </TableCell>
                <TableCell className="hidden md:table-cell">
                  <div className="flex flex-col gap-0.5">
                    <span className="text-sm font-medium">{c.classe || '-'}</span>
                    {c.assunto && <span className="text-xs text-muted-foreground">{c.assunto}</span>}
                  </div>
                </TableCell>
                <TableCell className="hidden lg:table-cell">
                  <span className="text-sm max-w-xs truncate block">{c.partesResumo || '-'}</span>
                </TableCell>
                <TableCell className="text-center">
                  <div className="flex items-center justify-center gap-1.5">
                    <span className="text-sm font-medium tabular-nums">{c.totalMovimentacoes || '-'}</span>
                    {c.novasMovimentacoes > 0 && (
                      <Badge className="text-xs bg-primary text-primary-foreground px-1.5 py-0 h-5 min-w-5 flex items-center justify-center">
                        +{c.novasMovimentacoes}
                      </Badge>
                    )}
                  </div>
                </TableCell>
                <TableCell className="text-center hidden sm:table-cell">
                  <span className="text-sm tabular-nums">{c.totalDocumentos || '-'}</span>
                </TableCell>
                <TableCell className="hidden sm:table-cell">
                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                    <Clock className="h-3 w-3" />{formatRelativo(c.ultimaSincronizacao)}
                  </span>
                </TableCell>
                <TableCell className="text-right pr-4">
                  <div className="flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
                    <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-foreground"
                      onClick={() => onAbrir(c)} title="Ver detalhes">
                      <Eye className="h-3.5 w-3.5" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-destructive"
                      onClick={() => onRemover(c.id)} title="Remover">
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}

export default function ProcessosPage() {
  const [mode, setMode] = useState<'casos' | 'datajud' | 'mni'>('casos')

  // ── Casos OAB state ──────────────────────────────────────────────────
  const { data: casosData, isLoading: casosLoading } = useCasosOAB()
  const { data: syncStatusData } = useSyncStatus()
  const syncMutation = useSyncCasos()
  const { progress: pipelineProgress } = useSyncProgress()
  const adicionarCasoMut = useAdicionarCaso()
  const removerCasoMut = useRemoverCaso()
  const marcarVistoMut = useMarcarCasoVisto()

  const [casoAbertoId, setCasoAbertoId] = useState<string | null>(null)
  const { data: casoDetalhe } = useCasoDetalhe(casoAbertoId)
  const [mostraCadastroCaso, setMostraCadastroCaso] = useState(false)
  const [numeroCasoNovo, setNumeroCasoNovo] = useState('')

  const casos = casosData?.items || []

  const handleAdicionarCaso = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!numeroCasoNovo.trim()) return
    try {
      await adicionarCasoMut.mutateAsync(numeroCasoNovo.trim())
      setNumeroCasoNovo('')
      setMostraCadastroCaso(false)
    } catch { /* handled by RQ */ }
  }

  const handleAbrirCaso = (c: CasoOAB) => {
    setCasoAbertoId(c.id)
    if (c.novasMovimentacoes > 0) marcarVistoMut.mutate(c.id)
  }

  // ── MNI state ────────────────────────────────────────────────────────────
  const [numeroProcessoMNI, setNumeroProcessoMNI] = useState('')
  const [tribunalId, setTribunalId] = useState('')
  const [certificadoId, setCertificadoId] = useState('')
  const consultarMNI = useConsultarProcessoMNI()
  const { data: certificados, isLoading: loadingCerts } = useCertificados()
  const certsValidos = certificados?.filter((c) => c.status === 'valido' || c.status === 'expirando') || []
  const canSubmitMNI = !!(numeroProcessoMNI && tribunalId && tribunalId !== 'auto' && certificadoId)

  // ── Processos monitorados (do banco) ────────────────────────────────────
  const { processos, adicionar, remover, consultarProcesso: consultarProcessoDB, marcarVisto, precisamAtualizar } = useProcessosMonitorados()

  const [mostraCadastro, setMostraCadastro] = useState(false)
  const [processoAberto, setProcessoAberto] = useState<ProcessoMonitorado | null>(null)
  const [atualizando, setAtualizando] = useState<Set<string>>(new Set())
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const consultarProcesso = async (p: ProcessoMonitorado) => {
    setAtualizando((prev) => new Set(prev).add(p.id))
    try {
      await consultarProcessoDB(p.id)
    } catch { /* silently ignore */ } finally {
      setAtualizando((prev) => { const next = new Set(prev); next.delete(p.id); return next })
    }
  }

  useEffect(() => {
    const rodarPolling = () => precisamAtualizar().forEach((p) => consultarProcesso(p))
    rodarPolling()
    const DOZE_HORAS = 12 * 60 * 60 * 1000
    pollingRef.current = setInterval(rodarPolling, DOZE_HORAS)
    return () => { if (pollingRef.current) clearInterval(pollingRef.current) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleCadastrar = async (numero: string, apelido?: string) => {
    try {
      const id = await adicionar(numero, apelido)
      setMostraCadastro(false)
      // Trigger DataJud consultation for the new process
      setAtualizando((prev) => new Set(prev).add(id))
      try {
        await consultarProcessoDB(id)
      } catch { /* silently ignore */ } finally {
        setAtualizando((prev) => { const next = new Set(prev); next.delete(id); return next })
      }
    } catch { /* API error handled by React Query */ }
  }

  const processoAtualizado = processoAberto
    ? (processos.find((p) => p.id === processoAberto.id) ?? processoAberto)
    : null

  return (
    <div className="flex-1 p-8 lg:p-12 overflow-y-auto bg-background transition-colors duration-300">
      <header className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4 border-b border-border/40 pb-6">
        <div>
          <h1 className="text-3xl md:text-4xl font-serif font-bold text-foreground tracking-tight">
            {mode === 'casos' && casoAbertoId ? 'Detalhe do Processo' : mode === 'datajud' && processoAberto ? 'Detalhe do Processo' : 'Consulta de Processos'}
          </h1>
          <p className="mt-2 text-sm font-medium text-muted-foreground tracking-wide">
            Casos (scrapy automático) | DataJud (CNJ público) | MNI 2.2.2 (SOAP)
          </p>
        </div>
        {mode === 'casos' && !casoAbertoId && (
          <div className="flex items-center gap-2 self-start md:self-auto">
            <Button onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending || syncStatusData?.status === 'running'}
              variant="outline" className="font-medium">
              <RefreshCw className={`h-4 w-4 mr-2 ${
                syncMutation.isPending || syncStatusData?.status === 'running' ? 'animate-spin' : ''
              }`} />
              {syncMutation.isPending
                ? 'Aguarde...'
                : syncStatusData?.status === 'running'
                  ? 'Sincronizando...'
                  : 'Atualizar'}
            </Button>
            <Button onClick={() => setMostraCadastroCaso((v) => !v)}
              className="bg-primary hover:bg-primary/90 text-primary-foreground font-medium shadow-sm">
              <Plus className="h-4 w-4 mr-2" />Adicionar processo
            </Button>
          </div>
        )}
        {mode === 'datajud' && !processoAberto && (
          <Button onClick={() => setMostraCadastro((v) => !v)}
            className="bg-primary hover:bg-primary/90 text-primary-foreground font-medium shadow-sm self-start md:self-auto">
            <Plus className="h-4 w-4 mr-2" />Adicionar processo
          </Button>
        )}
      </header>

      {/* Mode toggle */}
      <div className="flex gap-2 mb-6">
        <button onClick={() => { setMode('casos'); setCasoAbertoId(null) }}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${mode === 'casos' ? 'bg-primary text-primary-foreground border-primary'
            : 'bg-card text-muted-foreground border-border/40 hover:bg-muted/30'}`}>
          <Briefcase className="h-4 w-4" />
          Casos
          {casos.some((c) => c.novasMovimentacoes > 0) && mode !== 'casos' && (
            <span className="w-2 h-2 rounded-full bg-primary ml-1" />
          )}
        </button>
        <button onClick={() => { setMode('datajud'); setProcessoAberto(null) }}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${mode === 'datajud' ? 'bg-primary text-primary-foreground border-primary'
            : 'bg-card text-muted-foreground border-border/40 hover:bg-muted/30'}`}>
          <Database className="h-4 w-4" />
          DataJud (público)
          {processos.some((p) => (p.novasMovimentacoes ?? 0) > 0) && mode !== 'datajud' && (
            <span className="w-2 h-2 rounded-full bg-primary ml-1" />
          )}
        </button>
        <button onClick={() => setMode('mni')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${mode === 'mni' ? 'bg-primary text-primary-foreground border-primary'
            : 'bg-card text-muted-foreground border-border/40 hover:bg-muted/30'}`}>
          <Shield className="h-4 w-4" />
          MNI 2.2.2 (certificado)
        </button>
      </div>

      {/* ── Casos Tab ──────────────────────────────────────────────────── */}
      {mode === 'casos' && (
        <>
          {casoAbertoId && casoDetalhe ? (
            <CasoOABDetalhe
              caso={casoDetalhe}
              onVoltar={() => setCasoAbertoId(null)}
            />
          ) : (
            <>
              {/* Sync status bar */}
              {syncStatusData && syncStatusData.status !== 'no_oab' && (
                <div className={`mb-4 rounded-lg border px-4 py-3 ${
                  syncStatusData.status === 'running'
                    ? 'bg-blue-50 border-blue-200 text-blue-700'
                    : syncStatusData.status === 'error'
                      ? 'bg-red-50 border-red-200 text-red-700'
                      : 'bg-muted/30 border-border text-muted-foreground'
                }`}>
                  <div className="flex items-center gap-3 text-xs">
                    {syncStatusData.status === 'running'
                      ? <Loader2 className="h-3.5 w-3.5 animate-spin shrink-0" />
                      : <Clock className="h-3.5 w-3.5 shrink-0" />}
                    <span className="font-medium">
                      {syncStatusData.status === 'running'
                        ? (pipelineProgress?.faseLabel || 'Sincronizando processos em segundo plano…')
                        : syncStatusData.status === 'error'
                          ? 'Erro na última sincronização'
                          : `Última sincronização: ${syncStatusData.ultimoSync ? formatRelativo(syncStatusData.ultimoSync) : 'Nunca'}`}
                      {syncStatusData.status !== 'running' && syncStatusData.totalProcessos > 0 && ` — ${syncStatusData.totalProcessos} processos`}
                    </span>
                    {syncStatusData.oabNumero && (
                      <Badge variant="outline" className="text-xs font-mono ml-auto">
                        OAB/{syncStatusData.oabUf} {syncStatusData.oabNumero}
                      </Badge>
                    )}
                  </div>

                  {/* Pipeline progress details */}
                  {syncStatusData.status === 'running' && pipelineProgress && (
                    <div className="mt-2 space-y-1.5">
                      {/* Tribunal + process context */}
                      <div className="flex items-center gap-2 text-[11px] text-blue-600/80">
                        {pipelineProgress.tribunal && (
                          <Badge variant="secondary" className="text-[10px] px-1.5 py-0 font-mono uppercase">
                            {pipelineProgress.tribunal}
                          </Badge>
                        )}
                        {pipelineProgress.numero && (
                          <span className="font-mono">{pipelineProgress.numero}</span>
                        )}
                        {pipelineProgress.processoIndex != null && pipelineProgress.processoTotal != null && (
                          <span>
                            Processo {pipelineProgress.processoIndex}/{pipelineProgress.processoTotal}
                          </span>
                        )}
                        {pipelineProgress.docIndex != null && pipelineProgress.docTotal != null && (
                          <span>
                            • Doc {pipelineProgress.docIndex}/{pipelineProgress.docTotal}
                          </span>
                        )}
                      </div>

                      {/* Progress bar */}
                      {pipelineProgress.processoTotal != null && pipelineProgress.processoTotal > 0 && (
                        <div className="h-1.5 rounded-full bg-blue-200 overflow-hidden">
                          <div
                            className="h-full rounded-full bg-blue-500 transition-all duration-500"
                            style={{
                              width: `${Math.min(100, ((pipelineProgress.processoIndex || 0) / pipelineProgress.processoTotal) * 100)}%`,
                            }}
                          />
                        </div>
                      )}
                    </div>
                  )}

                  {/* Completed summary */}
                  {pipelineProgress?.fase === 'completed' && (
                    <div className="mt-2 flex items-center gap-3 text-[11px] text-green-700">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      <span>
                        {pipelineProgress.totalProcessos || 0} processos
                        {pipelineProgress.novosProcessos ? ` (${pipelineProgress.novosProcessos} novos)` : ''}
                        {pipelineProgress.docsBaixados ? ` • ${pipelineProgress.docsBaixados} documentos baixados` : ''}
                      </span>
                    </div>
                  )}
                </div>
              )}

              {/* Sync result feedback */}
              {syncMutation.data && (
                <div className={`flex items-center gap-2 rounded-xl px-5 py-3 mb-4 ${
                  syncMutation.data.queued
                    ? 'bg-blue-50 border border-blue-200 text-blue-800'
                    : syncMutation.data.sucesso
                      ? 'bg-green-50 border border-green-200 text-green-800'
                      : 'bg-amber-50 border border-amber-200 text-amber-800'
                }`}>
                  {syncMutation.data.queued
                    ? <Loader2 className="h-4 w-4 animate-spin" />
                    : syncMutation.data.sucesso
                      ? <CheckCircle2 className="h-4 w-4" />
                      : <AlertCircle className="h-4 w-4" />}
                  <span className="text-sm font-medium">{syncMutation.data.mensagem}</span>
                </div>
              )}

              {/* Add process form */}
              {mostraCadastroCaso && (
                <div className="border border-primary/20 rounded-xl bg-primary/2 p-5 mb-6 shadow-sm">
                  <div className="flex items-center gap-2 mb-4">
                    <Plus className="h-4 w-4 text-primary" />
                    <h3 className="font-semibold text-sm text-foreground">Adicionar processo manualmente</h3>
                    <button onClick={() => setMostraCadastroCaso(false)} className="ml-auto text-muted-foreground hover:text-foreground transition-colors">
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                  <form onSubmit={handleAdicionarCaso}>
                    <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
                      <div className="md:col-span-8">
                        <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">Número do Processo (CNJ) *</label>
                        <div className="relative">
                          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                          <Input placeholder="1013264-53.2025.4.01.3904" value={numeroCasoNovo}
                            onChange={(e) => setNumeroCasoNovo(e.target.value)} className="pl-10 font-mono" autoFocus />
                        </div>
                      </div>
                      <div className="md:col-span-4 flex items-end">
                        <Button type="submit" disabled={!numeroCasoNovo.trim() || adicionarCasoMut.isPending}
                          className="flex-1 bg-primary hover:bg-primary/90 text-primary-foreground font-medium">
                          {adicionarCasoMut.isPending
                            ? <><Loader2 className="h-4 w-4 mr-1.5 animate-spin" />Adicionando...</>
                            : <><Plus className="h-4 w-4 mr-1.5" />Adicionar</>}
                        </Button>
                      </div>
                    </div>
                  </form>
                </div>
              )}

              {/* Stats */}
              {casos.length > 0 && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
                  <div className="border border-border/40 rounded-xl bg-card px-4 py-3">
                    <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Processos</p>
                    <p className="text-2xl font-bold font-mono mt-1 text-foreground">{casos.length}</p>
                  </div>
                  <div className="border border-border/40 rounded-xl bg-card px-4 py-3">
                    <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Movimentações</p>
                    <p className="text-2xl font-bold font-mono mt-1 text-foreground">
                      {casos.reduce((a, c) => a + c.totalMovimentacoes, 0) || '-'}
                    </p>
                  </div>
                  <div className="border border-border/40 rounded-xl bg-card px-4 py-3">
                    <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Novas</p>
                    <p className="text-2xl font-bold font-mono mt-1 text-primary">
                      {casos.reduce((a, c) => a + c.novasMovimentacoes, 0) || '-'}
                    </p>
                  </div>
                  <div className="border border-border/40 rounded-xl bg-card px-4 py-3">
                    <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Documentos</p>
                    <p className="text-2xl font-bold font-mono mt-1 text-foreground">
                      {casos.reduce((a, c) => a + c.totalDocumentos, 0) || '-'}
                    </p>
                  </div>
                </div>
              )}

              {/* Loading */}
              {casosLoading && (
                <div className="flex items-center justify-center p-12 text-muted-foreground">
                  <Loader2 className="h-6 w-6 animate-spin mr-3" />
                  <span className="text-sm">Carregando casos...</span>
                </div>
              )}

              {/* List */}
              {!casosLoading && casos.length > 0 && (
                <CasosOABLista
                  casos={casos}
                  onAbrir={handleAbrirCaso}
                  onRemover={(id) => removerCasoMut.mutate(id)}
                />
              )}

              {/* Empty state */}
              {!casosLoading && casos.length === 0 && (
                <div className="border border-border/40 rounded-xl bg-card p-14 text-center">
                  <Briefcase className="h-12 w-12 text-muted-foreground/25 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-foreground mb-2">Nenhum caso encontrado</h3>
                  {syncStatusData?.status === 'no_oab' ? (
                    <p className="text-sm text-muted-foreground max-w-md mx-auto">
                      Configure seu número OAB no <a href="/configuracoes" className="text-primary underline">perfil</a> para buscar processos automaticamente.
                    </p>
                  ) : (
                    <div className="space-y-3">
                      <p className="text-sm text-muted-foreground max-w-md mx-auto">
                        Seus processos serão sincronizados automaticamente 2x por dia.
                        Clique em <strong>Atualizar</strong> para buscar agora.
                      </p>
                      <Button onClick={() => syncMutation.mutate()}
                        disabled={syncMutation.isPending || syncStatusData?.status === 'running'}
                        className="bg-primary hover:bg-primary/90 text-primary-foreground font-medium">
                        <RefreshCw className={`h-4 w-4 mr-2 ${
                          syncMutation.isPending || syncStatusData?.status === 'running' ? 'animate-spin' : ''
                        }`} />
                        {syncMutation.isPending
                          ? 'Aguarde...'
                          : syncStatusData?.status === 'running'
                            ? 'Sincronizando...'
                            : 'Sincronizar agora'}
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </>
      )}

      {/* ── DataJud Tab ─────────────────────────────────────────────────── */}
      {mode === 'datajud' && (
        <>
          {processoAberto && processoAtualizado?.dados ? (
            <DatajudDetalhe
              resultado={processoAtualizado.dados}
              processoMonitorado={processoAtualizado}
              onVoltar={() => setProcessoAberto(null)}
            />
          ) : (
            <>
              {mostraCadastro && (
                <FormCadastro onCadastrar={handleCadastrar} onCancelar={() => setMostraCadastro(false)} />
              )}
              {processos.length > 0 && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
                  <div className="border border-border/40 rounded-xl bg-card px-4 py-3">
                    <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Monitorados</p>
                    <p className="text-2xl font-bold font-mono mt-1 text-foreground">{processos.length}</p>
                  </div>
                  <div className="border border-border/40 rounded-xl bg-card px-4 py-3">
                    <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Atualizando</p>
                    <p className="text-2xl font-bold font-mono mt-1 text-amber-500">{atualizando.size || '-'}</p>
                  </div>
                  <div className="border border-border/40 rounded-xl bg-card px-4 py-3">
                    <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Novos movimentos</p>
                    <p className="text-2xl font-bold font-mono mt-1 text-primary">
                      {processos.reduce((a, p) => a + (p.novasMovimentacoes ?? 0), 0) || '-'}
                    </p>
                  </div>
                  <div className="border border-border/40 rounded-xl bg-card px-4 py-3">
                    <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Próx. atualização</p>
                    <p className="text-sm font-medium mt-1 text-muted-foreground">~12h</p>
                  </div>
                </div>
              )}
              <DatajudLista
                processos={processos}
                atualizando={atualizando}
                onAbrir={(p) => { marcarVisto(p.id); setProcessoAberto({ ...p }) }}
                onAtualizar={consultarProcesso}
                onRemover={remover}
              />
            </>
          )}
        </>
      )}

      {/* ── MNI Tab ──────────────────────────────────────────────────────── */}
      {mode === 'mni' && (
        <>
          <div className="border border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl p-6 bg-card mb-8">
            <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
              <div className="md:col-span-4">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1.5 block">Número do Processo</label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input placeholder="0206561-11.2023.8.06.0001" value={numeroProcessoMNI}
                    onChange={(e) => setNumeroProcessoMNI(e.target.value)} className="pl-10 font-mono"
                    onKeyDown={(e) => { if (e.key === 'Enter' && canSubmitMNI) consultarMNI.mutate({ numeroProcesso: numeroProcessoMNI, tribunalId, certificadoId }) }} />
                </div>
              </div>
              <div className="md:col-span-3">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1.5 block">Tribunal</label>
                <Select value={tribunalId} onValueChange={setTribunalId}>
                  <SelectTrigger><SelectValue placeholder="Selecione o tribunal" /></SelectTrigger>
                  <SelectContent>
                    {tribunaisMNI.map((t) => <SelectItem key={t.id} value={t.id}>{t.nome} ({t.sistema})</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="md:col-span-3">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1.5 block">Certificado Digital</label>
                <Select value={certificadoId} onValueChange={setCertificadoId}>
                  <SelectTrigger><SelectValue placeholder={loadingCerts ? 'Carregando...' : 'Selecione o certificado'} /></SelectTrigger>
                  <SelectContent>
                    {certsValidos.map((c) => <SelectItem key={c.id} value={c.id}>{c.titularNome} ({c.titularCpfCnpj})</SelectItem>)}
                    {certsValidos.length === 0 && !loadingCerts && <div className="px-3 py-2 text-sm text-muted-foreground">Nenhum certificado válido</div>}
                  </SelectContent>
                </Select>
              </div>
              <div className="md:col-span-2 flex items-end">
                <Button onClick={() => consultarMNI.mutate({ numeroProcesso: numeroProcessoMNI, tribunalId, certificadoId })}
                  disabled={!canSubmitMNI || consultarMNI.isPending}
                  className="w-full bg-primary hover:bg-primary/90 text-primary-foreground font-medium shadow-sm">
                  {consultarMNI.isPending
                    ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Consultando...</>
                    : <><Search className="h-4 w-4 mr-2" />Consultar</>}
                </Button>
              </div>
            </div>
            {consultarMNI.isError && (
              <div className="mt-4 flex items-center gap-2 text-destructive bg-destructive/10 rounded-lg px-4 py-3">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span className="text-sm font-medium">{(consultarMNI.error as Error)?.message || 'Erro ao consultar processo'}</span>
              </div>
            )}
          </div>
          {consultarMNI.data ? (
            <MniResultado resultado={consultarMNI.data} />
          ) : !consultarMNI.isPending && (
            <div className="border border-border/40 rounded-xl bg-card p-12 text-center">
              <Shield className="h-12 w-12 text-muted-foreground/30 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-foreground mb-2">Consulte via MNI 2.2.2</h3>
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                Informe o número, tribunal e certificado para consultar dados direto do sistema judicial via SOAP.
              </p>
            </div>
          )}
        </>
      )}

    </div>
  )
}
