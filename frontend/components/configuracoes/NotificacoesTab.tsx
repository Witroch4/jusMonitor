'use client'

import { useState } from 'react'
import { Bell, Scale, Clock, Users, Megaphone } from 'lucide-react'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'

interface NotificationPref {
  id: string
  label: string
  description: string
  icon: React.ElementType
  enabled: boolean
}

const DEFAULT_PREFS: NotificationPref[] = [
  {
    id: 'movimentacoes',
    label: 'Movimentações Processuais',
    description: 'Receba alertas quando houver novas movimentações nos seus processos.',
    icon: Scale,
    enabled: true,
  },
  {
    id: 'prazos',
    label: 'Prazos e Vencimentos',
    description: 'Lembretes de prazos processuais e vencimentos de documentos.',
    icon: Clock,
    enabled: true,
  },
  {
    id: 'leads_novos',
    label: 'Leads Novos',
    description: 'Notificações quando novos leads entrarem no funil de vendas.',
    icon: Users,
    enabled: true,
  },
  {
    id: 'atualizacoes_sistema',
    label: 'Atualizações do Sistema',
    description: 'Novidades, manutenções programadas e atualizações de funcionalidades.',
    icon: Megaphone,
    enabled: false,
  },
]

export function NotificacoesTab() {
  const [prefs, setPrefs] = useState<NotificationPref[]>(DEFAULT_PREFS)

  const togglePref = (id: string) => {
    setPrefs((prev) =>
      prev.map((p) => (p.id === id ? { ...p, enabled: !p.enabled } : p))
    )
    // TODO: persist via PATCH /profile/preferences when backend endpoint is ready
  }

  return (
    <div className="space-y-6">
      <Card className="border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden bg-card">
        <CardHeader className="border-b border-border/40 pb-4 bg-muted/10">
          <CardTitle className="font-serif text-xl tracking-tight text-primary flex items-center gap-2">
            <Bell className="w-5 h-5" />
            Preferências de Notificação
          </CardTitle>
          <CardDescription className="text-sm font-medium">
            Escolha quais notificações deseja receber por e-mail e no aplicativo.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-6">
          <div className="space-y-1">
            {prefs.map((pref, index) => {
              const IconComp = pref.icon
              return (
                <div key={pref.id}>
                  <div className="flex items-center justify-between py-4 px-4 rounded-xl hover:bg-muted/5 transition-colors">
                    <div className="flex items-start gap-4">
                      <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                        <IconComp className="w-4.5 h-4.5 text-primary" />
                      </div>
                      <Label htmlFor={pref.id} className="cursor-pointer space-y-1">
                        <span className="font-medium text-foreground text-[15px]">
                          {pref.label}
                        </span>
                        <p className="text-sm text-muted-foreground font-normal leading-relaxed">
                          {pref.description}
                        </p>
                      </Label>
                    </div>
                    <Switch
                      id={pref.id}
                      checked={pref.enabled}
                      onCheckedChange={() => togglePref(pref.id)}
                    />
                  </div>
                  {index < prefs.length - 1 && <Separator className="mx-4" />}
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
