'use client'

import { useRef } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Camera, Loader2 } from 'lucide-react'

import { useProfile, useUpdateProfile, useUploadAvatar } from '@/hooks/api/useProfile'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'

const ESTADOS_BR = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT',
  'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO',
  'RR', 'SC', 'SP', 'SE', 'TO',
]

const ROLES_PT: Record<string, string> = {
  super_admin: 'Super Admin',
  admin: 'Administrador',
  lawyer: 'Advogado',
  assistant: 'Assistente',
  viewer: 'Visualizador',
}

const perfilSchema = z.object({
  full_name: z.string().min(2, 'Nome deve ter ao menos 2 caracteres'),
  phone: z
    .string()
    .optional()
    .refine(
      (v) => !v || /^\d{10,11}$/.test(v.replace(/\D/g, '')),
      { message: 'Telefone inválido' }
    ),
  oab_number: z
    .string()
    .optional()
    .refine(
      (v) => !v || /^\d{1,7}$/.test(v),
      { message: 'Número OAB: apenas dígitos (máx. 7)' }
    ),
  oab_state: z.string().optional(),
  cpf: z
    .string()
    .optional()
    .refine(
      (v) => !v || /^\d{11}$/.test(v.replace(/\D/g, '')),
      { message: 'CPF inválido' }
    ),
})

type PerfilFormValues = z.infer<typeof perfilSchema>

export function PerfilTab() {
  const { data: profile, isLoading } = useProfile()
  const updateProfile = useUpdateProfile()
  const uploadAvatar = useUploadAvatar()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const form = useForm<PerfilFormValues>({
    resolver: zodResolver(perfilSchema),
    values: {
      full_name: profile?.full_name || '',
      phone: profile?.phone || '',
      oab_number: profile?.oab_number || '',
      oab_state: profile?.oab_state || '',
      cpf: profile?.cpf || '',
    },
  })

  const onSubmit = async (data: PerfilFormValues) => {
    try {
      await updateProfile.mutateAsync({
        full_name: data.full_name,
        phone: data.phone || undefined,
        oab_number: data.oab_number || undefined,
        oab_state: data.oab_state || undefined,
        cpf: data.cpf ? data.cpf.replace(/\D/g, '') : undefined,
      })
    } catch {
      // Error handled by React Query
    }
  }

  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      await uploadAvatar.mutateAsync(file)
    } catch {
      // Error handled by React Query
    }
  }

  const initials = profile?.full_name
    ?.split(' ')
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase() || '?'

  if (isLoading) return <PerfilTabSkeleton />

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        {/* Personal Info Card */}
        <Card className="border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden bg-card">
          <CardHeader className="border-b border-border/40 pb-4 bg-muted/10">
            <CardTitle className="font-serif text-xl tracking-tight text-primary">
              Informações Pessoais
            </CardTitle>
            <CardDescription className="text-sm font-medium">
              Atualize sua foto e detalhes pessoais.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-8">
            <div className="flex flex-col md:flex-row gap-8 items-start">
              {/* Avatar section */}
              <div className="flex-none text-center">
                <div className="relative inline-block">
                  <Avatar className="w-24 h-24 border-2 border-primary/20 ring-2 ring-background shadow-md">
                    <AvatarImage src={profile?.avatar_url || undefined} alt={profile?.full_name} />
                    <AvatarFallback className="font-serif font-bold text-3xl text-primary bg-primary/10">
                      {initials}
                    </AvatarFallback>
                  </Avatar>
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploadAvatar.isPending}
                    className="absolute bottom-0 right-0 bg-primary text-primary-foreground rounded-full p-1.5 shadow-md hover:bg-primary/90 transition-colors disabled:opacity-50"
                  >
                    {uploadAvatar.isPending ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Camera className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  className="hidden"
                  onChange={handleAvatarChange}
                />
                <p className="text-[11px] text-muted-foreground mt-3">
                  JPEG, PNG ou WEBP. Máx 2MB.
                </p>
              </div>

              {/* Form fields */}
              <div className="flex-1 w-full space-y-5">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <FormField
                    control={form.control}
                    name="full_name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                          Nome Completo
                        </FormLabel>
                        <FormControl>
                          <Input
                            {...field}
                            className="border-border/60 bg-white dark:bg-muted/20 shadow-sm focus-visible:ring-primary/20 rounded-lg text-foreground font-medium"
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* Email is read-only */}
                  <div className="space-y-2">
                    <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      E-mail Corporativo
                    </Label>
                    <Input
                      value={profile?.email || ''}
                      disabled
                      className="border-border/60 bg-muted/30 cursor-not-allowed text-muted-foreground font-medium"
                    />
                    <p className="text-[11px] text-muted-foreground">
                      Contate o administrador para alterar o e-mail.
                    </p>
                  </div>

                  <FormField
                    control={form.control}
                    name="phone"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                          Telefone
                        </FormLabel>
                        <FormControl>
                          <Input
                            {...field}
                            placeholder="(11) 99999-9999"
                            className="border-border/60 bg-white dark:bg-muted/20 shadow-sm focus-visible:ring-primary/20 rounded-lg text-foreground font-medium"
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* Role display */}
                  <div className="space-y-2">
                    <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Função
                    </Label>
                    <div className="flex items-center h-10 px-3 rounded-lg border border-border/40 bg-muted/20">
                      <Badge variant="secondary" className="capitalize text-xs">
                        {ROLES_PT[profile?.role || ''] || profile?.role}
                      </Badge>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* OAB Card */}
        <Card className="border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden bg-card">
          <CardHeader className="border-b border-border/40 pb-4 bg-muted/10">
            <CardTitle className="font-serif text-xl tracking-tight text-primary">
              Registro OAB
            </CardTitle>
            <CardDescription className="text-sm font-medium">
              Informe seu número OAB para uso em petições e documentos.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-8">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              <div className="md:col-span-2">
                <FormField
                  control={form.control}
                  name="oab_number"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                        Número OAB
                      </FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          placeholder="123456"
                          className="border-border/60 bg-white dark:bg-muted/20 shadow-sm focus-visible:ring-primary/20 rounded-lg text-foreground font-medium"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="oab_state"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Estado OAB
                    </FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger className="border-border/60 bg-white dark:bg-muted/20 shadow-sm">
                          <SelectValue placeholder="UF" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {ESTADOS_BR.map((uf) => (
                          <SelectItem key={uf} value={uf}>
                            {uf}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="md:col-span-2">
                <FormField
                  control={form.control}
                  name="cpf"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                        CPF
                      </FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          placeholder="000.000.000-00"
                          className="border-border/60 bg-white dark:bg-muted/20 shadow-sm focus-visible:ring-primary/20 rounded-lg text-foreground font-medium font-mono"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>

            {(profile?.oab_formatted || profile?.cpf_formatted) && (
              <div className="mt-5 flex items-center gap-3 flex-wrap">
                {profile.oab_formatted && (
                  <Badge
                    variant="outline"
                    className="text-sm font-mono px-3 py-1 border-primary/30 text-primary"
                  >
                    {profile.oab_formatted}
                  </Badge>
                )}
                {profile.cpf_formatted && (
                  <Badge
                    variant="outline"
                    className="text-sm font-mono px-3 py-1 border-primary/30 text-primary"
                  >
                    CPF: {profile.cpf_formatted}
                  </Badge>
                )}
                <span className="text-xs text-muted-foreground">
                  Formato atual registrado
                </span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Social Profile Card */}
        <Card className="border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden bg-card">
          <CardHeader className="border-b border-border/40 pb-4 bg-muted/10">
            <CardTitle className="font-serif text-xl tracking-tight text-primary">
              Perfil Social
            </CardTitle>
            <CardDescription className="text-sm font-medium">
              Conecte suas redes sociais para enriquecer seu perfil e receber leads automaticamente.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-8">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 border border-border/40 rounded-xl bg-muted/5">
              {/* Left: icon + info */}
              <div className="flex items-center gap-4">
                {/* Instagram gradient icon */}
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm"
                  style={{
                    background: 'linear-gradient(135deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%)',
                  }}
                  aria-hidden="true"
                >
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="2" y="2" width="20" height="20" rx="5" ry="5" />
                    <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
                    <line x1="17.5" y1="6.5" x2="17.51" y2="6.5" />
                  </svg>
                </div>
                <div className="space-y-0.5">
                  <h4 className="font-semibold text-base text-foreground leading-tight">
                    Instagram Business
                  </h4>
                  <p className="text-sm text-muted-foreground leading-snug max-w-xs">
                    Conecte sua conta para enriquecer seu perfil com foto e nome, e receber leads via DM automaticamente pelo Chatwit.
                  </p>
                </div>
              </div>

              {/* Right: status + button */}
              <div className="flex flex-col sm:items-end gap-2 flex-shrink-0">
                <span className="text-xs font-medium text-muted-foreground">
                  Não conectado
                </span>
                <button
                  type="button"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold text-white shadow-sm transition-all hover:opacity-90 hover:-translate-y-px active:translate-y-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-pink-500"
                  style={{
                    background: 'linear-gradient(135deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%)',
                  }}
                  onClick={() => {
                    // Instagram OAuth flow — to be implemented
                    window.location.href = '/api/v1/integrations/instagram/connect'
                  }}
                  aria-label="Conectar conta do Instagram Business"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <rect x="2" y="2" width="20" height="20" rx="5" ry="5" />
                    <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
                    <line x1="17.5" y1="6.5" x2="17.51" y2="6.5" />
                  </svg>
                  Conectar Instagram
                </button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Action buttons */}
        <div className="flex justify-end gap-4 pt-2">
          <Button
            type="button"
            variant="ghost"
            onClick={() => form.reset()}
            className="font-semibold text-muted-foreground hover:text-foreground"
          >
            Cancelar
          </Button>
          <Button
            type="submit"
            disabled={updateProfile.isPending || !form.formState.isDirty}
            className="bg-primary hover:bg-primary/90 text-primary-foreground font-medium shadow-sm px-8"
          >
            {updateProfile.isPending ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Salvando...
              </>
            ) : (
              'Salvar Alterações'
            )}
          </Button>
        </div>

        {updateProfile.isSuccess && (
          <p className="text-sm text-emerald-600 text-right font-medium">
            Perfil atualizado com sucesso.
          </p>
        )}
      </form>
    </Form>
  )
}

function PerfilTabSkeleton() {
  return (
    <div className="space-y-6">
      <Card className="rounded-xl overflow-hidden">
        <CardHeader className="border-b border-border/40 bg-muted/10 pb-4">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-72 mt-2" />
        </CardHeader>
        <CardContent className="p-8">
          <div className="flex gap-8">
            <Skeleton className="w-24 h-24 rounded-full shrink-0" />
            <div className="flex-1 space-y-4">
              <div className="grid grid-cols-2 gap-5">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="rounded-xl overflow-hidden">
        <CardHeader className="border-b border-border/40 bg-muted/10 pb-4">
          <Skeleton className="h-6 w-36" />
        </CardHeader>
        <CardContent className="p-8">
          <div className="grid grid-cols-3 gap-5">
            <Skeleton className="h-10 col-span-2" />
            <Skeleton className="h-10" />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
