export type FaturaStatus = 'pendente' | 'paga' | 'vencida' | 'cancelada' | 'parcial'
export type FormaPagamento = 'pix' | 'boleto' | 'transferencia' | 'cartao' | 'dinheiro'
export type LancamentoTipo = 'receita' | 'despesa'
export type LancamentoCategoria = 'honorarios' | 'custas' | 'pericia' | 'deslocamento' | 'exito' | 'outros'

export interface Fatura {
  id: string
  tenant_id: string
  contrato_id: string
  client_id: string
  numero: string
  referencia?: string
  valor: number
  valor_pago: number
  data_vencimento: string
  data_pagamento?: string
  status: FaturaStatus
  forma_pagamento?: FormaPagamento
  observacoes?: string
  nosso_numero?: string
  client_name?: string
  contrato_titulo?: string
  created_at: string
  updated_at: string
}

export interface FaturaListResponse {
  items: Fatura[]
  total: number
  skip: number
  limit: number
}

export interface Lancamento {
  id: string
  tenant_id: string
  contrato_id?: string
  fatura_id?: string
  client_id?: string
  tipo: LancamentoTipo
  categoria: LancamentoCategoria
  descricao: string
  valor: number
  data_lancamento: string
  data_competencia?: string
  observacoes?: string
  contrato_titulo?: string
  client_name?: string
  created_at: string
  updated_at: string
}

export interface LancamentoListResponse {
  items: Lancamento[]
  total: number
  skip: number
  limit: number
}

export interface ResumoReceitas {
  total_faturado: number
  total_recebido: number
  total_a_receber: number
  total_em_atraso: number
}

export interface FinanceiroDashboard {
  resumo: ResumoReceitas
  contratos_ativos: number
  faturas_pendentes: number
  faturas_vencidas: number
  receita_por_mes: Array<{ mes: string; valor: number }>
}
