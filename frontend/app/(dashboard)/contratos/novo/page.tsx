'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api-client'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ChevronLeft, Plus, Trash2 } from 'lucide-react'
import type { Client } from '@/types'

interface ClausulaForm {
  titulo: string
  descricao: string
}

export default function NovoContratoPage() {
  const router = useRouter()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [clients, setClients] = useState<Client[]>([])
  const [error, setError] = useState<string | null>(null)

  // Form state
  const [titulo, setTitulo] = useState('')
  const [descricao, setDescricao] = useState('')
  const [tipo, setTipo] = useState('prestacao_servicos')
  const [clientId, setClientId] = useState('')
  const [valorTotal, setValorTotal] = useState('')
  const [valorMensal, setValorMensal] = useState('')
  const [valorEntrada, setValorEntrada] = useState('')
  const [percentualExito, setPercentualExito] = useState('')
  const [indiceReajuste, setIndiceReajuste] = useState('')
  const [dataInicio, setDataInicio] = useState('')
  const [dataVencimento, setDataVencimento] = useState('')
  const [diaVencimentoFatura, setDiaVencimentoFatura] = useState('10')
  const [observacoes, setObservacoes] = useState('')
  const [clausulas, setClausulas] = useState<ClausulaForm[]>([])

  useEffect(() => {
    apiClient.get('/clients', { params: { limit: 100 } }).then((res) => {
      setClients(res.data.items || res.data || [])
    }).catch(() => {})
  }, [])

  const addClausula = () => {
    setClausulas([...clausulas, { titulo: '', descricao: '' }])
  }

  const removeClausula = (index: number) => {
    setClausulas(clausulas.filter((_, i) => i !== index))
  }

  const updateClausula = (index: number, field: keyof ClausulaForm, value: string) => {
    const updated = [...clausulas]
    updated[index][field] = value
    setClausulas(updated)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    setError(null)

    try {
      const payload: Record<string, any> = {
        titulo,
        tipo,
        client_id: clientId,
        dia_vencimento_fatura: parseInt(diaVencimentoFatura) || 10,
      }

      if (descricao) payload.descricao = descricao
      if (valorTotal) payload.valor_total = parseFloat(valorTotal)
      if (valorMensal) payload.valor_mensal = parseFloat(valorMensal)
      if (valorEntrada) payload.valor_entrada = parseFloat(valorEntrada)
      if (percentualExito) payload.percentual_exito = parseFloat(percentualExito)
      if (indiceReajuste) payload.indice_reajuste = indiceReajuste
      if (dataInicio) payload.data_inicio = dataInicio
      if (dataVencimento) payload.data_vencimento = dataVencimento
      if (observacoes) payload.observacoes = observacoes
      if (clausulas.length > 0) {
        payload.clausulas = clausulas.filter(c => c.titulo.trim())
      }

      const res = await apiClient.post('/contratos', payload)
      router.push(`/contratos/${res.data.id}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao criar contrato')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center gap-4">
        <button
          onClick={() => router.push('/contratos')}
          className="inline-flex items-center text-accent hover:text-accent/80 text-sm font-medium transition-colors"
        >
          <ChevronLeft className="w-4 h-4 mr-1" /> Voltar
        </button>
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Novo Contrato</h1>
          <p className="mt-1 text-sm text-gray-600">
            Cadastre um novo contrato jurídico
          </p>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Info */}
        <Card>
          <CardHeader>
            <CardTitle>Informações Básicas</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <Label htmlFor="titulo">Título do Contrato *</Label>
                <Input
                  id="titulo"
                  value={titulo}
                  onChange={(e) => setTitulo(e.target.value)}
                  placeholder="Ex: Contrato de Prestação de Serviços Jurídicos"
                  required
                />
              </div>
              <div>
                <Label htmlFor="client_id">Cliente *</Label>
                <Select value={clientId} onValueChange={setClientId} required>
                  <SelectTrigger>
                    <SelectValue placeholder="Selecione o cliente" />
                  </SelectTrigger>
                  <SelectContent>
                    {clients.map((c) => (
                      <SelectItem key={c.id} value={c.id}>
                        {c.full_name || c.fullName}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="tipo">Tipo *</Label>
                <Select value={tipo} onValueChange={setTipo}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="prestacao_servicos">Prestação de Serviços</SelectItem>
                    <SelectItem value="honorarios_exito">Honorários de Êxito</SelectItem>
                    <SelectItem value="misto">Misto</SelectItem>
                    <SelectItem value="consultoria">Consultoria</SelectItem>
                    <SelectItem value="contencioso">Contencioso</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="md:col-span-2">
                <Label htmlFor="descricao">Descrição</Label>
                <Textarea
                  id="descricao"
                  value={descricao}
                  onChange={(e) => setDescricao(e.target.value)}
                  placeholder="Descrição detalhada do contrato..."
                  rows={3}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Financial */}
        <Card>
          <CardHeader>
            <CardTitle>Valores e Condições</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <Label htmlFor="valor_mensal">Valor Mensal (R$)</Label>
                <Input
                  id="valor_mensal"
                  type="number"
                  step="0.01"
                  min="0"
                  value={valorMensal}
                  onChange={(e) => setValorMensal(e.target.value)}
                  placeholder="0,00"
                />
              </div>
              <div>
                <Label htmlFor="valor_total">Valor Total (R$)</Label>
                <Input
                  id="valor_total"
                  type="number"
                  step="0.01"
                  min="0"
                  value={valorTotal}
                  onChange={(e) => setValorTotal(e.target.value)}
                  placeholder="0,00"
                />
              </div>
              <div>
                <Label htmlFor="valor_entrada">Entrada (R$)</Label>
                <Input
                  id="valor_entrada"
                  type="number"
                  step="0.01"
                  min="0"
                  value={valorEntrada}
                  onChange={(e) => setValorEntrada(e.target.value)}
                  placeholder="0,00"
                />
              </div>
              <div>
                <Label htmlFor="percentual_exito">Percentual de Êxito (%)</Label>
                <Input
                  id="percentual_exito"
                  type="number"
                  step="0.01"
                  min="0"
                  max="100"
                  value={percentualExito}
                  onChange={(e) => setPercentualExito(e.target.value)}
                  placeholder="0,00"
                />
              </div>
              <div>
                <Label htmlFor="indice_reajuste">Índice de Reajuste</Label>
                <Select value={indiceReajuste} onValueChange={setIndiceReajuste}>
                  <SelectTrigger>
                    <SelectValue placeholder="Selecione" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="igpm">IGP-M</SelectItem>
                    <SelectItem value="ipca">IPCA</SelectItem>
                    <SelectItem value="inpc">INPC</SelectItem>
                    <SelectItem value="selic">SELIC</SelectItem>
                    <SelectItem value="fixo">Fixo</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="dia_vencimento">Dia Vencimento Fatura</Label>
                <Input
                  id="dia_vencimento"
                  type="number"
                  min="1"
                  max="31"
                  value={diaVencimentoFatura}
                  onChange={(e) => setDiaVencimentoFatura(e.target.value)}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Dates */}
        <Card>
          <CardHeader>
            <CardTitle>Datas</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="data_inicio">Data de Início</Label>
                <Input
                  id="data_inicio"
                  type="date"
                  value={dataInicio}
                  onChange={(e) => setDataInicio(e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="data_vencimento">Data de Vencimento</Label>
                <Input
                  id="data_vencimento"
                  type="date"
                  value={dataVencimento}
                  onChange={(e) => setDataVencimento(e.target.value)}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Clausulas */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Cláusulas</CardTitle>
              <Button type="button" variant="outline" size="sm" onClick={addClausula}>
                <Plus className="h-4 w-4 mr-1" />
                Adicionar
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {clausulas.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-4">
                Nenhuma cláusula adicionada
              </p>
            ) : (
              clausulas.map((clausula, idx) => (
                <div key={idx} className="border rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <Label>Cláusula {idx + 1}</Label>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeClausula(idx)}
                    >
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                  <Input
                    placeholder="Título da cláusula"
                    value={clausula.titulo}
                    onChange={(e) => updateClausula(idx, 'titulo', e.target.value)}
                  />
                  <Textarea
                    placeholder="Descrição da cláusula"
                    value={clausula.descricao}
                    onChange={(e) => updateClausula(idx, 'descricao', e.target.value)}
                    rows={2}
                  />
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Observações */}
        <Card>
          <CardHeader>
            <CardTitle>Observações</CardTitle>
          </CardHeader>
          <CardContent>
            <Textarea
              value={observacoes}
              onChange={(e) => setObservacoes(e.target.value)}
              placeholder="Observações internas sobre o contrato..."
              rows={3}
            />
          </CardContent>
        </Card>

        {/* Submit */}
        <div className="flex justify-end gap-3">
          <Button type="button" variant="outline" onClick={() => router.push('/contratos')}>
            Cancelar
          </Button>
          <Button type="submit" disabled={isSubmitting || !titulo || !clientId}>
            {isSubmitting ? 'Criando...' : 'Criar Contrato'}
          </Button>
        </div>
      </form>
    </div>
  )
}
