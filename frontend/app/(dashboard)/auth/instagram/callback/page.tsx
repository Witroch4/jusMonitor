'use client'

import { Suspense, useEffect, useState } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { Instagram, Loader2, CheckCircle, XCircle } from 'lucide-react'

import { apiClient } from '@/lib/api-client'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

type Status = 'loading' | 'success' | 'error'

function InstagramCallbackContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const [status, setStatus] = useState<Status>('loading')
  const [username, setUsername] = useState('')
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    const code = searchParams.get('code')
    const state = searchParams.get('state')
    const error = searchParams.get('error')

    if (error) {
      setStatus('error')
      setErrorMsg('Autorização negada pelo Instagram.')
      return
    }

    if (!code || !state) {
      setStatus('error')
      setErrorMsg('Parâmetros inválidos na URL de retorno.')
      return
    }

    apiClient
      .get('/integrations/instagram/callback', { params: { code, state } })
      .then((res) => {
        setUsername(res.data.username || '')
        setStatus('success')
        setTimeout(() => router.push('/configuracoes?tab=integracoes'), 2500)
      })
      .catch((err) => {
        setStatus('error')
        setErrorMsg(
          err.response?.data?.detail || 'Erro ao conectar com Instagram.'
        )
      })
  }, [searchParams, router])

  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <Card className="w-full max-w-md border-border/40 shadow-lg rounded-2xl">
        <CardContent className="p-10 text-center space-y-5">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500 via-pink-500 to-orange-400 flex items-center justify-center mx-auto shadow-md">
            <Instagram className="w-8 h-8 text-white" />
          </div>

          {status === 'loading' && (
            <>
              <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto" />
              <h2 className="font-serif text-xl font-semibold text-foreground">
                Conectando ao Instagram...
              </h2>
              <p className="text-sm text-muted-foreground">
                Aguarde enquanto verificamos sua autorização.
              </p>
            </>
          )}

          {status === 'success' && (
            <>
              <CheckCircle className="w-10 h-10 text-emerald-500 mx-auto" />
              <h2 className="font-serif text-xl font-semibold text-foreground">
                Instagram conectado!
              </h2>
              {username && (
                <p className="text-sm text-muted-foreground">
                  Conta{' '}
                  <span className="font-medium text-primary">@{username}</span>{' '}
                  vinculada com sucesso.
                </p>
              )}
              <p className="text-xs text-muted-foreground animate-pulse">
                Redirecionando para Configurações...
              </p>
            </>
          )}

          {status === 'error' && (
            <>
              <XCircle className="w-10 h-10 text-destructive mx-auto" />
              <h2 className="font-serif text-xl font-semibold text-foreground">
                Falha na conexão
              </h2>
              <p className="text-sm text-muted-foreground">{errorMsg}</p>
              <Button
                variant="outline"
                onClick={() => router.push('/configuracoes?tab=integracoes')}
                className="mt-2"
              >
                Voltar para Configurações
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default function InstagramCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-[60vh] flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      }
    >
      <InstagramCallbackContent />
    </Suspense>
  )
}
