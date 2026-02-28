'use client'

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { TIPO_DOCUMENTO_LABELS } from '@/types/peticoes'
import type { PeticaoDocumento } from '@/types/peticoes'

interface Props {
  documentos: PeticaoDocumento[]
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1048576).toFixed(1)} MB`
}

const statusConfig: Record<PeticaoDocumento['status'], { label: string; className: string }> = {
  uploading: { label: 'Enviando', className: 'bg-blue-500/10 text-blue-600 border-blue-200' },
  uploaded: { label: 'Enviado', className: 'bg-primary/15 text-primary border-primary/30' },
  error: { label: 'Erro', className: 'bg-destructive/10 text-destructive border-destructive/30' },
  validado: { label: 'Validado', className: 'bg-emerald-500/15 text-emerald-700 border-emerald-200' },
}

export function PeticaoDocumentos({ documentos }: Props) {
  if (documentos.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <span className="material-symbols-outlined text-3xl mb-2 block">folder_open</span>
        <p className="text-sm">Nenhum documento anexado</p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-border overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow className="bg-muted/30">
            <TableHead className="text-xs uppercase tracking-wider font-semibold">Documento</TableHead>
            <TableHead className="text-xs uppercase tracking-wider font-semibold">Tipo</TableHead>
            <TableHead className="text-xs uppercase tracking-wider font-semibold">Tamanho</TableHead>
            <TableHead className="text-xs uppercase tracking-wider font-semibold">Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {documentos.map((doc) => (
            <TableRow key={doc.id}>
              <TableCell>
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-red-500 text-lg">picture_as_pdf</span>
                  <span className="text-sm font-medium">{doc.nomeOriginal}</span>
                </div>
              </TableCell>
              <TableCell>
                <span className="text-xs text-muted-foreground">
                  {TIPO_DOCUMENTO_LABELS[doc.tipoDocumento]}
                </span>
              </TableCell>
              <TableCell>
                <span className="text-xs text-muted-foreground font-mono">
                  {formatFileSize(doc.tamanhoBytes)}
                </span>
              </TableCell>
              <TableCell>
                <Badge variant="outline" className={cn('text-[10px]', statusConfig[doc.status].className)}>
                  {statusConfig[doc.status].label}
                </Badge>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
