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
import { useCreatePeticao, useUploadDocumento, useProtocolar } from '@/hooks/api/usePeticoes'
import { useQueryClient } from '@tanstack/react-query'
import { useProfile } from '@/hooks/api/useProfile'
import { TRIBUNAIS } from '@/lib/data/tribunais'
import type { NovaPeticaoFormData, UploadedFile, AnaliseIA, Polo, AssuntoProcessual } from '@/types/peticoes'
import { ChevronLeft } from 'lucide-react'
import { toast } from 'sonner'

interface Props {
  onVoltar: () => void
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

export function PeticaoForm({ onVoltar }: Props) {
  const [formData, setFormData] = useState<NovaPeticaoFormData>(INITIAL_FORM)
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [analise, setAnalise] = useState<AnaliseIA | null>(null)
  const [certModalOpen, setCertModalOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const queryClient = useQueryClient()
  const createPeticao = useCreatePeticao()
  const uploadDocumento = useUploadDocumento()
  const protocolar = useProtocolar()
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
  const isValid = useRevisaoValidation(formData, files)

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
      // 1. Create petition with form data
      const peticao = await createPeticao.mutateAsync(formData)

      // 2. Upload each file to the created petition
      const uploadedFiles = files.filter((f) => f.status === 'uploaded')
      for (let i = 0; i < uploadedFiles.length; i++) {
        const f = uploadedFiles[i]
        await uploadDocumento.mutateAsync({
          peticaoId: peticao.id,
          arquivo: f.file,
          tipoDocumento: f.tipoDocumento,
          ordem: i + 1,
          sigiloso: f.sigiloso,
        })
      }

      // 3. Trigger filing via worker
      await protocolar.mutateAsync(peticao.id)

      // Invalidar cache para que aba Casos mostre o novo processo
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
      // 1. Create petition
      const peticao = await createPeticao.mutateAsync(formData)

      // 2. Upload files if any
      const uploadedFiles = files.filter((f) => f.status === 'uploaded')
      for (let i = 0; i < uploadedFiles.length; i++) {
        const f = uploadedFiles[i]
        await uploadDocumento.mutateAsync({
          peticaoId: peticao.id,
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
              Nova Petição
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
            <PeticaoFormUpload files={files} onFilesChange={setFiles} limiteArquivoMB={limiteArquivoMB} />
            <PeticaoFormRevisao formData={formData} files={files} analise={analise} />
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
