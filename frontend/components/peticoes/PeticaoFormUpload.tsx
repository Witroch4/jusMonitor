'use client'

import { useState, useCallback } from 'react'
import { cn } from '@/lib/utils'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { TIPO_DOCUMENTO_LABELS } from '@/types/peticoes'
import type { TipoDocumento, UploadedFile } from '@/types/peticoes'

interface Props {
  files: UploadedFile[]
  onFilesChange: (files: UploadedFile[]) => void
  limiteArquivoMB: number
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1048576).toFixed(1)} MB`
}

function generateId(): string {
  return `file-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export function PeticaoFormUpload({ files, onFilesChange, limiteArquivoMB }: Props) {
  const [dragOver, setDragOver] = useState(false)
  const limitBytes = limiteArquivoMB * 1024 * 1024

  const addFiles = useCallback(
    (newFiles: FileList | File[]) => {
      const fileArray = Array.from(newFiles)
      const uploads: UploadedFile[] = fileArray.map((file, i) => {
        const overLimit = file.size > limitBytes
        const notPdf = file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')
        return {
          file,
          id: generateId(),
          tipoDocumento: (files.length === 0 && i === 0 ? 'peticao_principal' : 'anexo') as TipoDocumento,
          status: overLimit || notPdf ? 'error' : 'uploaded',
          erroValidacao: overLimit
            ? `Arquivo excede o limite de ${limiteArquivoMB}MB`
            : notPdf
              ? 'Apenas arquivos PDF são aceitos'
              : undefined,
        }
      })
      onFilesChange([...files, ...uploads])
    },
    [files, onFilesChange, limitBytes, limiteArquivoMB]
  )

  const removeFile = useCallback(
    (id: string) => {
      onFilesChange(files.filter((f) => f.id !== id))
    },
    [files, onFilesChange]
  )

  const updateFileType = useCallback(
    (id: string, tipo: TipoDocumento) => {
      onFilesChange(files.map((f) => (f.id === id ? { ...f, tipoDocumento: tipo } : f)))
    },
    [files, onFilesChange]
  )

  return (
    <div className="bg-card border border-border rounded-2xl p-8 shadow-sm">
      <h2 className="font-display text-xl font-semibold text-foreground mb-6 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary">cloud_upload</span>
        Documentação
      </h2>

      {/* Drop Zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragOver(false)
          if (e.dataTransfer.files.length > 0) addFiles(e.dataTransfer.files)
        }}
        className={cn(
          'border-2 border-dashed rounded-2xl p-10 text-center transition-all cursor-pointer group',
          dragOver
            ? 'border-primary bg-primary/5'
            : 'border-border hover:border-primary/40 hover:bg-muted/20'
        )}
      >
        <div className={cn(
          'w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4 transition-colors',
          dragOver
            ? 'bg-primary/15 text-primary'
            : 'bg-muted/60 text-muted-foreground group-hover:bg-primary/10 group-hover:text-primary'
        )}>
          <span className="material-symbols-outlined text-3xl">upload_file</span>
        </div>
        <h3 className="text-lg font-medium text-foreground mb-2">
          Arraste e solte seus arquivos PDF
        </h3>
        <p className="text-sm text-primary/80 mb-5">
          Ou clique para selecionar documentos do seu computador
        </p>
        <label className="px-6 py-2 bg-card border border-border rounded-lg text-sm font-medium text-foreground hover:border-primary hover:text-primary transition-colors shadow-sm cursor-pointer inline-block">
          Selecionar Arquivos
          <input
            type="file"
            className="hidden"
            accept=".pdf"
            multiple
            onChange={(e) => e.target.files && addFiles(e.target.files)}
          />
        </label>
        <p className="text-xs text-muted-foreground mt-4">
          Máximo: {limiteArquivoMB}MB por arquivo (PDF)
        </p>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="mt-4 space-y-2">
          {files.map((f, idx) => (
            <div
              key={f.id}
              className={cn(
                'flex items-center justify-between p-3 rounded-xl border',
                f.status === 'error'
                  ? 'bg-destructive/5 border-destructive/20'
                  : 'bg-muted/30 border-border'
              )}
            >
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <span className={cn(
                  'material-symbols-outlined text-2xl shrink-0',
                  f.status === 'error' ? 'text-destructive' : 'text-red-500'
                )}>
                  picture_as_pdf
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-foreground truncate">{f.file.name}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-xs text-muted-foreground">{formatFileSize(f.file.size)}</span>
                    {f.status === 'error' && (
                      <span className="text-xs text-destructive">{f.erroValidacao}</span>
                    )}
                    {f.status === 'uploaded' && (
                      <span className="text-xs text-emerald-600 flex items-center gap-0.5">
                        <span className="material-symbols-outlined text-xs">check</span>
                        Carregado
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <Select
                  value={f.tipoDocumento}
                  onValueChange={(v) => updateFileType(f.id, v as TipoDocumento)}
                >
                  <SelectTrigger className="w-[150px] h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(Object.entries(TIPO_DOCUMENTO_LABELS) as [TipoDocumento, string][]).map(([key, label]) => (
                      <SelectItem key={key} value={key} className="text-xs">{label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <button
                  onClick={() => removeFile(f.id)}
                  className="text-muted-foreground hover:text-destructive transition-colors p-1"
                >
                  <span className="material-symbols-outlined text-lg">delete</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
