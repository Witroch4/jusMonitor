'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Lock, Shield, CheckCircle, Eye, EyeOff, Loader2 } from 'lucide-react'

import { useChangePassword } from '@/hooks/api/useProfile'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'

const changePasswordSchema = z
  .object({
    current_password: z.string().min(8, 'Mínimo 8 caracteres'),
    new_password: z
      .string()
      .min(8, 'Mínimo 8 caracteres')
      .regex(/[A-Z]/, 'Deve conter ao menos uma letra maiúscula')
      .regex(/[0-9]/, 'Deve conter ao menos um número'),
    confirm_password: z.string(),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    message: 'Senhas não conferem',
    path: ['confirm_password'],
  })

type ChangePasswordValues = z.infer<typeof changePasswordSchema>

export function SegurancaTab() {
  const changePassword = useChangePassword()
  const [showPasswords, setShowPasswords] = useState({
    current: false,
    new: false,
    confirm: false,
  })
  const [success, setSuccess] = useState(false)

  const form = useForm<ChangePasswordValues>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: {
      current_password: '',
      new_password: '',
      confirm_password: '',
    },
  })

  const onSubmit = async (data: ChangePasswordValues) => {
    setSuccess(false)
    try {
      await changePassword.mutateAsync(data)
      form.reset()
      setSuccess(true)
    } catch {
      // Error handled by React Query
    }
  }

  const toggleShow = (field: 'current' | 'new' | 'confirm') => {
    setShowPasswords((prev) => ({ ...prev, [field]: !prev[field] }))
  }

  return (
    <div className="space-y-6">
      <Card className="border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden bg-card">
        <CardHeader className="border-b border-border/40 pb-4 bg-muted/10">
          <CardTitle className="font-serif text-xl tracking-tight text-primary flex items-center gap-2">
            <Lock className="w-5 h-5" />
            Alterar Senha
          </CardTitle>
          <CardDescription className="text-sm font-medium">
            Use uma senha forte com letras maiúsculas, números e símbolos.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-8">
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5 max-w-md">
              <FormField
                control={form.control}
                name="current_password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Senha Atual
                    </FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Input
                          {...field}
                          type={showPasswords.current ? 'text' : 'password'}
                          className="border-border/60 bg-white dark:bg-muted/20 shadow-sm focus-visible:ring-primary/20 rounded-lg pr-10"
                        />
                        <button
                          type="button"
                          onClick={() => toggleShow('current')}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                        >
                          {showPasswords.current ? (
                            <EyeOff className="w-4 h-4" />
                          ) : (
                            <Eye className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="new_password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Nova Senha
                    </FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Input
                          {...field}
                          type={showPasswords.new ? 'text' : 'password'}
                          className="border-border/60 bg-white dark:bg-muted/20 shadow-sm focus-visible:ring-primary/20 rounded-lg pr-10"
                        />
                        <button
                          type="button"
                          onClick={() => toggleShow('new')}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                        >
                          {showPasswords.new ? (
                            <EyeOff className="w-4 h-4" />
                          ) : (
                            <Eye className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="confirm_password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Confirmar Nova Senha
                    </FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Input
                          {...field}
                          type={showPasswords.confirm ? 'text' : 'password'}
                          className="border-border/60 bg-white dark:bg-muted/20 shadow-sm focus-visible:ring-primary/20 rounded-lg pr-10"
                        />
                        <button
                          type="button"
                          onClick={() => toggleShow('confirm')}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                        >
                          {showPasswords.confirm ? (
                            <EyeOff className="w-4 h-4" />
                          ) : (
                            <Eye className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {changePassword.isError && (
                <p className="text-sm text-destructive font-medium">
                  {(changePassword.error as any)?.response?.data?.detail || 'Erro ao alterar senha.'}
                </p>
              )}

              {success && (
                <p className="text-sm text-emerald-600 font-medium flex items-center gap-1.5">
                  <CheckCircle className="w-4 h-4" />
                  Senha alterada com sucesso.
                </p>
              )}

              <Button
                type="submit"
                disabled={changePassword.isPending}
                className="bg-primary hover:bg-primary/90 text-primary-foreground font-medium shadow-sm"
              >
                {changePassword.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Alterando...
                  </>
                ) : (
                  'Alterar Senha'
                )}
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>

      <Separator className="my-2" />

      <Card className="border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden bg-card">
        <CardHeader className="border-b border-border/40 pb-4 bg-muted/10">
          <CardTitle className="font-serif text-xl tracking-tight text-primary flex items-center gap-2">
            <Shield className="w-5 h-5" />
            Autenticação de Dois Fatores
          </CardTitle>
          <CardDescription className="text-sm font-medium">
            Adicione uma camada extra de segurança à sua conta.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-8">
          <div className="flex items-center justify-between p-4 border border-border/40 rounded-xl bg-muted/5">
            <div className="space-y-1">
              <p className="font-medium text-foreground">2FA via Aplicativo Autenticador</p>
              <p className="text-sm text-muted-foreground">
                Em breve disponível. Proteja sua conta com Google Authenticator ou similar.
              </p>
            </div>
            <Button variant="outline" size="sm" disabled>
              Em breve
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
