'use client'

import { useState, useRef } from 'react'
import { Upload, FileKey } from 'lucide-react'
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
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import {
  useCertificados,
  useUploadCertificado,
  useTestarCertificado,
  useRemoverCertificado,
} from '@/hooks/api/useCertificados'
import type { CertificadoDigital } from '@/types/peticoes'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const statusConfig: Record<CertificadoDigital['status'], { label: string; className: string }> = {
  valido: { label: 'Válido', className: 'bg-emerald-500/15 text-emerald-700 border-emerald-200 dark:text-emerald-400' },
  expirando: { label: 'Expirando', className: 'bg-yellow-500/15 text-yellow-700 border-yellow-200 dark:text-yellow-400' },
  expirado: { label: 'Expirado', className: 'bg-destructive/10 text-destructive border-destructive/30' },
}

export function CertificadoModal({ open, onOpenChange }: Props) {
  const { data: certificados, isLoading } = useCertificados()
  const upload = useUploadCertificado()
  const testar = useTestarCertificado()
  const remover = useRemoverCertificado()

  const [showForm, setShowForm] = useState(false)
  const [nomeAmigavel, setNomeAmigavel] = useState('')
  const [senha, setSenha] = useState('')
  const [arquivo, setArquivo] = useState<File | null>(null)
  const [dragOverCert, setDragOverCert] = useState(false)
  const certFileRef = useRef<HTMLInputElement>(null)
  const [testResults, setTestResults] = useState<Record<string, { sucesso: boolean; mensagem: string }>>({})

  const handleUpload = async () => {
    if (!arquivo || !nomeAmigavel || !senha) return
    await upload.mutateAsync({
      arquivo,
      nome: nomeAmigavel,
      senhaPfx: senha,
    })
    setShowForm(false)
    setNomeAmigavel('')
    setSenha('')
    setArquivo(null)
    setDragOverCert(false)
  }

  const handleTestar = async (id: string) => {
    const result = await testar.mutateAsync(id)
    setTestResults((prev) => ({ ...prev, [id]: result }))
  }

  const handleRemover = async (id: string) => {
    await remover.mutateAsync(id)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary">key</span>
            Certificados Digitais A1
          </DialogTitle>
          <DialogDescription>
            Gerencie seus certificados ICP-Brasil para peticionamento eletrônico
          </DialogDescription>
        </DialogHeader>

        {/* Certificate list */}
        <div className="space-y-3 mt-2">
          {certificados?.map((cert) => (
            <div key={cert.id} className="border border-border rounded-xl p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="text-sm font-semibold text-foreground">{cert.nome}</p>
                    <Badge variant="outline" className={cn('text-[10px] px-1.5 py-0', statusConfig[cert.status].className)}>
                      {statusConfig[cert.status].label}
                    </Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                    <div>
                      <span className="text-muted-foreground">Titular: </span>
                      <span className="text-foreground">{cert.titularNome}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">CPF/CNPJ: </span>
                      <span className="text-foreground">{cert.titularCpfCnpj}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Emissora: </span>
                      <span className="text-foreground">{cert.emissora}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Serial: </span>
                      <span className="text-foreground font-mono">{cert.serialNumber}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Válido até: </span>
                      <span className="text-foreground">{new Date(cert.validoAte).toLocaleDateString('pt-BR')}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="material-symbols-outlined text-xs text-muted-foreground">lock</span>
                      <span className="text-muted-foreground">{cert.criptografia}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 shrink-0">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleTestar(cert.id)}
                    disabled={testar.isPending || cert.status === 'expirado'}
                    className="h-8 text-xs gap-1"
                  >
                    <span className="material-symbols-outlined text-xs">lan</span>
                    Testar
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRemover(cert.id)}
                    disabled={remover.isPending}
                    className="h-8 text-xs text-destructive hover:text-destructive hover:bg-destructive/10"
                  >
                    <span className="material-symbols-outlined text-xs">delete</span>
                  </Button>
                </div>
              </div>

              {testResults[cert.id] && (
                <div className={cn(
                  'mt-3 flex items-center gap-2 p-2 rounded-lg border text-xs',
                  testResults[cert.id].sucesso
                    ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-700 dark:text-emerald-400'
                    : 'bg-destructive/5 border-destructive/20 text-destructive'
                )}>
                  <span className="material-symbols-outlined text-sm">
                    {testResults[cert.id].sucesso ? 'check_circle' : 'error'}
                  </span>
                  {testResults[cert.id].mensagem}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Add form */}
        {showForm ? (
          <div className="border border-dashed border-primary/30 rounded-xl p-5 bg-primary/5 mt-2">
            <h4 className="text-sm font-semibold mb-4 flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-base">add_circle</span>
              Adicionar Certificado A1
            </h4>
            <div className="space-y-3">
              <div>
                <Label className="text-xs mb-2 block">Arquivo PFX/P12</Label>
                <div
                  onClick={() => certFileRef.current?.click()}
                  onDragOver={(e) => { e.preventDefault(); setDragOverCert(true) }}
                  onDragLeave={() => setDragOverCert(false)}
                  onDrop={(e) => {
                    e.preventDefault()
                    setDragOverCert(false)
                    const file = e.dataTransfer.files?.[0]
                    if (file) setArquivo(file)
                  }}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === 'Enter' && certFileRef.current?.click()}
                  aria-label="Selecionar arquivo PFX ou P12"
                  className={cn(
                    'flex items-center gap-3 w-full rounded-lg border-2 border-dashed px-4 py-3 cursor-pointer transition-all select-none',
                    dragOverCert
                      ? 'border-primary bg-primary/10 scale-[1.01]'
                      : arquivo
                        ? 'border-emerald-500/50 bg-emerald-500/5 hover:border-emerald-500/80'
                        : 'border-border hover:border-primary/50 hover:bg-muted/30'
                  )}
                >
                  <div className={cn(
                    'w-8 h-8 rounded-md flex items-center justify-center shrink-0 transition-colors',
                    arquivo ? 'bg-emerald-500/15 text-emerald-600' : 'bg-muted text-muted-foreground'
                  )}>
                    {arquivo ? <FileKey className="h-4 w-4" /> : <Upload className="h-4 w-4" />}
                  </div>
                  <div className="flex-1 min-w-0 text-left">
                    {arquivo ? (
                      <>
                        <p className="text-sm font-medium text-foreground truncate">{arquivo.name}</p>
                        <p className="text-xs text-muted-foreground">{(arquivo.size / 1024).toFixed(1)} KB • Clique para trocar</p>
                      </>
                    ) : (
                      <>
                        <p className="text-sm font-medium text-foreground">Selecionar arquivo .pfx / .p12</p>
                        <p className="text-xs text-muted-foreground">Clique ou arraste o certificado aqui</p>
                      </>
                    )}
                  </div>
                  <input
                    ref={certFileRef}
                    type="file"
                    accept=".pfx,.p12"
                    className="hidden"
                    onChange={(e) => setArquivo(e.target.files?.[0] ?? null)}
                  />
                </div>
              </div>
              <div>
                <Label className="text-xs mb-1 block">Senha do Certificado</Label>
                <Input
                  type="password"
                  value={senha}
                  onChange={(e) => setSenha(e.target.value)}
                  placeholder="Senha do arquivo PFX"
                />
              </div>
              <div>
                <Label className="text-xs mb-1 block">Nome Amigável</Label>
                <Input
                  value={nomeAmigavel}
                  onChange={(e) => setNomeAmigavel(e.target.value)}
                  placeholder="Ex: Certificado Dra. Maria"
                />
              </div>
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                <span className="material-symbols-outlined text-xs">lock</span>
                O certificado será criptografado (AES-128-CBC) e armazenado com segurança
              </p>
              <div className="flex gap-2 pt-1">
                <Button onClick={handleUpload} disabled={!arquivo || !nomeAmigavel || !senha || upload.isPending} size="sm">
                  {upload.isPending ? 'Salvando...' : 'Salvar Certificado'}
                </Button>
                <Button variant="outline" size="sm" onClick={() => setShowForm(false)}>
                  Cancelar
                </Button>
              </div>
            </div>
          </div>
        ) : (
          <Button
            variant="outline"
            onClick={() => setShowForm(true)}
            className="w-full mt-2 gap-2"
          >
            <span className="material-symbols-outlined text-base">add</span>
            Adicionar Certificado A1
          </Button>
        )}
      </DialogContent>
    </Dialog>
  )
}
