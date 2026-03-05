'use client'

import { useState, useRef, useEffect } from 'react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { TRIBUNAIS, JURISDICAO_ORDER, getTribunaisByJurisdicao } from '@/lib/data/tribunais'
import { TIPO_PETICAO_LABELS } from '@/types/peticoes'
import type { TribunalId, TipoPeticao, NovaPeticaoFormData, DadosBasicos } from '@/types/peticoes'
import { useCasosOAB } from '@/hooks/api/useCasosOAB'
import { useTiposDocumentoPje, useTiposDocumentoTPU } from '@/hooks/api/usePeticoes'
import { maskProcessoNumero, isProcessoNumeroValido, tribunalFromProcesso } from '@/lib/utils/processo'

// codigoLocalidade PJe/MNI — código interno de cada seção judiciária.
// Fonte: tabela interna do PJe (NÃO é código IBGE nem CNJ TPU).
// O campo aceita digitação livre — se a comarca não estiver listada, basta digitar o código.
const COMARCAS_COMUNS = [
  // Capitais — TRF1 (AM, AP, AC, BA, DF, GO, MA, MG, MT, PA, PI, RO, RR, TO)
  { codigo: '0002100', nome: 'São Luís/MA' },
  { codigo: '0002101', nome: 'Imperatriz/MA' },
  { codigo: '0002102', nome: 'Caxias/MA' },
  { codigo: '0002103', nome: 'Balsas/MA' },
  { codigo: '0002104', nome: 'Bacabal/MA' },
  { codigo: '0002105', nome: 'Codó/MA' },
  { codigo: '0002106', nome: 'Timon/MA' },
  { codigo: '0001500', nome: 'Belém/PA' },
  { codigo: '0003200', nome: 'Manaus/AM' },
  { codigo: '0001207', nome: 'Rio Branco/AC' },
  { codigo: '0001100', nome: 'Porto Velho/RO' },
  { codigo: '0001600', nome: 'Macapá/AP' },
  { codigo: '0002200', nome: 'Teresina/PI' },
  { codigo: '0003100', nome: 'Belo Horizonte/MG' },
  { codigo: '0005300', nome: 'Brasília/DF' },
  { codigo: '0005200', nome: 'Goiânia/GO' },
  { codigo: '0005100', nome: 'Cuiabá/MT' },
  { codigo: '0001700', nome: 'Palmas/TO' },
  { codigo: '0001400', nome: 'Boa Vista/RR' },
  // TRF5 (AL, CE, PB, PE, RN, SE)
  { codigo: '0001330', nome: 'Maceió/AL' },
  { codigo: '0001200', nome: 'Fortaleza/CE' },
  { codigo: '0002500', nome: 'João Pessoa/PB' },
  { codigo: '0002611', nome: 'Recife/PE' },
  { codigo: '0002400', nome: 'Natal/RN' },
  { codigo: '0002704', nome: 'Aracaju/SE' },
  // TRF2 (RJ, ES)
  { codigo: '0003300', nome: 'Rio de Janeiro/RJ' },
  { codigo: '0002800', nome: 'Vitória/ES' },
  // TRF3 (SP, MS)
  { codigo: '0003500', nome: 'São Paulo/SP' },
  { codigo: '0007900', nome: 'Campo Grande/MS' },
  // TRF4 (RS, SC, PR)
  { codigo: '0004300', nome: 'Porto Alegre/RS' },
  { codigo: '0004200', nome: 'Florianópolis/SC' },
  { codigo: '0004100', nome: 'Curitiba/PR' },
  // TRF6 (MG — desmembrado)
  // TRF5 BA
  { codigo: '0002900', nome: 'Salvador/BA' },
]

interface Props {
  formData: NovaPeticaoFormData
  onChange: (data: Partial<NovaPeticaoFormData>) => void
  dadosBasicos?: DadosBasicos
  onDadosBasicosChange?: (partial: Partial<DadosBasicos>) => void
}

const tribunaisPorJurisdicao = getTribunaisByJurisdicao()

export function PeticaoFormDadosProcesso({ formData, onChange, dadosBasicos, onDadosBasicosChange }: Props) {
  const selectedTribunal = TRIBUNAIS.find((t) => t.id === formData.tribunalId)
  const isPeticaoInicial = formData.tipoPeticao === 'peticao_inicial'
  const [tribunalAutoDetectado, setTribunalAutoDetectado] = useState(false)

  // Tipos de documento do PJe para o tribunal selecionado
  const { data: tiposPje = [], isLoading: isLoadingTipos } = useTiposDocumentoPje(
    formData.tribunalId || undefined
  )

  // Tipos de documento da Tabela Processual Unificada (CNJ oficial)
  const { data: tiposTPU = [], isLoading: isLoadingTPU } = useTiposDocumentoTPU(
    formData.tribunalId || undefined
  )

  // Auto-detect tribunal when process number is pre-filled (e.g. from URL query param)
  useEffect(() => {
    if (formData.processoNumero && !formData.tribunalId) {
      const detected = tribunalFromProcesso(formData.processoNumero)
      if (detected) {
        onChange({ tribunalId: detected as TribunalId })
        setTribunalAutoDetectado(true)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [formData.processoNumero])

  // --- Process number autocomplete ---
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const { data: casosData } = useCasosOAB()
  const savedProcessos = casosData?.items ?? []

  const filterQuery = (formData.processoNumero ?? '').trim().toLowerCase()
  const filteredProcessos = savedProcessos
    .filter((p) => {
      if (!filterQuery) return true
      return (
        p.numero.toLowerCase().includes(filterQuery) ||
        (p.partesResumo ?? '').toLowerCase().includes(filterQuery)
      )
    })
    .slice(0, 8)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div className="bg-card border border-border rounded-2xl p-8 shadow-sm">
      <h2 className="font-display text-xl font-semibold text-foreground mb-6 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary">description</span>
        Dados do Processo
      </h2>

      <div className="space-y-5">
        {/* Tribunal */}
        <div>
          <Label className="text-sm font-medium mb-2 block">Tribunal de Destino</Label>
          <Select
            value={formData.tribunalId || undefined}
            onValueChange={(v) => {
              onChange({ tribunalId: v as TribunalId })
              setTribunalAutoDetectado(false) // usuário escolheu manualmente
            }}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Selecionar Tribunal..." />
            </SelectTrigger>
            <SelectContent className="max-h-72 overflow-y-auto">
              {JURISDICAO_ORDER.map((jur) => {
                const tribunais = tribunaisPorJurisdicao[jur]
                if (tribunais.length === 0) return null
                return (
                  <SelectGroup key={jur}>
                    <SelectLabel className="text-xs uppercase tracking-wider text-muted-foreground">
                      {jur}
                    </SelectLabel>
                    {tribunais.map((t) => (
                      <SelectItem key={t.id} value={t.id}>
                        <div className="flex items-center gap-2">
                          <span>{t.nome}</span>
                          <span className="text-[10px] font-mono bg-muted px-1.5 py-0.5 rounded text-muted-foreground">
                            {t.sistema}
                          </span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectGroup>
                )
              })}
            </SelectContent>
          </Select>
          {tribunalAutoDetectado && formData.tribunalId && (
            <p className="mt-1.5 text-xs text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
              <span className="material-symbols-outlined text-xs">auto_fix_high</span>
              Detectado automaticamente pelo número do processo
            </p>
          )}
          {selectedTribunal?.avisoInstabilidade && (
            <div className="mt-2 flex items-start gap-2 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
              <span className="material-symbols-outlined text-yellow-600 text-sm shrink-0 mt-0.5">warning</span>
              <p className="text-xs text-yellow-700 dark:text-yellow-400">
                {selectedTribunal.avisoInstabilidade}
              </p>
            </div>
          )}
        </div>

        {/* Tipo de Petição (primeiro para guiar o preenchimento do número) */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <Label className="text-sm font-medium mb-2 block">Tipo de Petição</Label>
            <Select
              value={formData.tipoPeticao || undefined}
              onValueChange={(v) => {
                const tipo = v as TipoPeticao
                onChange({
                  tipoPeticao: tipo,
                  // Limpa número ao trocar para Petição Inicial
                  ...(tipo === 'peticao_inicial' ? { processoNumero: '' } : {}),
                })
              }}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Selecionar tipo..." />
              </SelectTrigger>
              <SelectContent>
                {(Object.entries(TIPO_PETICAO_LABELS) as [TipoPeticao, string][]).map(([key, label]) => (
                  <SelectItem key={key} value={key}>{label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label className={`text-sm font-medium mb-2 block ${isPeticaoInicial ? 'text-muted-foreground' : ''}`}>
              Número do Processo
              {isPeticaoInicial && (
                <span className="ml-1.5 text-xs font-normal text-muted-foreground">(gerado pelo tribunal)</span>
              )}
            </Label>
            <div className="relative" ref={wrapperRef}>
              <Input
                value={isPeticaoInicial ? '' : formData.processoNumero}
                onChange={(e) => {
                  const masked = maskProcessoNumero(e.target.value)
                  const updates: Partial<typeof formData> = { processoNumero: masked }
                  // Auto-detectar tribunal pelo número CNJ
                  const detected = tribunalFromProcesso(masked)
                  if (detected && !formData.tribunalId) {
                    updates.tribunalId = detected as TribunalId
                    setTribunalAutoDetectado(true)
                  } else if (detected && formData.tribunalId !== detected) {
                    // Número mudou para outro tribunal — atualiza se foi auto-detectado antes
                    if (tribunalAutoDetectado) {
                      updates.tribunalId = detected as TribunalId
                    }
                  } else if (!detected) {
                    setTribunalAutoDetectado(false)
                  }
                  onChange(updates)
                  if (masked.replace(/\D/g, '').length > 0) setDropdownOpen(false)
                }}
                onFocus={() => {
                  if (!isPeticaoInicial && savedProcessos.length > 0) setDropdownOpen(true)
                }}
                placeholder={isPeticaoInicial ? 'Será atribuído após o protocolo' : '0000000-00.0000.0.00.0000'}
                maxLength={25}
                className={`font-mono ${isPeticaoInicial
                    ? 'bg-muted/50 cursor-not-allowed text-muted-foreground'
                    : formData.processoNumero && !isProcessoNumeroValido(formData.processoNumero)
                      ? 'border-destructive focus-visible:ring-destructive'
                      : ''
                  }`}
                disabled={isPeticaoInicial}
                autoComplete="off"
                name="processo-numero"
                inputMode="numeric"
              />
              {dropdownOpen && !isPeticaoInicial && filteredProcessos.length > 0 && (
                <div className="absolute top-full left-0 right-0 z-50 mt-1 bg-background border border-border rounded-lg shadow-lg max-h-64 overflow-y-auto">
                  {filteredProcessos.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      className="w-full text-left px-3 py-2.5 hover:bg-muted/60 flex items-center gap-3 transition-colors border-b border-border/40 last:border-0"
                      onMouseDown={(e) => {
                        e.preventDefault()
                        const detected = tribunalFromProcesso(p.numero)
                        onChange({
                          processoNumero: maskProcessoNumero(p.numero),
                          ...(detected && !formData.tribunalId ? { tribunalId: detected as TribunalId } : {}),
                        })
                        if (detected && !formData.tribunalId) setTribunalAutoDetectado(true)
                        setDropdownOpen(false)
                      }}
                    >
                      <span className="font-mono text-sm font-medium shrink-0 text-foreground">{maskProcessoNumero(p.numero)}</span>
                      {p.partesResumo && (
                        <span className="text-xs text-muted-foreground truncate">— {p.partesResumo}</span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
            {isPeticaoInicial ? (
              <p className="mt-1.5 text-xs text-muted-foreground flex items-center gap-1">
                <span className="material-symbols-outlined text-xs">info</span>
                Petição Inicial cria um processo novo — o número é gerado pelo tribunal
              </p>
            ) : formData.processoNumero && !isProcessoNumeroValido(formData.processoNumero) ? (
              <p className="mt-1.5 text-xs text-destructive flex items-center gap-1">
                <span className="material-symbols-outlined text-xs">error</span>
                Formato inválido — use NNNNNNN-DD.AAAA.J.TT.OOOO (ex: 1014980-12.2025.4.01.4100)
              </p>
            ) : formData.processoNumero && isProcessoNumeroValido(formData.processoNumero) ? (
              <p className="mt-1.5 text-xs text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                <span className="material-symbols-outlined text-xs">check_circle</span>
                Número no formato CNJ correto
              </p>
            ) : null}
          </div>
        </div>

        {/* Tipo de Documento PJe + Descrição PJe */}
        {formData.tribunalId && (tiposPje.length > 0 || tiposTPU.length > 0) && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <Label className="text-sm font-medium mb-2 block">
                Tipo de Documento{' '}
                <span className="text-xs font-normal text-muted-foreground">(PJe)</span>
                <span className="ml-1 text-destructive">*</span>
              </Label>
              <Select
                value={formData.tipoPeticaoPje || undefined}
                onValueChange={(v) => onChange({ tipoPeticaoPje: v })}
              >
                <SelectTrigger className="w-full">
                  <SelectValue
                    placeholder={
                      isLoadingTipos || isLoadingTPU ? 'Carregando...' : 'Selecionar tipo PJe...'
                    }
                  />
                </SelectTrigger>
                <SelectContent className="max-h-80 overflow-y-auto">
                  {tiposPje.length > 0 && (
                    <SelectGroup>
                      <SelectLabel className="text-xs text-muted-foreground px-2 py-1.5">
                        🟢 Tipos PJe — capturados do tribunal
                      </SelectLabel>
                      {tiposPje.map((tipo) => (
                        <SelectItem key={`pje-${tipo}`} value={tipo}>
                          {tipo}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  )}
                  {tiposTPU.length > 0 && (
                    <SelectGroup>
                      <SelectLabel className="text-xs text-muted-foreground px-2 py-1.5">
                        🟦 Tipos TPU — Tabela Processual Unificada (CNJ)
                      </SelectLabel>
                      {tiposTPU.map((tipo) => (
                        <SelectItem
                          key={`tpu-${tipo.cod_item}`}
                          value={tipo.nome}
                          title={tipo.descricao || undefined}
                        >
                          <span className="mr-1.5 text-xs text-muted-foreground font-mono">
                            {tipo.cod_item}
                          </span>
                          {tipo.nome}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  )}
                </SelectContent>
              </Select>
              <p className="mt-1 text-xs text-muted-foreground">
                <span className="text-green-600">●</span> PJe: label exato do formulário ·{' '}
                <span className="text-blue-600">●</span> TPU: tabela oficial CNJ (com código)
              </p>
            </div>
            <div>
              <Label className="text-sm font-medium mb-2 block">
                Descrição{' '}
                <span className="text-xs font-normal text-muted-foreground">(campo PJe — opcional)</span>
              </Label>
              <Input
                value={formData.descricaoPje ?? ''}
                onChange={(e) => onChange({ descricaoPje: e.target.value || undefined })}
                placeholder="Descrição livre do documento..."
                className="h-9 text-sm"
                maxLength={500}
              />
            </div>
          </div>
        )}

        {/* Comarca / Localidade */}
        <div>
          <Label className="text-sm font-medium mb-2 block">
            Comarca / Localidade
            <span className="ml-1.5 text-xs font-normal text-muted-foreground">
              (domicílio do requerente — codigoLocalidade MNI)
            </span>
          </Label>
          {/* Campo livre: digita nome ou código. Lista é sugestão — não é exaustiva */}
          <div className="relative">
            <Input
              list="comarcas-datalist"
              value={dadosBasicos?.codigoLocalidade ?? ''}
              onChange={(e) => {
                const typed = e.target.value
                // Se bater exato em nome, guarda o código; senão guarda o que foi digitado
                const match = COMARCAS_COMUNS.find(
                  (c) => c.nome.toLowerCase() === typed.toLowerCase() || c.codigo === typed
                )
                onDadosBasicosChange?.({ codigoLocalidade: match ? match.codigo : typed || undefined })
              }}
              placeholder="Ex: Balsas/MA ou código 0002103"
              className="font-mono pr-10"
              autoComplete="off"
            />
            {dadosBasicos?.codigoLocalidade && (() => {
              const match = COMARCAS_COMUNS.find((c) => c.codigo === dadosBasicos.codigoLocalidade)
              return match ? (
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground truncate max-w-30">
                  {match.nome}
                </span>
              ) : null
            })()}
          </div>
          <datalist id="comarcas-datalist">
            {COMARCAS_COMUNS.map((c) => (
              <option key={c.codigo} value={c.codigo} label={c.nome} />
            ))}
          </datalist>
          <p className="mt-1.5 text-xs text-muted-foreground flex items-center gap-1">
            <span className="material-symbols-outlined text-xs">info</span>
            Digite o nome (sugestão) ou o código direto do PJe. Código do PJe ≠ IBGE.
          </p>
        </div>

        {/* Descrição */}
        <div>
          <Label className="text-sm font-medium mb-2 block">
            Descrição <span className="text-muted-foreground font-normal">(opcional)</span>
          </Label>
          <Textarea
            value={formData.descricao}
            onChange={(e) => onChange({ descricao: e.target.value })}
            placeholder="Observações ou detalhes adicionais sobre a petição..."
            rows={3}
          />
        </div>
      </div>
    </div>
  )
}
