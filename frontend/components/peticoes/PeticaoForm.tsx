'use client'

import { useState, useCallback, useEffect } from 'react'
import { PeticaoFormDadosProcesso } from './PeticaoFormDadosProcesso'
import { PeticaoFormPartes } from './PeticaoFormPartes'
import { PeticaoFormAssuntos } from './PeticaoFormAssuntos'
import { PeticaoFormCaracteristicas } from './PeticaoFormCaracteristicas'
import { PeticaoFormUpload } from './PeticaoFormUpload'
import { PeticaoFormCertificado } from './PeticaoFormCertificado'
import { PeticaoFormRevisao, useRevisaoValidation } from './PeticaoFormRevisao'
import { PeticaoAnaliseIA } from './PeticaoAnaliseIA'
import { CertificadoModal } from './CertificadoModal'
import { useCreatePeticao, useUpdatePeticao, useUploadDocumento, useProtocolar, usePeticao, useDeleteDocumento } from '@/hooks/api/usePeticoes'
import { useQueryClient } from '@tanstack/react-query'
import { useProfile } from '@/hooks/api/useProfile'
import { TRIBUNAIS } from '@/lib/data/tribunais'
import type { NovaPeticaoFormData, UploadedFile, AnaliseIA, Polo, AssuntoProcessual } from '@/types/peticoes'
import { ChevronLeft } from 'lucide-react'
import { toast } from 'sonner'

interface Props {
  onVoltar: () => void
  rascunhoId?: string
  initialProcessoNumero?: string
}

const INITIAL_FORM: NovaPeticaoFormData = {
  tribunalId: '',
  processoNumero: '',
  tipoPeticao: '',
  assunto: '',
  descricao: '',
  certificadoId: '',
  dadosBasicos: {
    polos: [
      { polo: 'AT', partes: [{ nome: '', tipoPessoa: 'fisica' }], advogados: [{ nome: '', inscricaoOAB: '', intimacao: true }] },
      { polo: 'PA', partes: [{ nome: '', tipoPessoa: 'fisica' }], advogados: [] },
    ],
    assuntos: [],
  },
}

export function PeticaoForm({ onVoltar, rascunhoId, initialProcessoNumero }: Props) {
  const isEditMode = !!rascunhoId
  const [formData, setFormData] = useState<NovaPeticaoFormData>(() => (
    initialProcessoNumero ? { ...INITIAL_FORM, processoNumero: initialProcessoNumero } : INITIAL_FORM
  ))
  const [formPopulated, setFormPopulated] = useState(false)
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [analise, setAnalise] = useState<AnaliseIA | null>(null)
  const [certModalOpen, setCertModalOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const queryClient = useQueryClient()
  const createPeticao = useCreatePeticao()
  const updatePeticao = useUpdatePeticao()
  const uploadDocumento = useUploadDocumento()
  const deleteDocumento = useDeleteDocumento()
  const protocolar = useProtocolar()

  // Fetch existing draft when editing
  const { data: rascunho, isLoading: isLoadingRascunho } = usePeticao(rascunhoId ?? '')

  // Pre-populate form from fetched draft
  useEffect(() => {
    if (!isEditMode || formPopulated || !rascunho) return
    setFormData({
      tribunalId: rascunho.tribunalId ?? '',
      processoNumero: rascunho.processoNumero ?? '',
      tipoPeticao: rascunho.tipoPeticao ?? '',
      assunto: rascunho.assunto ?? '',
      descricao: rascunho.descricao ?? '',
      certificadoId: rascunho.certificadoId ?? '',
      dadosBasicos: INITIAL_FORM.dadosBasicos,
      tipoPeticaoPje: rascunho.tipoPeticaoPje ?? '',
      descricaoPje: rascunho.descricaoPje ?? '',
    })
    setFormPopulated(true)
  }, [rascunho, isEditMode, formPopulated])
  const { data: profile } = useProfile()

  // Auto-preencher advogado do Polo Ativo com dados do perfil do usuário
  useEffect(() => {
    if (!profile?.oab_number) return
    setFormData((prev) => {
      const poloAt = prev.dadosBasicos?.polos.find((p) => p.polo === 'AT')
      const adv = poloAt?.advogados[0]
      // Só preenche se ainda estiver vazio (não sobrescreve edição manual)
      if (adv && !adv.nome && !adv.inscricaoOAB) {
        const oab = `${profile.oab_state || ''}${profile.oab_number}`
        return {
          ...prev,
          dadosBasicos: {
            ...prev.dadosBasicos!,
            polos: prev.dadosBasicos!.polos.map((p) =>
              p.polo === 'AT'
                ? { ...p, advogados: [{ nome: profile.full_name || '', inscricaoOAB: oab, cpf: profile.cpf || '', intimacao: true }] }
                : p
            ),
          },
        }
      }
      return prev
    })
  }, [profile])
  const isValid = useRevisaoValidation(formData, files, null, isEditMode ? (rascunho?.documentos ?? []) : [])

  const updateDadosBasicos = useCallback((partial: Partial<NovaPeticaoFormData['dadosBasicos']>) => {
    setFormData((prev) => ({
      ...prev,
      dadosBasicos: { ...prev.dadosBasicos!, ...partial },
    }))
  }, [])

  const tribunal = TRIBUNAIS.find((t) => t.id === formData.tribunalId)
  const limiteArquivoMB = tribunal?.limiteArquivoMB ?? 5

  const updateForm = useCallback((partial: Partial<NovaPeticaoFormData>) => {
    setFormData((prev) => ({ ...prev, ...partial }))
  }, [])

  const hasUploadedFiles = files.some((f) => f.status === 'uploaded')

  const handleReanalisar = () => {
    setAnalise(null)
  }

  const handleProtocolar = async () => {
    if (!isValid || isSubmitting) return
    setIsSubmitting(true)

    try {
      let peticaoId: string

      if (isEditMode && rascunhoId) {
        // Update existing draft first
        await updatePeticao.mutateAsync({
          id: rascunhoId,
          tribunalId: formData.tribunalId || undefined,
          processoNumero: formData.processoNumero || undefined,
          tipoPeticao: formData.tipoPeticao || undefined,
          assunto: formData.assunto || undefined,
          descricao: formData.descricao || undefined,
          certificadoId: formData.certificadoId || undefined,
        })
        peticaoId = rascunhoId
      } else {
        // Create new petition
        const peticao = await createPeticao.mutateAsync(formData)
        peticaoId = peticao.id
      }

      // Upload any new files
      const uploadedFiles = files.filter((f) => f.status === 'uploaded')
      for (let i = 0; i < uploadedFiles.length; i++) {
        const f = uploadedFiles[i]
        await uploadDocumento.mutateAsync({
          peticaoId,
          arquivo: f.file,
          tipoDocumento: f.tipoDocumento,
          ordem: i + 1,
          sigiloso: f.sigiloso,
        })
      }

      // Trigger filing via worker
      await protocolar.mutateAsync(peticaoId)

      queryClient.invalidateQueries({ queryKey: ['peticoes', 'protocoladas'] })
      toast.success('Petição enviada para protocolo!')
      onVoltar()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Erro ao protocolar petição'
      toast.error(msg)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleSalvarRascunho = async () => {
    if (isSubmitting) return
    const minValid =
      !!formData.tribunalId &&
      !!formData.tipoPeticao
    if (!minValid) {
      toast.error('Preencha tribunal e tipo de petição para salvar o rascunho.')
      return
    }
    setIsSubmitting(true)

    try {
      let peticaoId: string

      if (isEditMode && rascunhoId) {
        // Update existing draft
        await updatePeticao.mutateAsync({
          id: rascunhoId,
          tribunalId: formData.tribunalId || undefined,
          processoNumero: formData.processoNumero || undefined,
          tipoPeticao: formData.tipoPeticao || undefined,
          assunto: formData.assunto || undefined,
          descricao: formData.descricao || undefined,
          certificadoId: formData.certificadoId || undefined,
        })
        peticaoId = rascunhoId
      } else {
        const peticao = await createPeticao.mutateAsync(formData)
        peticaoId = peticao.id
      }

      // Upload any new files
      const uploadedFiles = files.filter((f) => f.status === 'uploaded')
      for (let i = 0; i < uploadedFiles.length; i++) {
        const f = uploadedFiles[i]
        await uploadDocumento.mutateAsync({
          peticaoId,
          arquivo: f.file,
          tipoDocumento: f.tipoDocumento,
          ordem: i + 1,
          sigiloso: f.sigiloso,
        })
      }

      toast.success('Rascunho salvo com sucesso!')
      onVoltar()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Erro ao salvar rascunho'
      toast.error(msg)
    } finally {
      setIsSubmitting(false)
    }
  }

  if (isEditMode && isLoadingRascunho) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-48 bg-muted animate-pulse rounded" />
        <div className="h-6 w-96 bg-muted animate-pulse rounded" />
        <div className="h-[400px] w-full bg-muted animate-pulse rounded-xl" />
      </div>
    )
  }

  return (
    <>
      <div className="min-h-full pb-28">
        {/* Header */}
        <header className="flex flex-col md:flex-row md:items-start justify-between gap-4 mb-8">
          <div>
            <button
              onClick={onVoltar}
              className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors mb-3"
            >
              <ChevronLeft className="h-4 w-4" />
              Voltar para Petições
            </button>
            <h1 className="font-display text-3xl md:text-4xl font-bold text-foreground mb-1">
              {isEditMode ? 'Continuar Petição' : 'Nova Petição'}
            </h1>
            <p className="text-muted-foreground text-base">
              Preencha os dados e protocole eletronicamente
            </p>
          </div>
        </header>

        {/* Main grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left column - Form sections */}
          <div className="lg:col-span-2 space-y-6">
            <PeticaoFormDadosProcesso
              formData={formData}
              onChange={updateForm}
              dadosBasicos={formData.dadosBasicos}
              onDadosBasicosChange={updateDadosBasicos}
            />
            <PeticaoFormAssuntos
              classeProcessual={formData.dadosBasicos?.classeProcessual}
              classeProcessualNome={formData.dadosBasicos?.classeProcessualNome}
              materiaCodigo={formData.dadosBasicos?.materiaCodigo}
              materiaNome={formData.dadosBasicos?.materiaNome}
              assuntos={formData.dadosBasicos?.assuntos || []}
              onClasseChange={(codigo, nome) =>
                updateDadosBasicos({ classeProcessual: codigo, classeProcessualNome: nome })
              }
              onMateriaChange={(codigo, nome) =>
                updateDadosBasicos({ materiaCodigo: codigo, materiaNome: nome })
              }
              onAssuntosChange={(assuntos: AssuntoProcessual[]) => updateDadosBasicos({ assuntos })}
            />
            <PeticaoFormPartes
              polos={formData.dadosBasicos?.polos || []}
              onChange={(polos: Polo[]) => updateDadosBasicos({ polos })}
            />
            <PeticaoFormCaracteristicas
              dadosBasicos={formData.dadosBasicos || { polos: [], assuntos: [] }}
              onChange={updateDadosBasicos}
            />
            <PeticaoFormUpload
              files={files}
              onFilesChange={setFiles}
              limiteArquivoMB={limiteArquivoMB}
              existingDocuments={isEditMode ? (rascunho?.documentos ?? []) : []}
              onDeleteExisting={isEditMode && rascunhoId ? (docId) => {
                deleteDocumento.mutate({ peticaoId: rascunhoId, docId })
              } : undefined}
            />
            <PeticaoFormRevisao formData={formData} files={files} analise={analise} existingDocuments={isEditMode ? (rascunho?.documentos ?? []) : []} />
          </div>

          {/* Right column - AI + Certificate */}
          <div className="lg:col-span-1 space-y-4">
            <PeticaoAnaliseIA
              analise={analise}
              isAnalyzing={false}
              hasDocuments={hasUploadedFiles}
              onReanalisar={handleReanalisar}
            />
            <PeticaoFormCertificado
              certificadoId={formData.certificadoId}
              onChange={(id) => updateForm({ certificadoId: id })}
              onOpenModal={() => setCertModalOpen(true)}
            />
          </div>
        </div>

        {/* Fixed action bar */}
        <div className="fixed bottom-0 left-0 right-0 z-20 p-4 md:p-6 flex justify-center pointer-events-none">
          <div className="pointer-events-auto flex items-center gap-3">
            <button
              onClick={handleSalvarRascunho}
              disabled={isSubmitting}
              className="flex items-center gap-2 px-6 py-4 rounded-2xl font-semibold text-sm shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed bg-card border border-border text-foreground hover:bg-muted"
            >
              <span className="material-symbols-outlined text-lg">save</span>
              Salvar Rascunho
            </button>
            <button
              onClick={handleProtocolar}
              disabled={!isValid || isSubmitting}
              className="flex items-center gap-3 px-10 py-4 rounded-2xl font-semibold text-base shadow-2xl transition-all disabled:opacity-50 disabled:cursor-not-allowed enabled:hover:scale-[1.02] enabled:hover:shadow-primary/30"
              style={{ background: 'linear-gradient(135deg, #b8860b, #d4af37)', color: '#0B0F19' }}
            >
              {isSubmitting ? (
                <>
                  <span className="material-symbols-outlined text-xl animate-spin">progress_activity</span>
                  Enviando...
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-xl">send</span>
                  Protocolar Petição
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      <CertificadoModal open={certModalOpen} onOpenChange={setCertModalOpen} />
    </>
  )
}
