'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useWebSocket } from '@/hooks/useWebSocket'
import type { SyncProgressEvent } from '@/types/casos-oab'

/**
 * Pipeline progress phases and their labels.
 */
const PHASE_LABELS: Record<string, string> = {
  starting: 'Iniciando pipeline...',
  listing: 'Buscando processos no tribunal...',
  listing_done: 'Listagem concluída',
  detailing: 'Extraindo detalhes do processo...',
  detail_done: 'Detalhes extraídos',
  downloading: 'Baixando documento...',
  completed: 'Sincronização concluída!',
}

export interface PipelineProgress {
  fase: string
  faseLabel: string
  tribunal?: string
  numero?: string
  /** E.g. "processo 3 de 7" */
  processoIndex?: number
  processoTotal?: number
  /** E.g. "doc 2 de 5" */
  docIndex?: number
  docTotal?: number
  /** Summary counts after completion */
  totalProcessos?: number
  novosProcessos?: number
  novasMovimentacoes?: number
  docsBaixados?: number
  docLinks?: number
  errors?: Array<{ tribunal: string; error: string }>
}

/**
 * Hook that listens to WebSocket for real-time OAB sync pipeline progress.
 *
 * Returns the latest progress event, automatically parsed.
 * Falls back to null when no sync is running.
 */
export function useSyncProgress() {
  const { lastMessage, isConnected } = useWebSocket()
  const [progress, setProgress] = useState<PipelineProgress | null>(null)
  const timeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Parse WebSocket messages
  useEffect(() => {
    if (!lastMessage) return

    try {
      const parsed = JSON.parse(lastMessage)
      if (parsed.type !== 'oab_sync_progress') return

      const event = parsed as SyncProgressEvent
      const data = event.data

      const newProgress: PipelineProgress = {
        fase: data.fase,
        faseLabel: PHASE_LABELS[data.fase] || data.fase,
        tribunal: data.tribunal,
        numero: data.numero,
        processoIndex: data.index,
        processoTotal: data.total,
        docIndex: data.doc_index,
        docTotal: data.doc_total,
        totalProcessos: data.total_processos,
        novosProcessos: data.novos_processos,
        novasMovimentacoes: data.novas_movimentacoes,
        docsBaixados: data.docs_baixados,
        docLinks: data.doc_links,
        errors: data.errors,
      }

      setProgress(newProgress)

      // Clear progress 10s after completion
      if (data.fase === 'completed') {
        if (timeoutRef.current) clearTimeout(timeoutRef.current)
        timeoutRef.current = setTimeout(() => setProgress(null), 10_000)
      }
    } catch {
      // Ignore non-JSON messages
    }
  }, [lastMessage])

  // Cleanup
  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
    }
  }, [])

  const clearProgress = useCallback(() => setProgress(null), [])

  return { progress, isConnected, clearProgress }
}
