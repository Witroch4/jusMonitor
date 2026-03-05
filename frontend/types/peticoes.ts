// Petition management types for JusMonitorIA

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
  | 'TRF5-JFAL'
  | 'TRF5-JFSE'
  | 'TRF5-JFPE'
  | 'TRF5-JFPB'
  | 'TRF5-JFRN'
  | 'TRF6-1G'
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
  sigiloso: boolean
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
  tipoPeticaoPje?: string
  descricaoPje?: string
  status: PeticaoStatus
  documentos: PeticaoDocumento[]
  certificadoId?: string
  dadosBasicos?: DadosBasicos
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
  totpConfigurado: boolean
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

// Tipo de vinculação por polo (espelho das opções PJe)
export const VINCULACOES_BY_POLO: Record<string, string[]> = {
  AT: [
    'LITISCONSORTE',
    'TERCEIRO INTERESSADO',
    'ASSISTENTE',
    'IMPETRANTE',
    'AUTOR',
    'REQUERENTE',
    'EXEQUENTE',
    'RECLAMANTE',
    'EMBARGANTE',
    'APELANTE',
    'RECORRENTE',
  ],
  PA: [
    'RÉU',
    'IMPETRADO',
    'REQUERIDO',
    'EXECUTADO',
    'RECLAMADO',
    'EMBARGADO',
    'APELADO',
    'RECORRIDO',
    'LITISCONSORTE',
    'TERCEIRO INTERESSADO',
    'ASSISTENTE',
  ],
  TC: [
    'TERCEIRO INTERESSADO',
    'LITISCONSORTE',
    'ASSISTENTE',
    'INTERVENIENTE',
    'AMICUS CURIAE',
    'FISCAL DA LEI',
  ],
}

// MNI 2.2.2 structured types
export interface Pessoa {
  nome: string
  tipoPessoa: 'fisica' | 'juridica' | 'entidade'
  tipoVinculacao?: string        // ex: IMPETRANTE, IMPETRADO, TERCEIRO INTERESSADO
  orgaoPublico?: boolean         // órgão público? sim/não (jurídica/entidade)
  cpf?: string
  semCpf?: boolean               // não possui CPF
  cnpj?: string
  semCnpj?: boolean              // não possui CNPJ
  nomeFantasia?: string          // nome fantasia (jurídica)
  sexo?: 'M' | 'F'
  dataNascimento?: string
}

export interface Advogado {
  nome: string
  inscricaoOAB: string
  cpf?: string
  tipoRepresentante?: string
  intimacao?: boolean
}

export interface Polo {
  polo: 'AT' | 'PA' | 'TC'
  partes: Pessoa[]
  advogados: Advogado[]
}

export interface OrgaoJulgador {
  codigoOrgao?: string
  nomeOrgao?: string
  codigoMunicipioIBGE?: number
  instancia?: string
}

export interface AssuntoProcessual {
  codigoNacional: number
  nome?: string
  principal: boolean
  hierarquia?: string
}

export interface DadosBasicos {
  polos: Polo[]
  orgaoJulgador?: OrgaoJulgador
  assuntos: AssuntoProcessual[]
  classeProcessual?: number
  classeProcessualNome?: string
  materiaCodigo?: number
  materiaNome?: string
  codigoLocalidade?: string
  competencia?: number
  nivelSigilo?: number
  valorCausa?: number
  prioridade?: string[]
  justicaGratuita?: boolean
  pedidoLiminar?: boolean
  juizoDigital?: boolean
}

export interface NovaPeticaoFormData {
  tribunalId: TribunalId | ''
  processoNumero: string
  tipoPeticao: TipoPeticao | ''
  assunto: string
  descricao: string
  certificadoId: string
  dadosBasicos?: DadosBasicos
  /** Label exato do select PJe (ex: 'Petição intercorrente') */
  tipoPeticaoPje?: string
  /** Descrição livre para o campo Descrição do formulário PJe */
  descricaoPje?: string
}

export interface UploadedFile {
  file: File
  id: string
  tipoDocumento: TipoDocumento
  sigiloso: boolean
  status: 'uploading' | 'uploaded' | 'error'
  erroValidacao?: string
}
