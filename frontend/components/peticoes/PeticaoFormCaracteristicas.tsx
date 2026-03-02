'use client'

import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { DadosBasicos } from '@/types/peticoes'

interface Props {
  dadosBasicos: DadosBasicos
  onChange: (partial: Partial<DadosBasicos>) => void
}

const PRIORIDADES_DISPONIVEIS = [
  { value: 'JUÍZO 100% DIGITAL', label: 'Juízo 100% Digital', desc: 'Evita deslocamentos — todos os atos são eletrônicos' },
  { value: 'IDOSO', label: 'Idoso (60+ anos)', desc: 'Prioridade de tramitação para pessoa idosa' },
  { value: 'DOENÇA_GRAVE', label: 'Doença Grave', desc: 'Portador de doença grave' },
  { value: 'CRIANÇA_ADOLESCENTE', label: 'Criança / Adolescente', desc: 'Envolve menor de 18 anos' },
]

const SIGILO_LABELS: Record<number, string> = {
  0: '0 — Público (sem sigilo)',
  1: '1 — Segredo de Justiça',
  2: '2 — Sigiloso',
  3: '3 — Ultrassecreto',
  4: '4 — Secreto',
  5: '5 — Reservado',
}

function RadioBool({
  label,
  value,
  onChange,
}: {
  label: string
  value: boolean | undefined
  onChange: (v: boolean) => void
}) {
  return (
    <div>
      <Label className="text-xs mb-2 block">{label}</Label>
      <div className="flex gap-3">
        {[
          { v: true, label: 'Sim' },
          { v: false, label: 'Não' },
        ].map(({ v, label: optLabel }) => (
          <button
            key={String(v)}
            type="button"
            onClick={() => onChange(v)}
            className={`flex-1 py-2 rounded-lg border text-sm font-medium transition-colors ${
              value === v
                ? 'border-primary bg-primary/10 text-primary'
                : 'border-border bg-card text-muted-foreground hover:border-primary/40 hover:text-foreground'
            }`}
          >
            {optLabel}
          </button>
        ))}
      </div>
    </div>
  )
}

export function PeticaoFormCaracteristicas({ dadosBasicos, onChange }: Props) {
  const prioridades = dadosBasicos.prioridade ?? []
  const nivelSigilo = dadosBasicos.nivelSigilo ?? 0

  const togglePrioridade = (value: string) => {
    const next = prioridades.includes(value)
      ? prioridades.filter((p) => p !== value)
      : [...prioridades, value]
    onChange({ prioridade: next })
  }

  return (
    <div className="bg-card border border-border rounded-2xl p-8 shadow-sm">
      <h2 className="font-display text-xl font-semibold text-foreground mb-6 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary">tune</span>
        Características do Processo
      </h2>

      <div className="space-y-6">
        {/* Prioridades */}
        <div>
          <Label className="text-xs mb-3 block font-medium">
            Prioridade / Modalidade
          </Label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {PRIORIDADES_DISPONIVEIS.map(({ value, label, desc }) => {
              const checked = prioridades.includes(value)
              return (
                <button
                  key={value}
                  type="button"
                  onClick={() => togglePrioridade(value)}
                  className={`text-left p-3 rounded-xl border transition-colors ${
                    checked
                      ? 'border-primary bg-primary/8 text-primary'
                      : 'border-border bg-muted/20 text-foreground hover:border-primary/40'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-0.5">
                    <span
                      className={`w-4 h-4 rounded border-2 flex items-center justify-center shrink-0 transition-colors ${
                        checked ? 'border-primary bg-primary' : 'border-muted-foreground'
                      }`}
                    >
                      {checked && (
                        <span className="material-symbols-outlined text-[11px] text-primary-foreground leading-none">
                          check
                        </span>
                      )}
                    </span>
                    <span className="text-sm font-medium">{label}</span>
                  </div>
                  <p className="text-xs text-muted-foreground ml-6">{desc}</p>
                </button>
              )
            })}
          </div>
        </div>

        {/* Valor da causa + Sigilo lado a lado */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <Label className="text-xs mb-1 block">Valor da Causa (R$)</Label>
            <Input
              type="number"
              min={0}
              step={0.01}
              value={dadosBasicos.valorCausa ?? ''}
              onChange={(e) =>
                onChange({
                  valorCausa: e.target.value ? parseFloat(e.target.value) : undefined,
                })
              }
              placeholder="0,00"
              className="h-9 text-sm font-mono"
            />
          </div>
          <div>
            <Label className="text-xs mb-1 block">Segredo de Justiça</Label>
            <Select
              value={String(nivelSigilo)}
              onValueChange={(v) => onChange({ nivelSigilo: parseInt(v) })}
            >
              <SelectTrigger className="h-9 text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(SIGILO_LABELS).map(([k, label]) => (
                  <SelectItem key={k} value={k}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Justiça Gratuita + Pedido de Liminar */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <RadioBool
            label="Justiça Gratuita"
            value={dadosBasicos.justicaGratuita}
            onChange={(v) => onChange({ justicaGratuita: v })}
          />
          <RadioBool
            label="Pedido de Liminar / Tutela de Urgência"
            value={dadosBasicos.pedidoLiminar}
            onChange={(v) => onChange({ pedidoLiminar: v })}
          />
        </div>
      </div>
    </div>
  )
}
