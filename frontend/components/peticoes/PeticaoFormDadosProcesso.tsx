'use client'

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
import type { TribunalId, TipoPeticao, NovaPeticaoFormData } from '@/types/peticoes'

interface Props {
  formData: NovaPeticaoFormData
  onChange: (data: Partial<NovaPeticaoFormData>) => void
}

const tribunaisPorJurisdicao = getTribunaisByJurisdicao()

export function PeticaoFormDadosProcesso({ formData, onChange }: Props) {
  const selectedTribunal = TRIBUNAIS.find((t) => t.id === formData.tribunalId)

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
            onValueChange={(v) => onChange({ tribunalId: v as TribunalId })}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Selecionar Tribunal..." />
            </SelectTrigger>
            <SelectContent>
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
          {selectedTribunal?.avisoInstabilidade && (
            <div className="mt-2 flex items-start gap-2 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
              <span className="material-symbols-outlined text-yellow-600 text-sm shrink-0 mt-0.5">warning</span>
              <p className="text-xs text-yellow-700 dark:text-yellow-400">
                {selectedTribunal.avisoInstabilidade}
              </p>
            </div>
          )}
        </div>

        {/* Processo + Tipo */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <Label className="text-sm font-medium mb-2 block">Número do Processo</Label>
            <Input
              value={formData.processoNumero}
              onChange={(e) => onChange({ processoNumero: e.target.value })}
              placeholder="0000000-00.0000.0.00.0000"
              className="font-mono"
            />
          </div>
          <div>
            <Label className="text-sm font-medium mb-2 block">Tipo de Petição</Label>
            <Select
              value={formData.tipoPeticao || undefined}
              onValueChange={(v) => onChange({ tipoPeticao: v as TipoPeticao })}
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
        </div>

        {/* Assunto */}
        <div>
          <Label className="text-sm font-medium mb-2 block">Assunto Principal</Label>
          <Input
            value={formData.assunto}
            onChange={(e) => onChange({ assunto: e.target.value })}
            placeholder="Ex: Indenização por Danos Morais..."
          />
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
