'use client'

import { useState, useEffect, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { PeticaoList } from '@/components/peticoes/PeticaoList'
import { PeticaoForm } from '@/components/peticoes/PeticaoForm'
import { normalizeProcessoNumero } from '@/lib/utils/processo'

type View = 'list' | 'form'

function PeticoesContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const processoParam = searchParams.get('processo')

  const editParam = searchParams.get('edit')

  const [view, setView] = useState<View>(processoParam || editParam ? 'form' : 'list')
  const [rascunhoId, setRascunhoId] = useState<string | null>(editParam ?? null)
  const [initialProcessoNumero, setInitialProcessoNumero] = useState<string>(
    processoParam ? normalizeProcessoNumero(processoParam) : ''
  )

  // If params arrive after mount (navigation), switch to form
  useEffect(() => {
    if (processoParam) {
      setInitialProcessoNumero(normalizeProcessoNumero(processoParam))
      setRascunhoId(null)
      setView('form')
    }
  }, [processoParam])

  // Handle ?edit=<id> — abre o form de edição (vindo da página de detalhe)
  useEffect(() => {
    if (editParam) {
      setRascunhoId(editParam)
      setInitialProcessoNumero('')
      setView('form')
      router.replace('/peticoes')
    }
  }, [editParam, router])

  function handleNovaPeticao() {
    setInitialProcessoNumero('')
    setRascunhoId(null)
    setView('form')
  }

  function handleEditRascunho(id: string) {
    setInitialProcessoNumero('')
    setRascunhoId(id)
    setView('form')
  }

  function handleRascunhoSalvo(id: string) {
    setRascunhoId(id)
  }

  function handleVoltar() {
    setInitialProcessoNumero('')
    setRascunhoId(null)
    setView('list')
    // Clear query param when going back
    if (processoParam) router.replace('/peticoes')
  }

  return view === 'list' ? (
    <PeticaoList onNovaPeticao={handleNovaPeticao} onEditRascunho={handleEditRascunho} />
  ) : (
    <PeticaoForm
      onVoltar={handleVoltar}
      rascunhoId={rascunhoId ?? undefined}
      initialProcessoNumero={initialProcessoNumero || undefined}
      onRascunhoSalvo={handleRascunhoSalvo}
    />
  )
}

export default function PeticoesPage() {
  return (
    <Suspense fallback={<div />}>
      <PeticoesContent />
    </Suspense>
  )
}
