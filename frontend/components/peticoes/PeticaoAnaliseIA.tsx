'use client'

import { cn } from '@/lib/utils'
import { Skeleton } from '@/components/ui/skeleton'
import type { AnaliseIA } from '@/types/peticoes'

interface Props {
  analise: AnaliseIA | null
  isAnalyzing: boolean
  hasDocuments: boolean
  onReanalisar: () => void
}

function ProgressBar({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-1.5">
        <span className="text-slate-300">{label}</span>
        <span className="font-bold text-[#d4af37]">{value}%</span>
      </div>
      <div className="h-2 bg-white/10 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{
            width: `${value}%`,
            background: 'linear-gradient(90deg, #b8860b, #d4af37)',
          }}
        />
      </div>
    </div>
  )
}

export function PeticaoAnaliseIA({ analise, isAnalyzing, hasDocuments, onReanalisar }: Props) {
  return (
    <div
      className="rounded-2xl p-6 text-white"
      style={{
        background: 'linear-gradient(135deg, #0f1929 0%, #1a2744 100%)',
        border: '1px solid rgba(212,175,55,0.2)',
      }}
    >
      <div className="flex items-center gap-2 mb-5">
        <div className="relative">
          <span className="material-symbols-outlined text-[#d4af37] text-2xl">smart_toy</span>
          <span className={cn(
            'absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full',
            isAnalyzing ? 'bg-yellow-400 animate-pulse' : analise ? 'bg-emerald-400' : 'bg-slate-500'
          )} />
        </div>
        <h3 className="font-semibold text-base">Análise Prévia IA</h3>
      </div>

      {!hasDocuments ? (
        <div className="text-center py-6">
          <span className="material-symbols-outlined text-3xl text-slate-500 mb-2 block">upload_file</span>
          <p className="text-sm text-slate-400">
            Faça upload de um documento para iniciar a análise
          </p>
        </div>
      ) : isAnalyzing ? (
        <div className="space-y-4">
          <div className="flex items-center gap-2 mb-4">
            <span className="material-symbols-outlined text-[#d4af37] animate-spin text-lg">progress_activity</span>
            <span className="text-sm text-slate-300">Analisando documento...</span>
          </div>
          <Skeleton className="h-2 w-full bg-white/10" />
          <Skeleton className="h-2 w-3/4 bg-white/10" />
          <Skeleton className="h-2 w-5/6 bg-white/10" />
        </div>
      ) : analise ? (
        <>
          <div className="space-y-4 mb-4">
            <ProgressBar label="Consistência Jurídica" value={analise.consistenciaJuridica} />
            <ProgressBar label="Jurisprudência" value={analise.jurisprudencia} />
            <ProgressBar label="Formatação" value={analise.formatacao} />
          </div>

          <div
            className="rounded-xl p-4 mb-3"
            style={{
              background: 'rgba(212,175,55,0.08)',
              border: '1px solid rgba(212,175,55,0.15)',
            }}
          >
            <p className="text-xs font-semibold text-[#d4af37] mb-2">Feedback da IA:</p>
            <p className="text-xs text-slate-300 leading-relaxed">{analise.feedback}</p>
          </div>

          {analise.sugestoes.length > 0 && (
            <div className="space-y-1.5 mb-3">
              <p className="text-xs font-semibold text-slate-400">Sugestões:</p>
              {analise.sugestoes.map((s, i) => (
                <div key={i} className="flex items-start gap-1.5">
                  <span className="material-symbols-outlined text-[#d4af37] text-xs mt-0.5">arrow_right</span>
                  <p className="text-xs text-slate-400">{s}</p>
                </div>
              ))}
            </div>
          )}

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 bg-emerald-400 rounded-full" />
              <p className="text-xs text-slate-400">
                Análise em {(analise.tempoAnaliseMs / 1000).toFixed(1)}s
              </p>
            </div>
            <button
              onClick={onReanalisar}
              className="text-xs text-[#d4af37] hover:text-[#e5c748] transition-colors flex items-center gap-1"
            >
              <span className="material-symbols-outlined text-xs">refresh</span>
              Reanalisar
            </button>
          </div>
        </>
      ) : null}
    </div>
  )
}
