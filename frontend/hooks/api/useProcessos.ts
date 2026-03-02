import { useMutation } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { ProcessoConsultaResponse, ConsultarOABResponse } from '@/types/processos'

export function useConsultarProcessoMNI() {
  return useMutation({
    mutationFn: async (params: {
      numeroProcesso: string
      tribunalId: string
      certificadoId: string
    }): Promise<ProcessoConsultaResponse> => {
      const { data } = await apiClient.post<ProcessoConsultaResponse>(
        '/processos/consultar',
        {
          numeroProcesso: params.numeroProcesso,
          tribunalId: params.tribunalId,
          certificadoId: params.certificadoId,
        }
      )
      return data
    },
  })
}

export interface DatajudMovimento {
  dataHora?: string
  codigo?: number
  nome?: string
  complementos?: string[]
  orgaoJulgador?: string
}

export interface DatajudAssunto {
  codigo?: number
  nome?: string
  principal?: boolean
}

export interface DatajudOrgaoJulgador {
  codigo?: string
  nome?: string
  codigoMunicipioIbge?: number
}

export interface DatajudProcesso {
  id: string
  numeroProcesso: string
  numeroProcessoFormatado: string
  tribunal?: string
  grau?: string
  sistema?: string
  formato?: string
  classe?: { codigo?: number; nome?: string }
  dataAjuizamento?: string
  nivelSigilo?: number
  dataUltimaAtualizacao?: string
  orgaoJulgador?: DatajudOrgaoJulgador
  assuntos?: DatajudAssunto[]
  movimentos?: DatajudMovimento[]
  indiceDatajud?: string
}

export interface DatajudResponse {
  sucesso: boolean
  mensagem: string
  processo?: DatajudProcesso
  hits?: DatajudProcesso[]
  total?: number
  alias?: string
}

export async function consultarDatajudFn(params: {
  numeroProcesso: string
  tribunalId?: string
}): Promise<DatajudResponse> {
  const { data } = await apiClient.post<DatajudResponse>(
    '/processos/consultar-datajud',
    {
      numero_processo: params.numeroProcesso,
      tribunal_id: params.tribunalId || null,
    },
  )
  return data
}

export function useConsultarDatajud() {
  return useMutation({
    mutationFn: consultarDatajudFn,
  })
}

// --- OAB Finder ---

export function useConsultarOAB() {
  return useMutation({
    mutationFn: async (params: {
      oabNumero: string
      oabUf: string
    }): Promise<ConsultarOABResponse> => {
      const { data } = await apiClient.post<ConsultarOABResponse>(
        '/processos/consultar-oab',
        {
          oabNumero: params.oabNumero,
          oabUf: params.oabUf,
        }
      )
      return data
    },
  })
}
