import { useCallback, useMemo } from 'react'
import type { DatajudResponse } from '@/hooks/api/useProcessos'
import {
  useProcessosMonitoradosAPI,
  useAdicionarProcessoMonitorado,
  useRemoverProcessoMonitorado,
  useConsultarProcessoMonitorado,
  useMarcarVistoProcessoMonitorado,
  type ProcessoMonitoradoDB,
} from '@/hooks/api/useProcessosMonitorados'

export interface ProcessoMonitorado {
  id: string
  numero: string
  apelido?: string
  adicionadoEm: string
  ultimaConsulta?: string
  dados?: DatajudResponse
  movimentacoesConhecidas?: number
  novasMovimentacoes?: number
  origemPeticao?: boolean
}

function mapFromDB(p: ProcessoMonitoradoDB): ProcessoMonitorado {
  return {
    id: p.id,
    numero: p.numero,
    apelido: p.apelido ?? undefined,
    adicionadoEm: p.criadoEm,
    ultimaConsulta: p.ultimaConsulta ?? undefined,
    dados: p.dadosDatajud as DatajudResponse | undefined,
    movimentacoesConhecidas: p.movimentacoesConhecidas,
    novasMovimentacoes: p.novasMovimentacoes,
    origemPeticao: !!p.peticaoId,
  }
}

export function useProcessosMonitorados() {
  const { data, isLoading } = useProcessosMonitoradosAPI()
  const adicionarMut = useAdicionarProcessoMonitorado()
  const removerMut = useRemoverProcessoMonitorado()
  const consultarMut = useConsultarProcessoMonitorado()
  const marcarVistoMut = useMarcarVistoProcessoMonitorado()

  const processos = useMemo<ProcessoMonitorado[]>(
    () => (data?.items ?? []).map(mapFromDB),
    [data],
  )

  const adicionar = useCallback(
    async (numero: string, apelido?: string): Promise<string> => {
      const created = await adicionarMut.mutateAsync({ numero, apelido })
      return created.id
    },
    [adicionarMut],
  )

  const remover = useCallback(
    (id: string) => {
      removerMut.mutate(id)
    },
    [removerMut],
  )

  const consultarProcesso = useCallback(
    async (id: string) => {
      await consultarMut.mutateAsync(id)
    },
    [consultarMut],
  )

  const marcarVisto = useCallback(
    (id: string) => {
      marcarVistoMut.mutate(id)
    },
    [marcarVistoMut],
  )

  const precisamAtualizar = useCallback((): ProcessoMonitorado[] => {
    const DOZE_HORAS = 12 * 60 * 60 * 1000
    const agora = Date.now()
    return processos.filter((p) => {
      if (!p.ultimaConsulta) return true
      return agora - new Date(p.ultimaConsulta).getTime() > DOZE_HORAS
    })
  }, [processos])

  return {
    processos,
    isLoading,
    adicionar,
    remover,
    consultarProcesso,
    marcarVisto,
    precisamAtualizar,
  }
}
