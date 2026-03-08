export type ContratoTipo = 'prestacao_servicos' | 'honorarios_exito' | 'misto' | 'consultoria' | 'contencioso'
export type ContratoStatus = 'rascunho' | 'ativo' | 'suspenso' | 'encerrado' | 'cancelado' | 'vencido'
export type IndiceReajuste = 'igpm' | 'ipca' | 'inpc' | 'selic' | 'fixo'

export interface ClausulaContrato {
  titulo: string
  descricao: string
}

export interface Contrato {
  id: string
  tenant_id: string
  client_id: string
  assigned_to?: string
  numero_contrato: string
  titulo: string
  descricao?: string
  tipo: ContratoTipo
  status: ContratoStatus
  valor_total?: number
  valor_mensal?: number
  valor_entrada?: number
  percentual_exito?: number
  indice_reajuste?: IndiceReajuste
  data_inicio?: string
  data_vencimento?: string
  data_assinatura?: string
  dia_vencimento_fatura: number
  dias_lembrete_antes: number
  dias_cobranca_apos: number[]
  clausulas?: ClausulaContrato[]
  observacoes?: string
  documento_url?: string
  client_name?: string
  assigned_user_name?: string
  created_at: string
  updated_at: string
}

export interface ContratoListResponse {
  items: Contrato[]
  total: number
  skip: number
  limit: number
}
