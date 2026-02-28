'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { useCertificados, useTestarCertificado } from '@/hooks/api/useCertificados'
import type { CertificadoDigital } from '@/types/peticoes'

interface Props {
  certificadoId: string
  onChange: (id: string) => void
  onOpenModal: () => void
}

const statusStyles: Record<CertificadoDigital['status'], { label: string; className: string }> = {
  valido: { label: 'Válido', className: 'bg-emerald-500/15 text-emerald-700 border-emerald-200 dark:text-emerald-400' },
  expirando: { label: 'Expirando', className: 'bg-yellow-500/15 text-yellow-700 border-yellow-200 dark:text-yellow-400' },
  expirado: { label: 'Expirado', className: 'bg-destructive/10 text-destructive border-destructive/30' },
}

function diasAteExpiracao(validoAte: string): number {
  const diff = new Date(validoAte).getTime() - Date.now()
  return Math.ceil(diff / (1000 * 60 * 60 * 24))
}

export function PeticaoFormCertificado({ certificadoId, onChange, onOpenModal }: Props) {
  const { data: certificados, isLoading } = useCertificados()
  const testar = useTestarCertificado()
  const [testeResultado, setTesteResultado] = useState<{ sucesso: boolean; mensagem: string } | null>(null)

  const selected = certificados?.find((c) => c.id === certificadoId)
  const dias = selected ? diasAteExpiracao(selected.validoAte) : null

  const handleTestar = async () => {
    if (!certificadoId) return
    setTesteResultado(null)
    const resultado = await testar.mutateAsync(certificadoId)
    setTesteResultado(resultado)
  }

  return (
    <div className="bg-card border border-border rounded-2xl p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-display text-base font-semibold text-foreground flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-lg">key</span>
          Certificado Digital A1
        </h3>
        <button
          onClick={onOpenModal}
          className="text-xs text-primary hover:text-primary/80 transition-colors flex items-center gap-1"
        >
          <span className="material-symbols-outlined text-xs">settings</span>
          Gerenciar
        </button>
      </div>

      <div className="space-y-4">
        <div>
          <Label className="text-xs font-medium mb-1.5 block text-muted-foreground">Selecionar Certificado</Label>
          <Select
            value={certificadoId || undefined}
            onValueChange={onChange}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Nenhum certificado selecionado" />
            </SelectTrigger>
            <SelectContent>
              {certificados?.filter((c) => c.status !== 'expirado').map((c) => (
                <SelectItem key={c.id} value={c.id}>
                  <div className="flex items-center gap-2">
                    <span>{c.nome}</span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {selected && (
          <div className="space-y-3 pt-2">
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <p className="text-muted-foreground">Titular</p>
                <p className="font-medium text-foreground truncate">{selected.titularNome}</p>
              </div>
              <div>
                <p className="text-muted-foreground">CPF/CNPJ</p>
                <p className="font-medium text-foreground">{selected.titularCpfCnpj}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Emissora</p>
                <p className="font-medium text-foreground truncate">{selected.emissora}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Validade</p>
                <div className="flex items-center gap-1.5">
                  <p className="font-medium text-foreground">
                    {new Date(selected.validoAte).toLocaleDateString('pt-BR')}
                  </p>
                  <Badge variant="outline" className={cn('text-[10px] px-1.5 py-0', statusStyles[selected.status].className)}>
                    {statusStyles[selected.status].label}
                  </Badge>
                </div>
              </div>
            </div>

            {dias !== null && dias <= 30 && dias > 0 && (
              <div className="flex items-start gap-2 p-2.5 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                <span className="material-symbols-outlined text-yellow-600 text-sm shrink-0">warning</span>
                <p className="text-xs text-yellow-700 dark:text-yellow-400">
                  Certificado expira em <strong>{dias} dias</strong>. Providencie a renovação.
                </p>
              </div>
            )}

            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="material-symbols-outlined text-xs">lock</span>
              <span>Criptografado ({selected.criptografia})</span>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={handleTestar}
              disabled={testar.isPending}
              className="w-full gap-2"
            >
              {testar.isPending ? (
                <>
                  <span className="material-symbols-outlined text-sm animate-spin">progress_activity</span>
                  Testando mTLS...
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-sm">lan</span>
                  Testar Conexão com Tribunal
                </>
              )}
            </Button>

            {testeResultado && (
              <div className={cn(
                'flex items-start gap-2 p-2.5 rounded-lg border text-xs',
                testeResultado.sucesso
                  ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-700 dark:text-emerald-400'
                  : 'bg-destructive/5 border-destructive/20 text-destructive'
              )}>
                <span className="material-symbols-outlined text-sm shrink-0">
                  {testeResultado.sucesso ? 'check_circle' : 'error'}
                </span>
                <span>{testeResultado.mensagem}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
