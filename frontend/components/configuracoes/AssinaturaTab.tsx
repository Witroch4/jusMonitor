'use client'

import { useState, useRef } from 'react'

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
  ShieldAlert,
  QrCode,
  CheckCircle2,
  ImageUp,
  RotateCcw,
} from 'lucide-react'

import { useProfile } from '@/hooks/api/useProfile'
import {
  useCertificados,
  useTestarCertificado,
  useRemoverCertificado,
  useConfigurarTotpQr,
  useRemoverTotp,
} from '@/hooks/api/useCertificados'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'

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
  const removerTotp = useRemoverTotp()
  const totpQr = useConfigurarTotpQr()
  const [modalAberto, setModalAberto] = useState(false)
  const [qrExpandedCertId, setQrExpandedCertId] = useState<string | null>(null)
  const [qrResults, setQrResults] = useState<Record<string, { sucesso: boolean; mensagem: string }>>({})
  const qrFileRef = useRef<HTMLInputElement>(null)

  const handleQrUpload = async (certId: string, file: File) => {
    try {
      const result = await totpQr.mutateAsync({ certId, imagem: file })
      setQrResults((prev) => ({
        ...prev,
        [certId]: { sucesso: true, mensagem: `${result.mensagem} (${result.secret_masked})` },
      }))
      setQrExpandedCertId(null)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      const msg = detail || (err instanceof Error ? err.message : 'Erro ao processar QR Code')
      setQrResults((prev) => ({ ...prev, [certId]: { sucesso: false, mensagem: msg } }))
    }
  }

  const hasCertWithout2FA = certificados?.some((c) => !c.totpConfigurado && c.status !== 'expirado')

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
                {profile?.email || '\u2014'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Separator className="my-2" />

      {/* CNJ 2FA Alert */}
      {hasCertWithout2FA && (
        <Card className="border-amber-300/60 bg-amber-50/50 dark:bg-amber-950/20 dark:border-amber-700/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden">
          <CardContent className="p-5">
            <div className="flex gap-4">
              <div className="w-10 h-10 rounded-lg bg-amber-100 dark:bg-amber-900/40 flex items-center justify-center shrink-0">
                <ShieldAlert className="w-5 h-5 text-amber-600 dark:text-amber-400" />
              </div>
              <div className="space-y-1.5">
                <p className="text-sm font-semibold text-amber-800 dark:text-amber-300">
                  Duplo Fator de Autenticação (2FA) Obrigatório
                </p>
                <p className="text-xs text-amber-700/80 dark:text-amber-400/70 leading-relaxed">
                  Envie o printscreen do QR Code gerado pelo sistema do tribunal (PJe, eProc, e-SAJ, etc.)
                  ao ativar o 2FA. O sistema irá decodificar automaticamente o segredo e configurar a
                  autenticação de dois fatores para peticionamento eletrônico.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

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
                const isQrExpanded = qrExpandedCertId === cert.id

                return (
                  <div
                    key={cert.id}
                    className="border border-border/40 rounded-xl bg-muted/5 hover:bg-muted/10 transition-colors overflow-hidden"
                  >
                    {/* Main row */}
                    <div className="flex items-center justify-between p-4">
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
                        {cert.totpConfigurado ? (
                          <div className="flex items-center gap-1.5">
                            <Badge variant="outline" className="text-[10px] px-2 py-0.5 bg-emerald-500/15 text-emerald-700 border-emerald-200 dark:text-emerald-400 dark:border-emerald-700 gap-1">
                              <CheckCircle2 className="w-3 h-3" />
                              2FA Ativo
                            </Badge>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 w-7 p-0 text-muted-foreground hover:text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-950/30"
                              title="Remover e reconfigurar 2FA"
                              disabled={removerTotp.isPending}
                              onClick={async () => {
                                await removerTotp.mutateAsync(cert.id)
                                setQrResults((prev) => { const n = { ...prev }; delete n[cert.id]; return n })
                                setQrExpandedCertId(cert.id)
                              }}
                            >
                              {removerTotp.isPending ? (
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              ) : (
                                <RotateCcw className="w-3.5 h-3.5" />
                              )}
                            </Button>
                          </div>
                        ) : cert.status !== 'expirado' ? (
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs gap-1.5 border-amber-300 text-amber-700 hover:bg-amber-50 hover:text-amber-800 dark:border-amber-700 dark:text-amber-400"
                            onClick={() => setQrExpandedCertId(isQrExpanded ? null : cert.id)}
                          >
                            <QrCode className="w-3.5 h-3.5" />
                            Configurar 2FA
                          </Button>
                        ) : (
                          <Badge variant="outline" className="text-[10px] px-2 py-0.5 bg-muted text-muted-foreground gap-1">
                            2FA
                          </Badge>
                        )}
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

                    {/* QR Code upload section */}
                    {isQrExpanded && (
                      <div className="px-4 pb-4 pt-0">
                        <div className="border-t border-border/40 pt-4">
                          <div className="flex items-start gap-3 mb-3">
                            <ShieldAlert className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
                            <p className="text-xs text-muted-foreground leading-relaxed">
                              Envie o <strong>screenshot/foto do QR Code</strong> que apareceu ao ativar o
                              2FA no portal do tribunal. O sistema irá decodificar automaticamente o segredo
                              TOTP e configurar a autenticação de dois fatores.
                            </p>
                          </div>
                          <div
                            onClick={() => qrFileRef.current?.click()}
                            onDragOver={(e) => e.preventDefault()}
                            onDrop={(e) => {
                              e.preventDefault()
                              const file = e.dataTransfer.files?.[0]
                              if (file) handleQrUpload(cert.id, file)
                            }}
                            role="button"
                            tabIndex={0}
                            onKeyDown={(e) => e.key === 'Enter' && qrFileRef.current?.click()}
                            aria-label="Selecionar imagem do QR Code TOTP"
                            className={cn(
                              'flex items-center gap-4 w-full rounded-lg border-2 border-dashed px-5 py-4 cursor-pointer transition-all',
                              totpQr.isPending
                                ? 'border-primary/40 bg-primary/5 pointer-events-none'
                                : 'border-border hover:border-primary/50 hover:bg-muted/30'
                            )}
                          >
                            <div className={cn(
                              'w-10 h-10 rounded-lg flex items-center justify-center shrink-0',
                              totpQr.isPending ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground'
                            )}>
                              {totpQr.isPending ? (
                                <Loader2 className="w-5 h-5 animate-spin" />
                              ) : (
                                <ImageUp className="w-5 h-5" />
                              )}
                            </div>
                            <div className="flex-1 min-w-0 text-left">
                              <p className="text-sm font-medium text-foreground">
                                {totpQr.isPending ? 'Decodificando QR Code...' : 'Enviar screenshot do QR Code TOTP'}
                              </p>
                              <p className="text-xs text-muted-foreground mt-0.5">
                                Arraste ou clique para selecionar a imagem (PNG, JPG, WebP)
                              </p>
                            </div>
                            <input
                              ref={qrFileRef}
                              type="file"
                              accept=".png,.jpg,.jpeg,.webp,.bmp"
                              className="hidden"
                              onChange={(e) => {
                                const file = e.target.files?.[0]
                                if (file) handleQrUpload(cert.id, file)
                                e.target.value = ''
                              }}
                            />
                          </div>
                        </div>
                      </div>
                    )}

                    {/* QR result message */}
                    {qrResults[cert.id] && (
                      <div className="px-4 pb-4 pt-0">
                        <div className={cn(
                          'flex items-center gap-2 p-3 rounded-lg border text-xs',
                          qrResults[cert.id].sucesso
                            ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-700 dark:text-emerald-400'
                            : 'bg-destructive/5 border-destructive/20 text-destructive'
                        )}>
                          {qrResults[cert.id].sucesso ? (
                            <CheckCircle2 className="w-4 h-4 shrink-0" />
                          ) : (
                            <XCircle className="w-4 h-4 shrink-0" />
                          )}
                          {qrResults[cert.id].mensagem}
                        </div>
                      </div>
                    )}
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
