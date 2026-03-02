'use client'

import { useState, useEffect, useRef } from 'react'
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
  if (!num || num.length !== 20) return num || '-'
  return `${num.slice(0, 7)}-${num.slice(7, 9)}.${num.slice(9, 13)}.${num.slice(13, 14)}.${num.slice(14, 16)}.${num.slice(16)}`
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
  const [showRaw, setShowRaw] = useState(false)
  const proc = resultado.processo
  const ultimoConhecido = processoMonitorado?.movimentacoesConhecidas ?? 0
  const totalMovimentos = proc?.movimentos?.length ?? 0
  const novosCount = ultimoConhecido > 0 ? Math.max(0, totalMovimentos - ultimoConhecido) : 0

  return (
    <div className="space-y-4">
      <button
        onClick={onVoltar}
        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors mb-2"
      >
        <ArrowLeft className="h-4 w-4" />
        Voltar à lista
      </button>

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

export default function ProcessosPage() {
  const [mode, setMode] = useState<'datajud' | 'mni' | 'oab'>('datajud')

  // ── OAB Finder state ───────────────────────────────────────────────────
  const [oabNumero, setOabNumero] = useState('')
  const [oabUf, setOabUf] = useState('')
  const consultarOAB = useConsultarOAB()

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
            {mode === 'datajud' && processoAberto ? 'Detalhe do Processo' : 'Consulta de Processos'}
          </h1>
          <p className="mt-2 text-sm font-medium text-muted-foreground tracking-wide">
            DataJud (CNJ público) | MNI 2.2.2 (SOAP) | OAB Finder (web scraping)
          </p>
        </div>
        {mode === 'datajud' && !processoAberto && (
          <Button onClick={() => setMostraCadastro((v) => !v)}
            className="bg-primary hover:bg-primary/90 text-primary-foreground font-medium shadow-sm self-start md:self-auto">
            <Plus className="h-4 w-4 mr-2" />Adicionar processo
          </Button>
        )}
      </header>

      {/* Mode toggle */}
      <div className="flex gap-2 mb-6">
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
        <button onClick={() => setMode('oab')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${mode === 'oab' ? 'bg-primary text-primary-foreground border-primary'
            : 'bg-card text-muted-foreground border-border/40 hover:bg-muted/30'}`}>
          <Search className="h-4 w-4" />
          OAB Finder (web)
        </button>
      </div>

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

      {/* ── MNI Tab (inalterado) ─────────────────────────────────────────── */}
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

      {/* ── OAB Finder Tab ────────────────────────────────────────────── */}
      {mode === 'oab' && (
        <>
          <div className="border border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl p-6 bg-card mb-8">
            <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
              <div className="md:col-span-4">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1.5 block">Número OAB</label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input placeholder="50784" value={oabNumero}
                    onChange={(e) => setOabNumero(e.target.value)} className="pl-10 font-mono"
                    onKeyDown={(e) => { if (e.key === 'Enter' && oabNumero && oabUf) consultarOAB.mutate({ oabNumero, oabUf }) }} />
                </div>
              </div>
              <div className="md:col-span-3">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1.5 block">Estado (UF)</label>
                <Select value={oabUf} onValueChange={setOabUf}>
                  <SelectTrigger><SelectValue placeholder="Selecione o estado" /></SelectTrigger>
                  <SelectContent>
                    {['AC','AL','AM','AP','BA','CE','DF','ES','GO','MA','MG','MS','MT','PA','PB','PE','PI','PR','RJ','RN','RO','RR','RS','SC','SE','SP','TO']
                      .map((uf) => <SelectItem key={uf} value={uf}>{uf}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="md:col-span-3 flex items-end">
                <Button onClick={() => consultarOAB.mutate({ oabNumero, oabUf })}
                  disabled={!oabNumero || !oabUf || consultarOAB.isPending}
                  className="w-full bg-primary hover:bg-primary/90 text-primary-foreground font-medium shadow-sm">
                  {consultarOAB.isPending
                    ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Buscando...</>
                    : <><Search className="h-4 w-4 mr-2" />Buscar</>}
                </Button>
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-3">
              A busca pode demorar 5-15 segundos pois acessa o site do TRF1 em tempo real via web scraping.
            </p>
            {consultarOAB.isError && (
              <div className="mt-4 flex items-center gap-2 text-destructive bg-destructive/10 rounded-lg px-4 py-3">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span className="text-sm font-medium">{(consultarOAB.error as Error)?.message || 'Erro na busca'}</span>
              </div>
            )}
          </div>

          {/* Results */}
          {consultarOAB.data?.sucesso && consultarOAB.data.processos.length > 0 && (
            <div className="border border-border/40 rounded-xl overflow-hidden bg-card shadow-sm">
              <div className="px-5 py-3 bg-green-50 border-b border-green-200 flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-green-700" />
                <span className="text-sm font-medium text-green-800">{consultarOAB.data.mensagem}</span>
                <Badge variant="secondary" className="ml-auto font-mono text-xs">{consultarOAB.data.total} processos</Badge>
              </div>
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/30">
                    <TableHead className="text-xs uppercase pl-5">Processo</TableHead>
                    <TableHead className="text-xs uppercase">Classe / Assunto</TableHead>
                    <TableHead className="text-xs uppercase hidden md:table-cell">Partes</TableHead>
                    <TableHead className="text-xs uppercase hidden sm:table-cell">Última Movimentação</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {consultarOAB.data.processos.map((proc: OABProcessoResumo, i: number) => (
                    <TableRow key={i} className="hover:bg-muted/30">
                      <TableCell className="pl-5">
                        <span className="font-mono text-sm font-medium">{proc.numero}</span>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-col gap-0.5">
                          <span className="text-sm font-medium">{proc.classe || '-'}</span>
                          {proc.assunto && <span className="text-xs text-muted-foreground">{proc.assunto}</span>}
                        </div>
                      </TableCell>
                      <TableCell className="hidden md:table-cell">
                        <span className="text-sm max-w-xs truncate block">{proc.partes || '-'}</span>
                      </TableCell>
                      <TableCell className="hidden sm:table-cell">
                        <div className="flex flex-col gap-0.5">
                          <span className="text-xs text-muted-foreground">{proc.ultimaMovimentacao || '-'}</span>
                          {proc.dataUltimaMovimentacao && (
                            <span className="text-xs text-muted-foreground/70">{proc.dataUltimaMovimentacao}</span>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          {/* No results */}
          {consultarOAB.data?.sucesso && consultarOAB.data.processos.length === 0 && (
            <div className="border border-amber-200 rounded-xl bg-amber-50 p-6 text-center">
              <AlertCircle className="h-8 w-8 text-amber-500 mx-auto mb-3" />
              <p className="text-sm font-medium text-amber-800">{consultarOAB.data.mensagem}</p>
            </div>
          )}

          {/* API error (sucesso=false) */}
          {consultarOAB.data && !consultarOAB.data.sucesso && (
            <div className="border border-red-200 rounded-xl bg-red-50 p-6 text-center">
              <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-3" />
              <p className="text-sm font-medium text-red-800">{consultarOAB.data.mensagem}</p>
            </div>
          )}

          {/* Empty state */}
          {!consultarOAB.data && !consultarOAB.isPending && (
            <div className="border border-border/40 rounded-xl bg-card p-12 text-center">
              <Search className="h-12 w-12 text-muted-foreground/30 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-foreground mb-2">Buscar processos por OAB</h3>
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                Informe o número da OAB e o estado para buscar processos no TRF1 (Justiça Federal 1ª Região).
              </p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
