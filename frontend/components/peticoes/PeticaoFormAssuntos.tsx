'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
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
import { useTpuClasses, useTpuAssuntos, useTpuMaterias, type TpuItem } from '@/hooks/api/useTpu'
import type { AssuntoProcessual } from '@/types/peticoes'
import { Trash2, Search } from 'lucide-react'

interface Props {
  classeProcessual?: number
  classeProcessualNome?: string
  materiaCodigo?: number
  materiaNome?: string
  assuntos: AssuntoProcessual[]
  onClasseChange: (codigo: number | undefined, nome: string | undefined) => void
  onMateriaChange: (codigo: number | undefined, nome: string | undefined) => void
  onAssuntosChange: (assuntos: AssuntoProcessual[]) => void
}

function TpuAutocomplete({
  label,
  placeholder,
  value,
  onSearch,
  results,
  isLoading,
  onSelect,
  showHierarchy = false,
}: {
  label: string
  placeholder: string
  value: string
  onSearch: (q: string) => void
  results?: TpuItem[]
  isLoading: boolean
  onSelect: (item: TpuItem) => void
  showHierarchy?: boolean
}) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleChange = (val: string) => {
    setQuery(val)
    onSearch(val)
    setOpen(true)
  }

  return (
    <div ref={ref} className="relative">
      {label && <Label className="text-xs mb-1 block">{label}</Label>}
      {value ? (
        <div className="flex items-center gap-2">
          <div className="flex-1 px-3 py-2 text-sm bg-muted/50 rounded-md border border-border truncate">
            {value}
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => {
              onSelect({ cod_item: 0, nome: '' })
              setQuery('')
            }}
            className="h-9 w-9 p-0 text-muted-foreground hover:text-destructive shrink-0"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      ) : (
        <>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => handleChange(e.target.value)}
              onFocus={() => {
                onSearch(query)
                setOpen(true)
              }}
              placeholder={placeholder}
              className="h-9 text-sm pl-9"
            />
          </div>
          {open && (
            <div className="absolute z-50 mt-1 w-full bg-popover border border-border rounded-lg shadow-lg max-h-64 overflow-y-auto">
              {isLoading ? (
                <div className="px-3 py-2 text-xs text-muted-foreground">Buscando...</div>
              ) : results && results.length > 0 ? (
                results.map((item) => (
                  <button
                    key={item.cod_item}
                    type="button"
                    onClick={() => {
                      onSelect(item)
                      setQuery('')
                      setOpen(false)
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-muted/50 transition-colors border-b border-border/30 last:border-b-0"
                  >
                    {showHierarchy && item.hierarquia ? (
                      <div className="space-y-0.5">
                        <div className="text-[11px] text-muted-foreground leading-tight">
                          {item.hierarquia}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-mono bg-primary/10 text-primary px-1.5 py-0.5 rounded shrink-0">
                            {item.cod_item}
                          </span>
                          <span className="text-sm font-medium">{item.nome}</span>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono bg-primary/10 text-primary px-1.5 py-0.5 rounded shrink-0">
                          {item.cod_item}
                        </span>
                        <span className="text-sm truncate">{item.nome}</span>
                      </div>
                    )}
                  </button>
                ))
              ) : results && results.length === 0 && query.length >= 2 ? (
                <div className="px-3 py-2 text-xs text-muted-foreground">Nenhum resultado</div>
              ) : results && results.length === 0 && query.length > 0 ? (
                <div className="px-3 py-2 text-xs text-muted-foreground">Digite ao menos 2 caracteres...</div>
              ) : null}
            </div>
          )}
        </>
      )}
    </div>
  )
}

export function PeticaoFormAssuntos({
  classeProcessual,
  classeProcessualNome,
  materiaCodigo,
  materiaNome,
  assuntos,
  onClasseChange,
  onMateriaChange,
  onAssuntosChange,
}: Props) {
  const classeDisplay = classeProcessual
    ? `${classeProcessual} — ${classeProcessualNome || ''}`
    : ''

  // Matérias (root assuntos) - loaded once
  const { data: materias } = useTpuMaterias()

  // Classes search
  const [classeQuery, setClasseQuery] = useState('')
  const { data: classeResults, isLoading: classeLoading } = useTpuClasses(classeQuery)

  // Assuntos search — filtered by selected matéria
  const [assuntoQuery, setAssuntoQuery] = useState('')
  const { data: assuntoResults, isLoading: assuntoLoading } = useTpuAssuntos(assuntoQuery, materiaCodigo)

  const addAssunto = (item: TpuItem) => {
    if (item.cod_item === 0) return
    if (assuntos.some((a) => a.codigoNacional === item.cod_item)) return
    const isFirst = assuntos.length === 0
    onAssuntosChange([
      ...assuntos,
      {
        codigoNacional: item.cod_item,
        nome: item.nome,
        principal: isFirst,
        hierarquia: item.hierarquia,
      },
    ])
  }

  const removeAssunto = (idx: number) => {
    const updated = assuntos.filter((_, i) => i !== idx)
    if (updated.length > 0 && !updated.some((a) => a.principal)) {
      updated[0].principal = true
    }
    onAssuntosChange(updated)
  }

  const togglePrincipal = (idx: number) => {
    const updated = assuntos.map((a, i) => ({ ...a, principal: i === idx }))
    onAssuntosChange(updated)
  }

  return (
    <div className="bg-card border border-border rounded-2xl p-8 shadow-sm">
      <h2 className="font-display text-xl font-semibold text-foreground mb-6 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary">category</span>
        Classificação Processual
      </h2>

      <div className="space-y-5">
        {/* Matéria — select simples como no PJe */}
        <div>
          <Label className="text-xs mb-1 block">Matéria <span className="text-red-500">*</span></Label>
          <Select
            value={materiaCodigo?.toString() || ''}
            onValueChange={(val) => {
              const mat = materias?.find((m) => m.cod_item.toString() === val)
              if (mat) {
                onMateriaChange(mat.cod_item, mat.nome)
              } else {
                onMateriaChange(undefined, undefined)
              }
            }}
          >
            <SelectTrigger className="h-9 text-sm">
              <SelectValue placeholder="Selecione a matéria" />
            </SelectTrigger>
            <SelectContent className="max-h-64">
              {materias?.map((m) => (
                <SelectItem key={m.cod_item} value={m.cod_item.toString()} className="text-sm">
                  {m.nome}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Classe Judicial */}
        <TpuAutocomplete
          label="Classe Judicial (TPU/CNJ)"
          placeholder="Buscar classe... (ex: Mandado de Segurança)"
          value={classeDisplay}
          onSearch={setClasseQuery}
          results={classeResults}
          isLoading={classeLoading}
          onSelect={(item) => {
            if (item.cod_item === 0) {
              onClasseChange(undefined, undefined)
            } else {
              onClasseChange(item.cod_item, item.nome)
            }
          }}
        />

        {/* Assuntos Associados — filtrados pela matéria */}
        <div>
          <Label className="text-sm font-medium mb-2 block">
            Assuntos Associados <span className="text-red-500">*</span>
            {materiaNome && (
              <span className="text-xs text-muted-foreground font-normal ml-2">
                ({materiaNome})
              </span>
            )}
          </Label>
          {assuntos.length > 0 && (
            <div className="space-y-1.5 mb-3">
              {assuntos.map((a, idx) => (
                <div
                  key={a.codigoNacional}
                  className="flex items-start gap-2 px-3 py-2 rounded-md bg-muted/30 border border-border text-sm"
                >
                  <button
                    type="button"
                    onClick={() => togglePrincipal(idx)}
                    className={`shrink-0 text-xs font-bold px-2 py-0.5 rounded-full transition-colors mt-0.5 ${a.principal
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted text-muted-foreground hover:bg-muted-foreground/20'
                      }`}
                  >
                    {a.principal ? 'Principal' : 'Secundário'}
                  </button>
                  <div className="flex-1 min-w-0">
                    {a.hierarquia ? (
                      <div className="space-y-0.5">
                        <div className="text-[11px] text-muted-foreground leading-tight">{a.hierarquia}</div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-[10px] font-mono text-muted-foreground">{a.codigoNacional}</span>
                          <span className="truncate font-medium">{a.nome}</span>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] font-mono text-muted-foreground">{a.codigoNacional}</span>
                        <span className="truncate">{a.nome}</span>
                      </div>
                    )}
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => removeAssunto(idx)}
                    className="h-6 w-6 p-0 text-muted-foreground hover:text-destructive shrink-0"
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              ))}
            </div>
          )}

          {materiaCodigo ? (
            <TpuAutocomplete
              label=""
              placeholder="Buscar assunto dentro da matéria selecionada..."
              value=""
              onSearch={setAssuntoQuery}
              results={assuntoResults}
              isLoading={assuntoLoading}
              onSelect={addAssunto}
              showHierarchy
            />
          ) : (
            <div className="px-3 py-2 text-xs text-muted-foreground border border-dashed border-border rounded-md">
              Selecione uma matéria primeiro para buscar assuntos
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
