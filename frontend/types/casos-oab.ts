/**
 * TypeScript types for OAB-scraped cases (Casos).
 */

export interface CasoOAB {
  id: string
  numero: string
  classe?: string | null
  assunto?: string | null
  partesResumo?: string | null
  oabNumero: string
  oabUf: string
  tribunal: string
  ultimaSincronizacao?: string | null
  totalMovimentacoes: number
  novasMovimentacoes: number
  totalDocumentos: number
  monitoramentoAtivo: boolean
  createdAt: string
}

export interface CasoOABDetail extends CasoOAB {
  partesJson?: ParteOAB[] | null
  movimentacoesJson?: MovimentacaoOAB[] | null
  documentosJson?: DocumentoOAB[] | null
}

export interface MovimentacaoOAB {
  descricao: string
  documento_vinculado?: string | null
  tem_documento?: boolean
}

export interface DocumentoOAB {
  nome: string
  tipo?: string | null
  s3Url?: string
  s3_url?: string
  tamanhoBytes?: number | null
  tamanho_bytes?: number | null
}

export interface ParteOAB {
  polo?: string | null
  nome: string
  papel?: string | null
  oab?: string | null
  documento?: string | null
}

export interface CasoOABListResponse {
  items: CasoOAB[]
  total: number
}

export interface SyncStatusResponse {
  ultimoSync?: string | null
  status: string
  totalProcessos: number
  oabNumero?: string | null
  oabUf?: string | null
  progressoDetalhado?: SyncProgressoDetalhado | null
}

/**
 * Detailed pipeline progress (from backend progresso_detalhado JSONB).
 */
export interface SyncProgressoDetalhado {
  fase_atual?: string
  tribunal_atual?: string
  tribunais?: string[]
  tribunais_status?: Record<string, string>
  total_processos?: number
  processados?: number
  novos_processos?: number
  novas_movimentacoes?: number
  total_docs?: number
  docs_baixados?: number
  errors?: Array<{ tribunal: string; error: string }>
}

/**
 * WebSocket progress event (real-time push from pipeline tasks).
 */
export interface SyncProgressEvent {
  type: 'oab_sync_progress'
  sync_config_id: string
  data: {
    fase: string
    tribunal?: string
    numero?: string
    index?: number
    total?: number
    doc_index?: number
    doc_total?: number
    total_processos?: number
    novos_processos?: number
    novas_movimentacoes?: number
    docs_baixados?: number
    doc_links?: number
    errors?: Array<{ tribunal: string; error: string }>
  }
}

export interface SyncTriggerResponse {
  sucesso: boolean
  mensagem: string
  queued: boolean
  total: number
  novosProcessos: number
  novasMovimentacoes: number
}
