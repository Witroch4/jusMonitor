import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'

export interface TpuItem {
  cod_item: number
  nome: string
  descricao_glossario?: string
  hierarquia?: string
}

// Backend returns { codigo, nome, glossario, hierarquia } via Pydantic camelCase
interface TpuApiItem {
  codigo: number
  nome: string
  glossario?: string
  hierarquia?: string
}

function mapApiToTpuItem(raw: TpuApiItem): TpuItem {
  return {
    cod_item: raw.codigo,
    nome: raw.nome,
    descricao_glossario: raw.glossario,
    hierarquia: raw.hierarquia,
  }
}

/** Lista matérias (assuntos raiz) — equivalente ao campo Matéria do PJe */
export function useTpuMaterias() {
  return useQuery({
    queryKey: ['tpu', 'materias'],
    queryFn: async (): Promise<TpuItem[]> => {
      const { data } = await apiClient.get<TpuApiItem[]>('/tpu/materias')
      return data.map(mapApiToTpuItem)
    },
    staleTime: 5 * 60_000, // 5 min — rarely changes
  })
}

export function useTpuClasses(query: string) {
  const isPopular = query.length === 0
  return useQuery({
    queryKey: ['tpu', 'classes', query || '__popular__'],
    queryFn: async (): Promise<TpuItem[]> => {
      const params: Record<string, string | number | boolean> = {}
      if (isPopular) {
        params.popular = true
      } else if (/^\d+$/.test(query)) {
        params.codigo = Number(query)
      } else {
        params.q = query
      }
      const { data } = await apiClient.get<TpuApiItem[]>('/tpu/classes', { params })
      return data.map(mapApiToTpuItem)
    },
    enabled: isPopular || query.length >= 2,
    staleTime: 60_000,
  })
}

/** Busca assuntos filtrados pela matéria selecionada */
export function useTpuAssuntos(query: string, materiaCodigo?: number) {
  const isPopular = query.length === 0
  return useQuery({
    queryKey: ['tpu', 'assuntos', query || '__popular__', materiaCodigo ?? '__all__'],
    queryFn: async (): Promise<TpuItem[]> => {
      const params: Record<string, string | number | boolean> = {}
      if (materiaCodigo) {
        params.materia = materiaCodigo
      }
      if (isPopular) {
        params.popular = true
      } else if (/^\d+$/.test(query)) {
        params.codigo = Number(query)
      } else {
        params.q = query
      }
      const { data } = await apiClient.get<TpuApiItem[]>('/tpu/assuntos', { params })
      return data.map(mapApiToTpuItem)
    },
    // Need either a matéria selected (shows children) or a query typed, or popular mode
    enabled: materiaCodigo != null || isPopular || query.length >= 2,
    staleTime: 60_000,
  })
}
