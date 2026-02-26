'use client'

import { useState } from 'react'
import { useLead, useUpdateLeadStage } from '@/hooks/api/useLeads'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import {
  Phone,
  Mail,
  User,
  TrendingUp,
  Clock,
  CheckCircle,
  AlertCircle,
  MessageSquare,
} from 'lucide-react'
import { formatDistanceToNow, format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

interface LeadDetailsModalProps {
  leadId: string
  onClose: () => void
}

export function LeadDetailsModal({ leadId, onClose }: LeadDetailsModalProps) {
  const { data: lead, isLoading } = useLead(leadId)
  const updateLeadStage = useUpdateLeadStage()
  const [isEditing, setIsEditing] = useState(false)

  if (isLoading || !lead) {
    return (
      <Dialog open={true} onOpenChange={onClose}>
        <DialogContent className="max-w-3xl">
          <div className="flex h-96 items-center justify-center">
            <div className="text-gray-500">Carregando...</div>
          </div>
        </DialogContent>
      </Dialog>
    )
  }

  const handleConvertToClient = async () => {
    try {
      await updateLeadStage.mutateAsync({ id: leadId, stage: 'convertido' })
      // TODO: Create client from lead
      onClose()
    } catch (error) {
      console.error('Failed to convert lead:', error)
    }
  }

  const getStageColor = (stage: string) => {
    const colors: Record<string, string> = {
      novo: 'bg-blue-100 text-blue-800',
      qualificado: 'bg-yellow-100 text-yellow-800',
      convertido: 'bg-green-100 text-green-800',
    }
    return colors[stage] || 'bg-gray-100 text-gray-800'
  }

  const getStageLabel = (stage: string) => {
    const labels: Record<string, string> = {
      novo: 'Novo',
      qualificado: 'Qualificado',
      convertido: 'Convertido',
    }
    return labels[stage] || stage
  }

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-start justify-between">
            <div>
              <DialogTitle className="text-2xl">{lead.full_name}</DialogTitle>
              <DialogDescription className="mt-2 flex items-center gap-2">
                <Badge className={getStageColor(lead.stage)}>
                  {getStageLabel(lead.stage)}
                </Badge>
                <span className="text-sm text-gray-500">
                  Criado {formatDistanceToNow(new Date(lead.created_at), { addSuffix: true, locale: ptBR })}
                </span>
              </DialogDescription>
            </div>
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-blue-500" />
              <span className="text-2xl font-bold text-blue-600">{lead.score}</span>
            </div>
          </div>
        </DialogHeader>

        <Tabs defaultValue="overview" className="mt-6">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="overview">Visão Geral</TabsTrigger>
            <TabsTrigger value="interactions">Interações</TabsTrigger>
            <TabsTrigger value="edit">Editar</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            {/* Contact Information */}
            <div className="rounded-lg border p-4">
              <h3 className="mb-4 font-semibold text-gray-900">Informações de Contato</h3>
              <div className="space-y-3">
                {lead.phone && (
                  <div className="flex items-center gap-3">
                    <Phone className="h-5 w-5 text-gray-400" />
                    <div>
                      <p className="text-sm text-gray-500">Telefone</p>
                      <p className="font-medium">{lead.phone}</p>
                    </div>
                  </div>
                )}
                {lead.email && (
                  <div className="flex items-center gap-3">
                    <Mail className="h-5 w-5 text-gray-400" />
                    <div>
                      <p className="text-sm text-gray-500">Email</p>
                      <p className="font-medium">{lead.email}</p>
                    </div>
                  </div>
                )}
                <div className="flex items-center gap-3">
                  <User className="h-5 w-5 text-gray-400" />
                  <div>
                    <p className="text-sm text-gray-500">Fonte</p>
                    <p className="font-medium capitalize">{lead.source}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Lead Score */}
            <div className="rounded-lg border p-4">
              <h3 className="mb-4 font-semibold text-gray-900">Score do Lead</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Pontuação atual</span>
                  <span className="text-2xl font-bold text-blue-600">{lead.score}/100</span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
                  <div
                    className="h-full bg-blue-600 transition-all"
                    style={{ width: `${lead.score}%` }}
                  />
                </div>
                <p className="text-sm text-gray-500">
                  {lead.score >= 70
                    ? 'Lead de alta prioridade - recomendado contato imediato'
                    : lead.score >= 40
                    ? 'Lead qualificado - agendar follow-up'
                    : 'Lead em qualificação - continuar nutrição'}
                </p>
              </div>
            </div>

            {/* Actions */}
            {lead.stage !== 'convertido' && (
              <div className="flex gap-3">
                <Button onClick={handleConvertToClient} className="flex-1">
                  <CheckCircle className="mr-2 h-4 w-4" />
                  Converter para Cliente
                </Button>
                <Button variant="outline" className="flex-1">
                  <MessageSquare className="mr-2 h-4 w-4" />
                  Enviar Mensagem
                </Button>
              </div>
            )}
          </TabsContent>

          {/* Interactions Tab */}
          <TabsContent value="interactions" className="space-y-4">
            <div className="rounded-lg border p-4">
              <h3 className="mb-4 font-semibold text-gray-900">Histórico de Interações</h3>
              
              {/* Mock interactions - in real app, fetch from API */}
              <div className="space-y-4">
                <div className="flex gap-3 border-l-2 border-blue-500 pl-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <MessageSquare className="h-4 w-4 text-blue-500" />
                      <span className="font-medium">Primeiro contato via Chatwit</span>
                    </div>
                    <p className="mt-1 text-sm text-gray-600">
                      Lead entrou em contato solicitando informações sobre serviços jurídicos
                    </p>
                    <p className="mt-1 text-xs text-gray-400">
                      {format(new Date(lead.created_at), "dd/MM/yyyy 'às' HH:mm", { locale: ptBR })}
                    </p>
                  </div>
                </div>

                <div className="flex gap-3 border-l-2 border-gray-300 pl-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <Clock className="h-4 w-4 text-gray-400" />
                      <span className="font-medium">Lead criado no sistema</span>
                    </div>
                    <p className="mt-1 text-sm text-gray-600">
                      Informações básicas registradas automaticamente
                    </p>
                    <p className="mt-1 text-xs text-gray-400">
                      {format(new Date(lead.created_at), "dd/MM/yyyy 'às' HH:mm", { locale: ptBR })}
                    </p>
                  </div>
                </div>
              </div>

              <div className="mt-6 rounded-lg bg-gray-50 p-4 text-center">
                <p className="text-sm text-gray-500">
                  Histórico completo de interações será implementado em breve
                </p>
              </div>
            </div>
          </TabsContent>

          {/* Edit Tab */}
          <TabsContent value="edit" className="space-y-4">
            <div className="rounded-lg border p-4">
              <h3 className="mb-4 font-semibold text-gray-900">Editar Informações</h3>
              
              <div className="space-y-4">
                <div>
                  <Label htmlFor="fullName">Nome Completo</Label>
                  <Input
                    id="fullName"
                    defaultValue={lead.full_name}
                    placeholder="Nome do lead"
                  />
                </div>

                <div>
                  <Label htmlFor="phone">Telefone</Label>
                  <Input
                    id="phone"
                    defaultValue={lead.phone || ''}
                    placeholder="(00) 00000-0000"
                  />
                </div>

                <div>
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    defaultValue={lead.email || ''}
                    placeholder="email@exemplo.com"
                  />
                </div>

                <div>
                  <Label htmlFor="source">Fonte</Label>
                  <Input
                    id="source"
                    defaultValue={lead.source}
                    placeholder="Origem do lead"
                  />
                </div>

                <div className="flex gap-3 pt-4">
                  <Button className="flex-1">
                    Salvar Alterações
                  </Button>
                  <Button variant="outline" className="flex-1" onClick={onClose}>
                    Cancelar
                  </Button>
                </div>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
