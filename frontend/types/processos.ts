// Types for MNI 2.2.2 process consultation response

export interface ProcessoAdvogado {
  nome: string
  inscricao?: string | null // OAB
  cpf?: string | null
  tipoRepresentante?: string | null
}

export interface ProcessoParte {
  nome: string
  documento?: string | null // CPF or CNPJ
  tipoPessoa?: string | null
  sexo?: string | null
  advogados: ProcessoAdvogado[]
}

export interface ProcessoPolo {
  polo: string // AT, PA, TC, FL, etc.
  poloLabel: string // "Ativo", "Passivo", etc.
  partes: ProcessoParte[]
}

export interface ProcessoAssunto {
  codigoNacional?: number | null
  codigoLocal?: number | null
  descricao?: string | null
  principal: boolean
}

export interface ProcessoOrgaoJulgador {
  codigoOrgao?: string | null
  nomeOrgao?: string | null
  codigoMunicipioIbge?: number | null
  instancia?: string | null
}

export interface ProcessoMovimento {
  dataHora?: string | null
  codigoNacional?: number | null
  descricao?: string | null
  complementos: string[]
}

export interface ProcessoDocumentoInfo {
  idDocumento?: string | null
  tipoDocumento?: string | null
  descricao?: string | null
  mimetype?: string | null
  dataHora?: string | null
  nivelSigilo?: number | null
}

export interface ProcessoCabecalho {
  numero?: string | null
  classeProcessual?: number | null
  classeProcessualDescricao?: string | null
  codigoLocalidade?: string | null
  competencia?: number | null
  nivelSigilo: number
  dataAjuizamento?: string | null
  valorCausa?: number | null
}

export interface ProcessoConsultaResponse {
  sucesso: boolean
  mensagem: string
  cabecalho?: ProcessoCabecalho | null
  polos: ProcessoPolo[]
  assuntos: ProcessoAssunto[]
  orgaoJulgador?: ProcessoOrgaoJulgador | null
  movimentos: ProcessoMovimento[]
  documentos: ProcessoDocumentoInfo[]
  raw?: Record<string, unknown> | null
}

// --- OAB Finder (web scraping) ---

export interface OABProcessoResumo {
  numero: string
  classe?: string | null
  assunto?: string | null
  partes?: string | null
  ultimaMovimentacao?: string | null
  dataUltimaMovimentacao?: string | null
}

export interface ConsultarOABResponse {
  sucesso: boolean
  mensagem: string
  processos: OABProcessoResumo[]
  total: number
}
