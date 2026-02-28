'use client'

import { useState } from 'react'
import { PeticaoList } from '@/components/peticoes/PeticaoList'
import { PeticaoForm } from '@/components/peticoes/PeticaoForm'

type View = 'list' | 'form'

export default function PeticoesPage() {
  const [view, setView] = useState<View>('list')

  return view === 'list' ? (
    <PeticaoList onNovaPeticao={() => setView('form')} />
  ) : (
    <PeticaoForm onVoltar={() => setView('list')} />
  )
}
