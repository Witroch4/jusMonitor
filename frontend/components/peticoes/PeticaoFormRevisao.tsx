'use client'

import { cn } from '@/lib/utils'
import { TRIBUNAIS } from '@/lib/data/tribunais'
import { TIPO_PETICAO_LABELS } from '@/types/peticoes'
import type { NovaPeticaoFormData, UploadedFile, AnaliseIA } from '@/types/peticoes'

interface Props {
  formData: NovaPeticaoFormData
  files: UploadedFile[]
  analise: AnaliseIA | null
}

interface CheckItem {
  label: string
  ok: boolean
}

export function PeticaoFormRevisao({ formData, files, analise }: Props) {
  const tribunal = TRIBUNAIS.find((t) => t.id === formData.tribunalId)
  const hasPrincipal = files.some((f) => f.tipoDocumento === 'peticao_principal' && f.status === 'uploaded')
  const validFiles = files.filter((f) => f.status === 'uploaded')

  const isPeticaoInicial = formData.tipoPeticao === 'peticao_inicial'
  const processoOk = isPeticaoInicial || formData.processoNumero.length > 10

  const checks: CheckItem[] = [
    { label: 'Tribunal selecionado', ok: !!formData.tribunalId },
    { label: isPeticaoInicial ? 'Número gerado pelo tribunal' : 'Número do processo preenchido', ok: processoOk },
    { label: 'Tipo de petição selecionado', ok: !!formData.tipoPeticao },
    { label: 'Matéria preenchida', ok: (formData.dadosBasicos?.assuntos?.length || 0) > 0 },
    { label: 'Documento principal anexado', ok: hasPrincipal },
    { label: 'Certificado digital selecionado', ok: !!formData.certificadoId },
  ]

  const allOk = checks.every((c) => c.ok)

  return (
    <div className="bg-card border border-border rounded-2xl p-8 shadow-sm">
      <h2 className="font-display text-xl font-semibold text-foreground mb-6 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary">checklist</span>
        Revisão e Envio
      </h2>

      {/* Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="space-y-2">
          <div className="text-xs text-muted-foreground">Tribunal</div>
          <div className="text-sm font-medium">{tribunal?.nome ?? '—'}</div>
        </div>
        <div className="space-y-2">
          <div className="text-xs text-muted-foreground">Processo</div>
          <div className="text-sm font-medium font-mono">{formData.processoNumero || '—'}</div>
        </div>
        <div className="space-y-2">
          <div className="text-xs text-muted-foreground">Tipo</div>
          <div className="text-sm font-medium">
            {formData.tipoPeticao ? TIPO_PETICAO_LABELS[formData.tipoPeticao] : '—'}
          </div>
        </div>
        <div className="space-y-2">
          <div className="text-xs text-muted-foreground">Documentos</div>
          <div className="text-sm font-medium">{validFiles.length} arquivo(s)</div>
        </div>
      </div>

      {/* Checklist */}
      <div className="border-t border-border pt-4">
        <h3 className="text-xs font-bold text-muted-foreground tracking-widest uppercase mb-3">
          Checklist de Validação
        </h3>
        <div className="space-y-2">
          {checks.map((check, i) => (
            <div key={i} className="flex items-center gap-2.5">
              <span className={cn(
                'material-symbols-outlined text-base',
                check.ok ? 'text-emerald-500' : 'text-muted-foreground/40'
              )}>
                {check.ok ? 'check_circle' : 'radio_button_unchecked'}
              </span>
              <span className={cn(
                'text-sm',
                check.ok ? 'text-foreground' : 'text-muted-foreground'
              )}>
                {check.label}
              </span>
            </div>
          ))}
        </div>

        {!allOk && (
          <p className="mt-4 text-xs text-muted-foreground">
            Preencha todos os campos obrigatórios para habilitar o protocolo.
          </p>
        )}
      </div>
    </div>
  )
}

export function useRevisaoValidation(
  formData: NovaPeticaoFormData,
  files: UploadedFile[],
  analise?: AnaliseIA | null
): boolean {
  const hasPrincipal = files.some((f) => f.tipoDocumento === 'peticao_principal' && f.status === 'uploaded')
  const isPeticaoInicial = formData.tipoPeticao === 'peticao_inicial'
  const processoOk = isPeticaoInicial || formData.processoNumero.length > 10
  return (
    !!formData.tribunalId &&
    processoOk &&
    !!formData.tipoPeticao &&
    (formData.dadosBasicos?.assuntos?.length || 0) > 0 &&
    hasPrincipal &&
    !!formData.certificadoId
  )
}
