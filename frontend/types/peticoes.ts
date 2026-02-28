// Petition management types for JusMonitor

export type PeticaoStatus =
  | 'rascunho'
  | 'validando'
  | 'assinando'
  | 'protocolando'
  | 'protocolada'
  | 'aceita'
  | 'rejeitada'

export type TipoPeticao =
  | 'peticao_inicial'
  | 'contestacao'
  | 'recurso_apelacao'
  | 'agravo_instrumento'
  | 'embargos_declaracao'
  | 'habeas_corpus'
  | 'mandado_seguranca'
  | 'manifestacao'
  | 'outro'

export const TIPO_PETICAO_LABELS: Record<TipoPeticao, string> = {
  peticao_inicial: 'Petição Inicial',
  contestacao: 'Contestação',
  recurso_apelacao: 'Recurso de Apelação',
  agravo_instrumento: 'Agravo de Instrumento',
  embargos_declaracao: 'Embargos de Declaração',
  habeas_corpus: 'Habeas Corpus',
  mandado_seguranca: 'Mandado de Segurança',
  manifestacao: 'Manifestação',
  outro: 'Outro',
}

export const STATUS_LABELS: Record<PeticaoStatus, string> = {
  rascunho: 'Rascunho',
  validando: 'Validando',
  assinando: 'Assinando',
  protocolando: 'Protocolando',
  protocolada: 'Protocolada',
  aceita: 'Aceita',
  rejeitada: 'Rejeitada',
}

export type SistemaJudicial = 'PJe' | 'e-SAJ' | 'EPROC' | 'PJe-CSJT'

export type TribunalId =
  | 'TJCE-1G'
  | 'TJCE-2G'
  | 'TRF5-JFCE'
  | 'TRF5-REG'
  | 'TRT7'
  | 'TRF3-1G'
  | 'TRF3-2G'
  | 'TRF1-1G'
  | 'TRF1-2G'
  | 'TRF4'
  | 'TJSP'
  | 'STF'
  | 'STJ'

export type JurisdicaoGrupo = 'Estadual' | 'Federal' | 'Trabalho' | 'Superior'

export interface Tribunal {
  id: TribunalId
  nome: string
  nomeCompleto: string
  instancia: string
  jurisdicao: JurisdicaoGrupo
  sistema: SistemaJudicial
  wsdlEndpoint: string | null
  limiteArquivoMB: number
  requerMTLS: boolean
  suportaMNI: boolean
  avisoInstabilidade?: string
}

export type TipoDocumento = 'peticao_principal' | 'procuracao' | 'anexo' | 'comprovante'

export const TIPO_DOCUMENTO_LABELS: Record<TipoDocumento, string> = {
  peticao_principal: 'Petição Principal',
  procuracao: 'Procuração',
  anexo: 'Anexo',
  comprovante: 'Comprovante',
}

export interface PeticaoDocumento {
  id: string
  nomeOriginal: string
  tamanhoBytes: number
  tipoDocumento: TipoDocumento
  ordem: number
  uploadedAt: string
  status: 'uploading' | 'uploaded' | 'error' | 'validado'
  erroValidacao?: string
}

export interface AnaliseIA {
  consistenciaJuridica: number
  jurisprudencia: number
  formatacao: number
  pontuacaoGeral: number
  feedback: string
  sugestoes: string[]
  analisadoEm: string
  tempoAnaliseMs: number
}

export interface Peticao {
  id: string
  tenantId: string
  numeroProtocolo?: string
  processoNumero: string
  tribunalId: TribunalId
  tipoPeticao: TipoPeticao
  assunto: string
  descricao?: string
  status: PeticaoStatus
  documentos: PeticaoDocumento[]
  certificadoId?: string
  analiseIA?: AnaliseIA
  protocoladoEm?: string
  protocoloRecibo?: string
  motivoRejeicao?: string
  criadoPor: string
  criadoEm: string
  atualizadoEm: string
}

export interface PeticaoListItem {
  id: string
  numeroProtocolo?: string
  processoNumero: string
  tribunalId: TribunalId
  tipoPeticao: TipoPeticao
  assunto: string
  status: PeticaoStatus
  protocoladoEm?: string
  criadoEm: string
  quantidadeDocumentos: number
}

export interface PeticaoFilters {
  search?: string
  status?: PeticaoStatus | 'all'
  tribunalId?: TribunalId | 'all'
}

export interface CertificadoDigital {
  id: string
  tenantId: string
  nome: string
  titularNome: string
  titularCpfCnpj: string
  emissora: string
  serialNumber: string
  validoAte: string
  status: 'valido' | 'expirando' | 'expirado'
  criptografia: 'AES-128-CBC'
  ultimoTesteEm?: string
  ultimoTesteResultado?: 'sucesso' | 'falha'
  criadoEm: string
}

export interface PeticaoEvento {
  id: string
  peticaoId: string
  status: PeticaoStatus
  descricao: string
  detalhes?: string
  criadoEm: string
}

export interface NovaPeticaoFormData {
  tribunalId: TribunalId | ''
  processoNumero: string
  tipoPeticao: TipoPeticao | ''
  assunto: string
  descricao: string
  certificadoId: string
}

export interface UploadedFile {
  file: File
  id: string
  tipoDocumento: TipoDocumento
  status: 'uploading' | 'uploaded' | 'error'
  erroValidacao?: string
}
