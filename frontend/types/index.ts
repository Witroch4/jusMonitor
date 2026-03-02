// Common types for the application

export interface User {
  id: string
  email: string
  fullName: string
  role: 'super_admin' | 'admin' | 'advogado' | 'assistente' | 'visualizador'
  tenantId: string
  isActive: boolean
  phone?: string
  avatarUrl?: string
  oabNumber?: string
  oabState?: string
  oabFormatted?: string
}

export interface Tenant {
  id: string
  name: string
  slug: string
  plan: string
  isActive: boolean
}

export interface Lead {
  id: string
  tenantId: string
  fullName: string
  phone?: string
  email?: string
  source: string
  stage: 'novo' | 'qualificado' | 'convertido'
  score: number
  status: string
  createdAt: string
  updatedAt: string
  instagramUsername?: string
  instagramProfilePictureUrl?: string
}

export interface Client {
  id: string
  tenantId: string
  fullName: string
  cpfCnpj?: string
  email?: string
  phone?: string
  status: string
  healthScore?: number
  createdAt: string
  updatedAt: string
  // properties used by Overview.tsx
  full_name?: string
  cpf_cnpj?: string
  health_score?: number
  active_cases_count?: number
  total_cases_count?: number
  last_interaction?: string
  last_interaction_type?: string
  alerts?: any[]
}

export interface LegalCase {
  id: string
  tenantId: string
  clientId: string
  cnjNumber: string
  court?: string
  caseType?: string
  subject?: string
  status?: string
  filingDate?: string
  lastMovementDate?: string
  nextDeadline?: string
  monitoringEnabled: boolean
  createdAt: string
  updatedAt: string
}

export interface Movement {
  id: string
  tenantId: string
  processId: string
  movementDate: string
  movementType?: string
  description: string
  isImportant: boolean
  requiresAction: boolean
  aiSummary?: string
  createdAt: string
}

export interface ApiResponse<T> {
  data: T
  message?: string
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

export interface ApiError {
  detail: string
  code?: string
}

// Dashboard types
export interface UrgentCaseItem {
  caseId: string
  cnjNumber: string
  clientId: string
  clientName: string
  nextDeadline: string
  daysRemaining: number
  caseType?: string
  court?: string
  lastMovementDate?: string
}

export interface AttentionCaseItem {
  caseId: string
  cnjNumber: string
  clientId: string
  clientName: string
  lastMovementDate?: string
  daysSinceMovement: number
  caseType?: string
  court?: string
  status?: string
}

export interface GoodNewsItem {
  caseId: string
  cnjNumber: string
  clientId: string
  clientName: string
  movementId: string
  movementDate: string
  movementType?: string
  description: string
  aiSummary?: string
}

export interface NoiseItem {
  caseId: string
  cnjNumber: string
  clientId: string
  clientName: string
  movementId: string
  movementDate: string
  movementType?: string
  description: string
}

export interface OfficeMetrics {
  conversionRate: number
  conversionRateChange: number
  avgResponseTimeHours: number
  avgResponseTimeChange: number
  satisfactionScore: number
  satisfactionScoreChange: number
  totalActiveCases: number
  newCasesThisPeriod: number
  totalActiveClients: number
  newClientsThisPeriod: number
}

export interface DashboardMetrics {
  metrics: OfficeMetrics
  periodStart: string
  periodEnd: string
  comparisonPeriodStart: string
  comparisonPeriodEnd: string
}

// Petition types
export type {
  PeticaoStatus,
  TipoPeticao,
  TribunalId,
  Tribunal,
  PeticaoDocumento,
  AnaliseIA,
  Peticao,
  PeticaoListItem,
  PeticaoFilters,
  CertificadoDigital,
  PeticaoEvento,
  NovaPeticaoFormData,
  UploadedFile,
} from './peticoes'

// Profile types (snake_case matching backend API response)
export interface UserProfile {
  user_id: string
  email: string
  full_name: string
  role: string
  tenant_id: string
  phone?: string
  avatar_url?: string
  oab_number?: string
  oab_state?: string
  oab_formatted?: string
  cpf?: string
  cpf_formatted?: string
}

export interface UpdateProfileData {
  full_name?: string
  phone?: string
  oab_number?: string
  oab_state?: string
  cpf?: string
}

export interface ChangePasswordData {
  current_password: string
  new_password: string
  confirm_password: string
}

// Integration types
export interface InstagramStatus {
  connected: boolean
  username?: string
  profile_picture_url?: string
  token_expires_at?: string
}
