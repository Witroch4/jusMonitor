'use client'

import { useState } from 'react'

import { useRouter } from 'next/navigation'
import { CertificadoModal } from '@/components/peticoes/CertificadoModal'
import {
  FileKey,
  Upload,
  ShieldCheck,
  AlertTriangle,
  XCircle,
  TestTube,
  Trash2,
  Loader2,
} from 'lucide-react'

import { useProfile } from '@/hooks/api/useProfile'
import {
  useCertificados,
  useTestarCertificado,
  useRemoverCertificado,
} from '@/hooks/api/useCertificados'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'

const STATUS_CONFIG = {
  valido: {
    label: 'Válido',
    variant: 'default' as const,
    className: 'bg-emerald-100 text-emerald-700 border-emerald-200 hover:bg-emerald-100',
    Icon: ShieldCheck,
  },
  expirando: {
    label: 'Expirando',
    variant: 'secondary' as const,
    className: 'bg-amber-100 text-amber-700 border-amber-200 hover:bg-amber-100',
    Icon: AlertTriangle,
  },
  expirado: {
    label: 'Expirado',
    variant: 'destructive' as const,
    className: 'bg-red-100 text-red-700 border-red-200 hover:bg-red-100',
    Icon: XCircle,
  },
}

export function AssinaturaTab() {
  const router = useRouter()
  const { data: profile } = useProfile()
  const { data: certificados, isLoading } = useCertificados()
  const testarCert = useTestarCertificado()
  const removerCert = useRemoverCertificado()
  const [modalAberto, setModalAberto] = useState(false)

  return (
    <div className="space-y-6">
      {/* OAB + Email summary */}
      <Card className="border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden bg-card">
        <CardHeader className="border-b border-border/40 pb-4 bg-muted/10">
          <CardTitle className="font-serif text-xl tracking-tight text-primary flex items-center gap-2">
            <FileKey className="w-5 h-5" />
            Identidade Jurídica
          </CardTitle>
          <CardDescription className="text-sm font-medium">
            Dados utilizados na assinatura digital de documentos e petições.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-1.5">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Registro OAB
              </p>
              {profile?.oab_formatted ? (
                <Badge
                  variant="outline"
                  className="text-sm font-mono px-3 py-1.5 border-primary/30 text-primary"
                >
                  {profile.oab_formatted}
                </Badge>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Não informado.{' '}
                  <button
                    onClick={() => router.push('/configuracoes?tab=perfil')}
                    className="text-primary underline hover:no-underline"
                  >
                    Configurar no perfil
                  </button>
                </p>
              )}
            </div>
            <div className="space-y-1.5">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                E-mail Jurídico
              </p>
              <p className="text-sm font-medium text-foreground">
                {profile?.email || '—'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Separator className="my-2" />

      {/* Certificates list */}
      <Card className="border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden bg-card">
        <CardHeader className="border-b border-border/40 pb-4 bg-muted/10">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="font-serif text-xl tracking-tight text-primary">
                Certificados Digitais A1
              </CardTitle>
              <CardDescription className="text-sm font-medium mt-1">
                Certificados ICP-Brasil para assinatura e protocolo eletrônico.
              </CardDescription>
            </div>
            <Button
              size="sm"
              onClick={() => setModalAberto(true)}
              className="bg-primary hover:bg-primary/90 text-primary-foreground"
            >
              <Upload className="w-4 h-4 mr-1.5" />
              Adicionar Certificado
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-6">
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2].map((i) => (
                <div key={i} className="h-20 bg-muted/30 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : !certificados?.length ? (
            <div className="text-center py-12">
              <FileKey className="w-12 h-12 text-muted-foreground/40 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground font-medium">
                Nenhum certificado cadastrado.
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Adicione um certificado A1 (.pfx ou .p12) para assinar petições eletronicamente.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {certificados.map((cert) => {
                const statusCfg = STATUS_CONFIG[cert.status] || STATUS_CONFIG.valido
                const StatusIcon = statusCfg.Icon

                return (
                  <div
                    key={cert.id}
                    className="flex items-center justify-between p-4 border border-border/40 rounded-xl bg-muted/5 hover:bg-muted/10 transition-colors"
                  >
                    <div className="flex items-center gap-4 min-w-0">
                      <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                        <StatusIcon className="w-5 h-5 text-primary" />
                      </div>
                      <div className="min-w-0">
                        <p className="font-medium text-foreground truncate">
                          {cert.titularNome}
                        </p>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {cert.emissora} · Válido até{' '}
                          {new Date(cert.validoAte).toLocaleDateString('pt-BR')}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge className={statusCfg.className}>{statusCfg.label}</Badge>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => testarCert.mutate(cert.id)}
                        disabled={testarCert.isPending}
                        title="Testar mTLS"
                      >
                        {testarCert.isPending ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <TestTube className="w-4 h-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removerCert.mutate(cert.id)}
                        disabled={removerCert.isPending}
                        className="text-destructive hover:text-destructive"
                        title="Remover certificado"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>

      <CertificadoModal open={modalAberto} onOpenChange={setModalAberto} />
    </div>
  )
}
