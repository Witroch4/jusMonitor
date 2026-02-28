'use client'

import { Instagram, MessageCircle, Loader2, ExternalLink } from 'lucide-react'

import { useInstagramIntegration, useDisconnectInstagram } from '@/hooks/api/useIntegrations'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function IntegracoesTab() {
  const { data: instagram, isLoading: igLoading } = useInstagramIntegration()
  const disconnect = useDisconnectInstagram()

  const handleConnectInstagram = () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
    window.location.href = `${apiUrl}/integrations/instagram/authorize`
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden bg-card">
        <CardHeader className="border-b border-border/40 pb-4 bg-muted/10">
          <CardTitle className="font-serif text-xl tracking-tight text-primary">
            Integrações
          </CardTitle>
          <CardDescription className="text-sm font-medium">
            Conecte serviços externos para enriquecer seu perfil e automatizar processos.
          </CardDescription>
        </CardHeader>
      </Card>

      {/* Instagram card */}
      <Card className="border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden bg-card">
        <CardContent className="p-8">
          <div className="flex items-start justify-between gap-6">
            <div className="flex items-start gap-4 min-w-0">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 via-pink-500 to-orange-400 flex items-center justify-center shadow-sm shrink-0">
                <Instagram className="w-6 h-6 text-white" />
              </div>
              <div className="min-w-0">
                <h3 className="font-serif font-semibold text-lg text-foreground">
                  Instagram Business
                </h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Conecte sua conta do Instagram Business para enriquecer seu perfil
                  com foto e nome, e receber leads via DM automaticamente pelo Chatwit.
                </p>
                {instagram?.connected && instagram.username && (
                  <div className="flex items-center gap-2 mt-3">
                    {instagram.profile_picture_url && (
                      <Avatar className="w-8 h-8 border border-pink-200">
                        <AvatarImage src={instagram.profile_picture_url} />
                        <AvatarFallback className="text-xs">IG</AvatarFallback>
                      </Avatar>
                    )}
                    <span className="text-sm font-medium text-primary">
                      @{instagram.username}
                    </span>
                  </div>
                )}
                {instagram?.connected && instagram.token_expires_at && (
                  <p className="text-xs text-muted-foreground mt-2">
                    Token expira em{' '}
                    {new Date(instagram.token_expires_at).toLocaleDateString('pt-BR')}
                  </p>
                )}
              </div>
            </div>

            <div className="flex flex-col items-end gap-3 shrink-0">
              {igLoading ? (
                <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
              ) : instagram?.connected ? (
                <>
                  <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200 hover:bg-emerald-100">
                    Conectado
                  </Badge>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => disconnect.mutate()}
                    disabled={disconnect.isPending}
                    className="text-destructive border-destructive/30 hover:bg-destructive/10"
                  >
                    {disconnect.isPending ? (
                      <Loader2 className="w-4 h-4 animate-spin mr-1.5" />
                    ) : null}
                    Desconectar
                  </Button>
                </>
              ) : (
                <>
                  <Badge variant="secondary">Não conectado</Badge>
                  <Button
                    size="sm"
                    onClick={handleConnectInstagram}
                    className="bg-gradient-to-br from-purple-500 via-pink-500 to-orange-400 text-white border-0 hover:opacity-90 shadow-sm"
                  >
                    <Instagram className="w-4 h-4 mr-1.5" />
                    Conectar Instagram
                  </Button>
                </>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Chatwit card */}
      <Card className="border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden bg-card">
        <CardContent className="p-8">
          <div className="flex items-start justify-between gap-6">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-emerald-500 flex items-center justify-center shadow-sm shrink-0">
                <MessageCircle className="w-6 h-6 text-white" />
              </div>
              <div>
                <h3 className="font-serif font-semibold text-lg text-foreground">
                  Chatwit
                </h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Fonte de verdade para chats com clientes via WhatsApp e Instagram DM.
                  Integração gerenciada pela equipe JusMonitor.
                </p>
                <a
                  href="https://chatwit.witdev.com.br"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-primary hover:underline inline-flex items-center gap-1 mt-2"
                >
                  Acessar painel Chatwit
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
            <div className="shrink-0">
              <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200 hover:bg-emerald-100">
                Ativo
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
