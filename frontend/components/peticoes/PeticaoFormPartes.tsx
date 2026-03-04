'use client'

import { useState, useCallback, useRef } from 'react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { Polo, Pessoa, Advogado } from '@/types/peticoes'
import { VINCULACOES_BY_POLO } from '@/types/peticoes'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Plus, Trash2, User, Building2, UserCheck, Pencil, Loader2, CheckCircle2, AlertCircle, Zap } from 'lucide-react'
import { useProfile } from '@/hooks/api/useProfile'

const TEMPLATES_POLO_PASSIVO = [
  {
    id: 'ms-oab',
    label: 'Mandado de Segurança — OAB (Exame da Ordem)',
    description: 'OAB Conselho Federal, Presidente da OAB, FGV e Presidente da FGV',
    partes: [
      {
        nome: 'ORDEM DOS ADVOGADOS DO BRASIL CONSELHO FEDERAL',
        tipoPessoa: 'juridica' as const,
        cnpj: '33.205.451/0001-14',
        tipoVinculacao: 'TERCEIRO INTERESSADO',
        orgaoPublico: false,
      },
      {
        nome: 'PRESIDENTE DO CONSELHO FEDERAL DA ORDEM DOS ADVOGADOS DO BRASIL',
        tipoPessoa: 'entidade' as const,
        tipoVinculacao: 'IMPETRADO',
      },
      {
        nome: 'FUNDACAO GETULIO VARGAS',
        tipoPessoa: 'juridica' as const,
        cnpj: '33.641.663/0001-44',
        tipoVinculacao: 'TERCEIRO INTERESSADO',
        orgaoPublico: false,
      },
      {
        nome: 'PRESIDENTE DA FUNDAÇÃO GETÚLIO VARGAS',
        tipoPessoa: 'entidade' as const,
        tipoVinculacao: 'IMPETRADO',
      },
    ] as Pessoa[],
  },
]

interface CnpjState {
  loading: boolean
  error: string | null
  found: boolean
}

interface Props {
  polos: Polo[]
  onChange: (polos: Polo[]) => void
}

const POLO_LABELS: Record<string, string> = {
  AT: 'Polo Ativo (Autor)',
  PA: 'Polo Passivo (Réu)',
  TC: 'Terceiro',
}

function emptyPessoa(): Pessoa {
  return { nome: '', tipoPessoa: 'fisica' }
}

function emptyAdvogado(): Advogado {
  return { nome: '', inscricaoOAB: '', intimacao: true }
}

function defaultPolos(): Polo[] {
  return [
    { polo: 'AT', partes: [emptyPessoa()], advogados: [emptyAdvogado()] },
    { polo: 'PA', partes: [emptyPessoa()], advogados: [] },
  ]
}

function formatCpf(cpf: string): string {
  const d = cpf.replace(/\D/g, '')
  if (d.length === 11) return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6, 9)}-${d.slice(9)}`
  return cpf
}

function formatCnpj(cnpj: string): string {
  const d = cnpj.replace(/\D/g, '')
  if (d.length === 14)
    return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}`
  return cnpj
}

export function PeticaoFormPartes({ polos, onChange }: Props) {
  const [expanded, setExpanded] = useState(true)
  const [templateDialogOpen, setTemplateDialogOpen] = useState(false)
  const [templatePoloIdx, setTemplatePoloIdx] = useState<number | null>(null)
  const { data: profile } = useProfile()

  // CNPJ lookup state per parte: key = `${poloIdx}-${parteIdx}`
  const [cnpjStates, setCnpjStates] = useState<Record<string, CnpjState>>({})
  const timerRef = useRef<Record<string, ReturnType<typeof setTimeout>>>({})

  const currentPolos = polos.length > 0 ? polos : defaultPolos()

  // Build read-only advogado label from profile (like PJe card)
  const profileOab = profile?.oab_number && profile?.oab_state
    ? `${profile.oab_state}${profile.oab_number}`
    : undefined
  const profileCpfFormatted = profile?.cpf_formatted || (profile?.cpf ? formatCpf(profile.cpf) : undefined)
  const profileLabel = profile
    ? [
        profile.full_name.toUpperCase(),
        'registrado(a) civilmente como',
        profile.full_name.toUpperCase(),
        profileOab ? `- OAB ${profileOab}` : '',
        profileCpfFormatted ? `- CPF: ${profileCpfFormatted}` : '',
        '(ADVOGADO)',
      ]
        .filter(Boolean)
        .join(' ')
    : null

  const updatePolo = (poloIdx: number, updates: Partial<Polo>) => {
    const updated = currentPolos.map((p, i) => (i === poloIdx ? { ...p, ...updates } : p))
    onChange(updated)
  }

  const updateParte = (poloIdx: number, parteIdx: number, updates: Partial<Pessoa>) => {
    const newPartes = currentPolos[poloIdx].partes.map((p, i) =>
      i === parteIdx ? { ...p, ...updates } : p
    )
    updatePolo(poloIdx, { partes: newPartes })
  }

  const addParte = (poloIdx: number) => {
    const newPartes = [...currentPolos[poloIdx].partes, emptyPessoa()]
    updatePolo(poloIdx, { partes: newPartes })
  }

  const removeParte = (poloIdx: number, parteIdx: number) => {
    if (currentPolos[poloIdx].partes.length <= 1) return
    const newPartes = currentPolos[poloIdx].partes.filter((_, i) => i !== parteIdx)
    updatePolo(poloIdx, { partes: newPartes })
  }

  const updateAdvogado = (poloIdx: number, advIdx: number, updates: Partial<Advogado>) => {
    const newAdvs = currentPolos[poloIdx].advogados.map((a, i) =>
      i === advIdx ? { ...a, ...updates } : a
    )
    updatePolo(poloIdx, { advogados: newAdvs })
  }

  const addAdvogado = (poloIdx: number) => {
    const newAdvs = [...currentPolos[poloIdx].advogados, emptyAdvogado()]
    updatePolo(poloIdx, { advogados: newAdvs })
  }

  const removeAdvogado = (poloIdx: number, advIdx: number) => {
    const newAdvs = currentPolos[poloIdx].advogados.filter((_, i) => i !== advIdx)
    updatePolo(poloIdx, { advogados: newAdvs })
  }

  const setCnpjState = (key: string, state: Partial<CnpjState>) =>
    setCnpjStates((prev) => ({ ...prev, [key]: { ...{ loading: false, error: null, found: false }, ...prev[key], ...state } }))

  // Fetch CNPJ data from BrasilAPI and auto-fill
  const lookupCnpj = useCallback(
    async (poloIdx: number, parteIdx: number, cnpjDigits: string) => {
      const key = `${poloIdx}-${parteIdx}`
      setCnpjState(key, { loading: true, error: null, found: false })
      try {
        const res = await fetch(`https://brasilapi.com.br/api/cnpj/v1/${cnpjDigits}`)
        if (!res.ok) {
          let msg = 'Erro ao consultar CNPJ'
          try {
            const errData = await res.json()
            if (errData?.message) msg = errData.message
            else if (res.status === 404) msg = 'CNPJ não encontrado'
          } catch {
            if (res.status === 404) msg = 'CNPJ não encontrado'
          }
          setCnpjState(key, { loading: false, error: msg, found: false })
          return
        }
        const data = await res.json()
        const nome = data.razao_social || data.nome_fantasia || ''
        const nomeFantasia = data.nome_fantasia && data.nome_fantasia !== nome ? data.nome_fantasia : undefined
        updateParte(poloIdx, parteIdx, {
          nome,
          nomeFantasia,
          cnpj: formatCnpj(cnpjDigits),
        })
        setCnpjState(key, { loading: false, error: null, found: true })
      } catch {
        setCnpjState(key, { loading: false, error: 'Falha na consulta do CNPJ. Verifique sua conexão.', found: false })
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [currentPolos]
  )

  const handleCnpjChange = (poloIdx: number, parteIdx: number, value: string) => {
    updateParte(poloIdx, parteIdx, { cnpj: value })
    const key = `${poloIdx}-${parteIdx}`
    // Reset state on change
    setCnpjState(key, { loading: false, error: null, found: false })
    // Clear pending timer
    if (timerRef.current[key]) clearTimeout(timerRef.current[key])
    const digits = value.replace(/\D/g, '')
    if (digits.length === 14) {
      timerRef.current[key] = setTimeout(() => lookupCnpj(poloIdx, parteIdx, digits), 400)
    }
  }

  const openTemplateDialog = (poloIdx: number) => {
    setTemplatePoloIdx(poloIdx)
    setTemplateDialogOpen(true)
  }

  const applyTemplate = (template: typeof TEMPLATES_POLO_PASSIVO[number]) => {
    if (templatePoloIdx === null) return
    updatePolo(templatePoloIdx, { partes: [...template.partes] })
    setTemplateDialogOpen(false)
    setTemplatePoloIdx(null)
  }

  return (
    <div className="bg-card border border-border rounded-2xl p-8 shadow-sm">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between"
      >
        <h2 className="font-display text-xl font-semibold text-foreground flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">groups</span>
          Partes do Processo
        </h2>
        <span className="material-symbols-outlined text-muted-foreground transition-transform" style={{ transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)' }}>
          expand_more
        </span>
      </button>

      {expanded && (
        <div className="mt-6 space-y-8">
          {currentPolos.map((polo, poloIdx) => (
            <div key={poloIdx} className="space-y-4">
              <div className="flex items-center gap-2 pb-2 border-b border-border">
                <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ${
                  polo.polo === 'AT'
                    ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400'
                    : polo.polo === 'PA'
                    ? 'bg-orange-500/10 text-orange-600 dark:text-orange-400'
                    : 'bg-gray-500/10 text-gray-600 dark:text-gray-400'
                }`}>
                  {POLO_LABELS[polo.polo] || polo.polo}
                </span>
              </div>

              {/* Partes */}
              {polo.partes.map((parte, parteIdx) => {
                const cnpjKey = `${poloIdx}-${parteIdx}`
                const cnpjState = cnpjStates[cnpjKey]
                return (
                  <div key={parteIdx} className="pl-4 border-l-2 border-muted space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                        {parte.tipoPessoa === 'juridica' ? (
                          <Building2 className="h-3.5 w-3.5" />
                        ) : (
                          <User className="h-3.5 w-3.5" />
                        )}
                        Parte {parteIdx + 1}
                      </span>
                      {polo.partes.length > 1 && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => removeParte(poloIdx, parteIdx)}
                          className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      )}
                    </div>

                    {/* Tipo de Vinculação */}
                    <div>
                      <Label className="text-xs mb-1 block">Tipo da Parte (Vinculação)</Label>
                      <Select
                        value={parte.tipoVinculacao || ''}
                        onValueChange={(v) => updateParte(poloIdx, parteIdx, { tipoVinculacao: v })}
                      >
                        <SelectTrigger className="h-9 text-sm">
                          <SelectValue placeholder="Selecione..." />
                        </SelectTrigger>
                        <SelectContent>
                          {(VINCULACOES_BY_POLO[polo.polo] || []).map((v) => (
                            <SelectItem key={v} value={v}>{v}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      <div className="md:col-span-2">
                        <Label className="text-xs mb-1 block">Nome</Label>
                        <Input
                          value={parte.nome}
                          onChange={(e) => updateParte(poloIdx, parteIdx, { nome: e.target.value })}
                          placeholder="Nome completo"
                          className="h-9 text-sm"
                        />
                      </div>
                      <div>
                        <Label className="text-xs mb-1 block">Tipo de Pessoa</Label>
                        <Select
                          value={parte.tipoPessoa}
                          onValueChange={(v) => updateParte(poloIdx, parteIdx, { tipoPessoa: v as Pessoa['tipoPessoa'], orgaoPublico: false })}
                        >
                          <SelectTrigger className="h-9 text-sm">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="fisica">Pessoa Física</SelectItem>
                            <SelectItem value="juridica">Pessoa Jurídica</SelectItem>
                            <SelectItem value="entidade">Ente ou Entidade</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    {/* Órgão Público (jurídica ou entidade) */}
                    {(parte.tipoPessoa === 'juridica' || parte.tipoPessoa === 'entidade') && (
                      <div className="flex items-center gap-4">
                        <span className="text-xs text-muted-foreground">Órgão Público?</span>
                        <div className="flex items-center gap-4">
                          <label className="flex items-center gap-1.5 cursor-pointer text-xs">
                            <input
                              type="radio"
                              name={`orgaoPublico-${poloIdx}-${parteIdx}`}
                              checked={parte.orgaoPublico === true}
                              onChange={() => updateParte(poloIdx, parteIdx, { orgaoPublico: true })}
                              className="accent-primary"
                            />
                            Sim
                          </label>
                          <label className="flex items-center gap-1.5 cursor-pointer text-xs">
                            <input
                              type="radio"
                              name={`orgaoPublico-${poloIdx}-${parteIdx}`}
                              checked={!parte.orgaoPublico}
                              onChange={() => updateParte(poloIdx, parteIdx, { orgaoPublico: false })}
                              className="accent-primary"
                            />
                            Não
                          </label>
                        </div>
                      </div>
                    )}

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {parte.tipoPessoa === 'juridica' || parte.tipoPessoa === 'entidade' ? (
                        <div className="md:col-span-2 space-y-2">
                          <Label className="text-xs mb-1 block">CNPJ</Label>
                          {!parte.semCnpj && (
                            <div className="relative">
                              <Input
                                value={parte.cnpj || ''}
                                onChange={(e) => handleCnpjChange(poloIdx, parteIdx, e.target.value)}
                                placeholder="00.000.000/0001-00"
                                className={`h-9 text-sm font-mono pr-8 ${
                                  cnpjState?.error ? 'border-destructive focus-visible:ring-destructive/30' : ''
                                }`}
                                maxLength={18}
                              />
                              {cnpjState?.loading && (
                                <Loader2 className="absolute right-2.5 top-2.5 h-4 w-4 animate-spin text-muted-foreground" />
                              )}
                              {cnpjState?.found && !cnpjState.loading && (
                                <CheckCircle2 className="absolute right-2.5 top-2.5 h-4 w-4 text-emerald-500" />
                              )}
                              {cnpjState?.error && !cnpjState.loading && (
                                <AlertCircle className="absolute right-2.5 top-2.5 h-4 w-4 text-destructive" />
                              )}
                            </div>
                          )}
                          {cnpjState?.error && !parte.semCnpj && (
                            <p className="text-[11px] text-destructive">{cnpjState.error}</p>
                          )}
                          {cnpjState?.found && !parte.semCnpj && (
                            <p className="text-[11px] text-emerald-600">Empresa encontrada — dados preenchidos automaticamente</p>
                          )}
                          <label className="flex items-center gap-2 cursor-pointer">
                            <Checkbox
                              checked={!!parte.semCnpj}
                              onCheckedChange={(checked) => updateParte(poloIdx, parteIdx, { semCnpj: !!checked, cnpj: checked ? '' : parte.cnpj })}
                            />
                            <span className="text-xs text-muted-foreground">Não possui este documento</span>
                          </label>
                        </div>
                      ) : (
                        <>
                          <div>
                            <Label className="text-xs mb-1 block">CPF</Label>
                            {!parte.semCpf && (
                              <Input
                                value={parte.cpf || ''}
                                onChange={(e) => updateParte(poloIdx, parteIdx, { cpf: e.target.value })}
                                placeholder="000.000.000-00"
                                className="h-9 text-sm font-mono"
                              />
                            )}
                            <label className="flex items-center gap-2 cursor-pointer mt-1.5">
                              <Checkbox
                                checked={!!parte.semCpf}
                                onCheckedChange={(checked) => updateParte(poloIdx, parteIdx, { semCpf: !!checked, cpf: checked ? '' : parte.cpf })}
                              />
                              <span className="text-xs text-muted-foreground">Não possui este documento</span>
                            </label>
                          </div>
                          <div>
                            <Label className="text-xs mb-1 block">Sexo</Label>
                            <Select
                              value={parte.sexo || ''}
                              onValueChange={(v) => updateParte(poloIdx, parteIdx, { sexo: v as 'M' | 'F' })}
                            >
                              <SelectTrigger className="h-9 text-sm">
                                <SelectValue placeholder="Selecionar..." />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="M">Masculino</SelectItem>
                                <SelectItem value="F">Feminino</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </>
                      )}
                      {/* Nome Fantasia — só para jurídica */}
                      {parte.tipoPessoa === 'juridica' && (
                        <div className="md:col-span-2">
                          <Label className="text-xs mb-1 block">Nome Fantasia</Label>
                          <Input
                            value={parte.nomeFantasia || ''}
                            onChange={(e) => updateParte(poloIdx, parteIdx, { nomeFantasia: e.target.value })}
                            placeholder="Nome fantasia"
                            className="h-9 text-sm"
                          />
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}

              <div className="flex items-center gap-2 ml-4">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => addParte(poloIdx)}
                  className="h-8 text-xs"
                >
                  <Plus className="h-3.5 w-3.5 mr-1" />
                  Adicionar Parte
                </Button>
                {polo.polo === 'PA' && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => openTemplateDialog(poloIdx)}
                    className="h-8 text-xs border-amber-500/40 text-amber-600 hover:bg-amber-500/10 dark:text-amber-400"
                  >
                    <Zap className="h-3.5 w-3.5 mr-1" />
                    Adição Rápida
                  </Button>
                )}
              </div>

              {/* Advogados */}
              {polo.advogados.length > 0 && (
                <div className="mt-3 space-y-3">
                  <span className="text-xs font-medium text-muted-foreground flex items-center gap-1 ml-4">
                    <UserCheck className="h-3.5 w-3.5" />
                    Advogado(s)
                  </span>
                  {polo.advogados.map((adv, advIdx) => {
                    const isProfileAdvogado = polo.polo === 'AT' && advIdx === 0 && profile

                    if (isProfileAdvogado) {
                      return (
                        <div key={advIdx} className="pl-4 border-l-2 border-primary/30">
                          <div className="flex items-start justify-between gap-2">
                            <p className="text-sm font-medium text-foreground leading-snug">
                              {profileLabel}
                            </p>
                            <a
                              href="/configuracoes"
                              target="_blank"
                              rel="noopener noreferrer"
                              className="shrink-0 text-muted-foreground hover:text-primary transition-colors"
                              title="Editar perfil"
                            >
                              <Pencil className="h-3.5 w-3.5" />
                            </a>
                          </div>
                          <button
                            type="button"
                            onClick={() => updateAdvogado(poloIdx, advIdx, { intimacao: !adv.intimacao })}
                            className={`mt-2 flex items-center gap-2 px-3 py-2 rounded-lg border text-xs font-medium w-fit transition-colors ${
                              adv.intimacao
                                ? 'border-primary/60 bg-primary/8 text-primary'
                                : 'border-border bg-transparent text-muted-foreground hover:border-primary/30'
                            }`}
                          >
                            <span
                              className={`w-4 h-4 rounded border-2 flex items-center justify-center shrink-0 transition-colors ${
                                adv.intimacao ? 'border-primary bg-primary' : 'border-muted-foreground'
                              }`}
                            >
                              {adv.intimacao && (
                                <span className="material-symbols-outlined text-[11px] text-primary-foreground leading-none">
                                  check
                                </span>
                              )}
                            </span>
                            Receber intimações eletrônicas
                          </button>
                        </div>
                      )
                    }

                    return (
                      <div key={advIdx} className="pl-4 border-l-2 border-primary/20 space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-muted-foreground">Advogado {advIdx + 1}</span>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => removeAdvogado(poloIdx, advIdx)}
                            className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                          <div>
                            <Label className="text-xs mb-1 block">Nome</Label>
                            <Input
                              value={adv.nome}
                              onChange={(e) => updateAdvogado(poloIdx, advIdx, { nome: e.target.value })}
                              placeholder="Nome do advogado"
                              className="h-9 text-sm"
                            />
                          </div>
                          <div>
                            <Label className="text-xs mb-1 block">OAB</Label>
                            <Input
                              value={adv.inscricaoOAB}
                              onChange={(e) => updateAdvogado(poloIdx, advIdx, { inscricaoOAB: e.target.value })}
                              placeholder="CE12345"
                              className="h-9 text-sm font-mono"
                            />
                          </div>
                          <div>
                            <Label className="text-xs mb-1 block">CPF</Label>
                            <Input
                              value={adv.cpf || ''}
                              onChange={(e) => updateAdvogado(poloIdx, advIdx, { cpf: e.target.value })}
                              placeholder="000.000.000-00"
                              className="h-9 text-sm font-mono"
                            />
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => updateAdvogado(poloIdx, advIdx, { intimacao: !adv.intimacao })}
                          className={`ml-0 mt-1 flex items-center gap-2 px-3 py-2 rounded-lg border text-xs font-medium w-fit transition-colors ${
                            adv.intimacao
                              ? 'border-primary/60 bg-primary/8 text-primary'
                              : 'border-border bg-transparent text-muted-foreground hover:border-primary/30'
                          }`}
                        >
                          <span
                            className={`w-4 h-4 rounded border-2 flex items-center justify-center shrink-0 transition-colors ${
                              adv.intimacao ? 'border-primary bg-primary' : 'border-muted-foreground'
                            }`}
                          >
                            {adv.intimacao && (
                              <span className="material-symbols-outlined text-[11px] text-primary-foreground leading-none">
                                check
                              </span>
                            )}
                          </span>
                          Receber intimações eletrônicas
                        </button>
                      </div>
                    )
                  })}
                </div>
              )}

              {polo.polo === 'AT' && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => addAdvogado(poloIdx)}
                  className="ml-4 h-8 text-xs"
                >
                  <Plus className="h-3.5 w-3.5 mr-1" />
                  Adicionar Advogado
                </Button>
              )}
            </div>
          ))}
        </div>
      )}

      <Dialog open={templateDialogOpen} onOpenChange={setTemplateDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Adição Rápida — Polo Passivo</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 mt-2">
            {TEMPLATES_POLO_PASSIVO.map((tpl) => (
              <button
                key={tpl.id}
                type="button"
                onClick={() => applyTemplate(tpl)}
                className="w-full text-left p-4 rounded-xl border border-border hover:border-primary/50 hover:bg-primary/5 transition-colors space-y-2"
              >
                <div className="flex items-center gap-2">
                  <Zap className="h-4 w-4 text-amber-500 shrink-0" />
                  <span className="font-medium text-sm">{tpl.label}</span>
                </div>
                <p className="text-xs text-muted-foreground">{tpl.description}</p>
                <div className="mt-2 space-y-1">
                  {tpl.partes.map((p, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs text-muted-foreground">
                      {p.tipoPessoa === 'juridica' ? (
                        <Building2 className="h-3 w-3 shrink-0" />
                      ) : (
                        <User className="h-3 w-3 shrink-0" />
                      )}
                      <span>{p.nome}</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted">{p.tipoVinculacao}</span>
                    </div>
                  ))}
                </div>
              </button>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
