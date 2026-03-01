'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'

// ─── Model catalogs ──────────────────────────────────────────────

const GOOGLE_MODELS = [
  { value: 'gemini-3.1-pro-preview', label: 'Gemini 3.1 Pro Preview', tag: 'SOTA' },
  { value: 'gemini-3-flash-preview', label: 'Gemini 3 Flash Preview', tag: 'recomendado' },
  { value: 'gemini-3-pro-preview', label: 'Gemini 3 Pro Preview', tag: '' },
  { value: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro', tag: '' },
  { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash', tag: '' },
  { value: 'gemini-2.5-flash-lite', label: 'Gemini 2.5 Flash Lite', tag: 'econômico' },
  { value: 'gemini-flash-latest', label: 'Gemini Flash (latest)', tag: 'alias' },
  { value: 'gemini-flash-lite-latest', label: 'Gemini Flash Lite (latest)', tag: 'alias' },
]

const OPENAI_MODELS = [
  { value: 'gpt-4.1', label: 'GPT-4.1', tag: 'recomendado' },
  { value: 'gpt-4.1-mini', label: 'GPT-4.1 Mini', tag: '' },
  { value: 'gpt-4.1-nano', label: 'GPT-4.1 Nano', tag: 'econômico' },
  { value: 'gpt-4o', label: 'GPT-4o', tag: '' },
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini', tag: '' },
  { value: 'gpt-5', label: 'GPT-5', tag: 'reasoning' },
  { value: 'gpt-5-mini', label: 'GPT-5 Mini', tag: 'reasoning' },
  { value: 'gpt-5.1', label: 'GPT-5.1', tag: 'reasoning' },
  { value: 'gpt-5.2', label: 'GPT-5.2', tag: 'reasoning' },
  { value: 'gpt-5-pro', label: 'GPT-5 Pro', tag: 'max reasoning' },
]

const ANTHROPIC_MODELS = [
  { value: 'claude-sonnet-4-6', label: 'Claude Sonnet 4.6', tag: 'recomendado' },
  { value: 'claude-haiku-4-5-20251001', label: 'Claude Haiku 4.5', tag: 'rápido' },
]

const MODEL_CATALOG: Record<string, typeof GOOGLE_MODELS> = {
  google: GOOGLE_MODELS,
  openai: OPENAI_MODELS,
  anthropic: ANTHROPIC_MODELS,
}

const PROVIDER_LABELS: Record<string, { label: string; color: string; icon: string }> = {
  google: { label: 'Google', color: 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/40 dark:text-blue-300', icon: 'auto_awesome' },
  openai: { label: 'OpenAI', color: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300', icon: 'psychology' },
  anthropic: { label: 'Anthropic', color: 'bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-950/40 dark:text-orange-300', icon: 'smart_toy' },
}

// ─── Types ───────────────────────────────────────────────────────

interface AIProvider {
  id: string
  tenant_id: string
  tenant_name: string | null
  provider: string
  model: string
  priority: number
  is_active: boolean
  usage_count: number
  last_used_at: string | null
}

interface Tenant {
  id: string
  name: string
}

// ─── Create Provider Form ────────────────────────────────────────

function CreateProviderDialog({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({
    tenant_id: '',
    provider: 'openai',
    model: 'gpt-4.1',
    api_key: '',
    priority: 0,
  })

  const { data: tenants } = useQuery<Tenant[]>({
    queryKey: ['admin-tenants'],
    queryFn: async () => {
      const res = await apiClient.get('/admin/tenants')
      return res.data.items ?? res.data
    },
  })

  const mutation = useMutation({
    mutationFn: (data: typeof form) => apiClient.post('/admin/agents/providers', data),
    onSuccess: () => {
      toast.success('Provedor criado com sucesso')
      setOpen(false)
      onCreated()
    },
    onError: () => toast.error('Erro ao criar provedor'),
  })

  const models = MODEL_CATALOG[form.provider] ?? []

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" className="gap-2">
          <span className="material-symbols-outlined text-lg">add</span>
          Novo Provedor
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Adicionar Provedor de IA</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 mt-2">
          <div className="space-y-1.5">
            <Label>Tenant</Label>
            <Select value={form.tenant_id} onValueChange={(v) => setForm((f) => ({ ...f, tenant_id: v }))}>
              <SelectTrigger>
                <SelectValue placeholder="Selecione o tenant..." />
              </SelectTrigger>
              <SelectContent>
                {(tenants ?? []).map((t) => (
                  <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label>Provedor</Label>
            <Select value={form.provider} onValueChange={(v) => setForm((f) => ({ ...f, provider: v, model: MODEL_CATALOG[v]?.[0]?.value ?? '' }))}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="google">Google</SelectItem>
                <SelectItem value="openai">OpenAI</SelectItem>
                <SelectItem value="anthropic">Anthropic</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label>Modelo</Label>
            <Select value={form.model} onValueChange={(v) => setForm((f) => ({ ...f, model: v }))}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {models.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    <span>{m.label}</span>
                    {m.tag && <span className="ml-2 text-xs text-muted-foreground">({m.tag})</span>}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label>API Key</Label>
            <Input
              type="password"
              placeholder="sk-..."
              value={form.api_key}
              onChange={(e) => setForm((f) => ({ ...f, api_key: e.target.value }))}
            />
          </div>

          <div className="space-y-1.5">
            <Label>Prioridade <span className="text-muted-foreground text-xs">(maior = preferido)</span></Label>
            <Input
              type="number"
              min={0}
              max={100}
              value={form.priority}
              onChange={(e) => setForm((f) => ({ ...f, priority: Number(e.target.value) }))}
            />
          </div>

          <Button
            className="w-full"
            disabled={!form.tenant_id || !form.api_key || mutation.isPending}
            onClick={() => mutation.mutate(form)}
          >
            {mutation.isPending ? 'Criando...' : 'Criar Provedor'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

// ─── Provider Row ─────────────────────────────────────────────────

function ProviderRow({ provider, onRefetch }: { provider: AIProvider; onRefetch: () => void }) {
  const [model, setModel] = useState(provider.model)
  const [priority, setPriority] = useState(provider.priority)
  const [dirty, setDirty] = useState(false)
  const qc = useQueryClient()

  const models = MODEL_CATALOG[provider.provider] ?? []
  const meta = PROVIDER_LABELS[provider.provider]

  const toggle = useMutation({
    mutationFn: () =>
      apiClient.put(`/admin/agents/providers/${provider.id}`, { is_active: !provider.is_active }),
    onSuccess: () => { onRefetch(); toast.success('Atualizado') },
    onError: () => toast.error('Erro ao atualizar'),
  })

  const save = useMutation({
    mutationFn: () =>
      apiClient.put(`/admin/agents/providers/${provider.id}`, { model, priority }),
    onSuccess: () => { setDirty(false); onRefetch(); toast.success('Salvo') },
    onError: () => toast.error('Erro ao salvar'),
  })

  const remove = useMutation({
    mutationFn: () => apiClient.delete(`/admin/agents/providers/${provider.id}`),
    onSuccess: () => { onRefetch(); toast.success('Removido') },
    onError: () => toast.error('Erro ao remover'),
  })

  return (
    <TableRow className={!provider.is_active ? 'opacity-50' : ''}>
      <TableCell className="font-medium text-sm">{provider.tenant_name ?? provider.tenant_id.slice(0, 8)}</TableCell>
      <TableCell>
        {meta && (
          <Badge variant="outline" className={`gap-1 text-xs ${meta.color}`}>
            <span className="material-symbols-outlined text-[13px]">{meta.icon}</span>
            {meta.label}
          </Badge>
        )}
      </TableCell>
      <TableCell>
        <Select
          value={model}
          onValueChange={(v) => { setModel(v); setDirty(true) }}
        >
          <SelectTrigger className="h-8 text-xs w-52">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {models.length > 0
              ? models.map((m) => (
                  <SelectItem key={m.value} value={m.value} className="text-xs">
                    {m.label}
                    {m.tag && <span className="ml-1.5 text-muted-foreground">({m.tag})</span>}
                  </SelectItem>
                ))
              : <SelectItem value={model}>{model}</SelectItem>
            }
          </SelectContent>
        </Select>
      </TableCell>
      <TableCell>
        <Input
          type="number"
          min={0}
          max={100}
          value={priority}
          onChange={(e) => { setPriority(Number(e.target.value)); setDirty(true) }}
          className="h-8 w-16 text-xs"
        />
      </TableCell>
      <TableCell className="text-xs text-muted-foreground">{provider.usage_count.toLocaleString('pt-BR')}</TableCell>
      <TableCell>
        <Switch
          checked={provider.is_active}
          onCheckedChange={() => toggle.mutate()}
          disabled={toggle.isPending}
        />
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-1">
          {dirty && (
            <Button
              size="sm"
              variant="default"
              className="h-7 px-2 text-xs"
              disabled={save.isPending}
              onClick={() => save.mutate()}
            >
              <span className="material-symbols-outlined text-sm">save</span>
            </Button>
          )}
          <Button
            size="sm"
            variant="ghost"
            className="h-7 w-7 p-0 text-destructive hover:bg-destructive/10"
            disabled={remove.isPending}
            onClick={() => {
              if (confirm('Remover este provedor?')) remove.mutate()
            }}
          >
            <span className="material-symbols-outlined text-sm">delete</span>
          </Button>
        </div>
      </TableCell>
    </TableRow>
  )
}

// ─── Page ─────────────────────────────────────────────────────────

export default function AdminIAPage() {
  const qc = useQueryClient()

  const { data: providers, isLoading, refetch } = useQuery<AIProvider[]>({
    queryKey: ['admin-ai-providers'],
    queryFn: async () => {
      const res = await apiClient.get('/admin/agents/providers')
      return res.data
    },
  })

  // Group by tenant
  const grouped = (providers ?? []).reduce<Record<string, AIProvider[]>>((acc, p) => {
    const key = p.tenant_name ?? p.tenant_id
    acc[key] = [...(acc[key] ?? []), p]
    return acc
  }, {})

  const totalActive = (providers ?? []).filter((p) => p.is_active).length
  const totalUsage = (providers ?? []).reduce((s, p) => s + p.usage_count, 0)

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="material-symbols-outlined text-amber-500 text-2xl">psychology</span>
            <h1 className="text-2xl font-bold">Provedores de IA</h1>
            <Badge variant="secondary" className="text-xs">Super Admin</Badge>
          </div>
          <p className="text-muted-foreground text-sm">
            Configure os modelos de IA por tenant. Cada provedor tem prioridade de fallback.
          </p>
        </div>
        <CreateProviderDialog onCreated={refetch} />
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-xl border bg-card p-4">
          <p className="text-xs text-muted-foreground uppercase tracking-wide">Total provedores</p>
          <p className="text-2xl font-bold mt-1">{providers?.length ?? 0}</p>
        </div>
        <div className="rounded-xl border bg-card p-4">
          <p className="text-xs text-muted-foreground uppercase tracking-wide">Ativos</p>
          <p className="text-2xl font-bold mt-1 text-emerald-600">{totalActive}</p>
        </div>
        <div className="rounded-xl border bg-card p-4">
          <p className="text-xs text-muted-foreground uppercase tracking-wide">Total chamadas</p>
          <p className="text-2xl font-bold mt-1">{totalUsage.toLocaleString('pt-BR')}</p>
        </div>
      </div>

      {/* Chains de fallback info */}
      <div className="rounded-xl border bg-muted/30 p-4 text-sm space-y-1">
        <p className="font-semibold text-foreground flex items-center gap-1.5">
          <span className="material-symbols-outlined text-base text-amber-500">info</span>
          Chains de fallback padrão (quando o tenant não tem provedores configurados)
        </p>
        <div className="grid grid-cols-3 gap-4 mt-2 text-xs text-muted-foreground">
          <div>
            <p className="font-medium text-foreground mb-1">🌐 Geral (default)</p>
            <p>1. GPT-4.1 (OpenAI)</p>
            <p>2. Gemini Flash Latest (Google)</p>
            <p>3. Claude Sonnet 4.6 (Anthropic)</p>
          </div>
          <div>
            <p className="font-medium text-foreground mb-1">📄 Documentos / Petições</p>
            <p>1. Gemini 3 Flash Preview (Google)</p>
            <p>2. GPT-4.1 (OpenAI)</p>
            <p>3. Claude Sonnet 4.6 (Anthropic)</p>
          </div>
          <div>
            <p className="font-medium text-foreground mb-1">⏰ Rotinas Diárias (DataJud)</p>
            <p>1. Gemini Flash Latest (Google)</p>
            <p>2. GPT-4.1 Mini (OpenAI)</p>
            <p>3. Claude Haiku 4.5 (Anthropic)</p>
          </div>
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center h-32 text-muted-foreground">
          <span className="material-symbols-outlined animate-spin mr-2">progress_activity</span>
          Carregando...
        </div>
      ) : !providers?.length ? (
        <div className="text-center py-16 text-muted-foreground">
          <span className="material-symbols-outlined text-4xl mb-2 block">smart_toy</span>
          Nenhum provedor configurado ainda.
        </div>
      ) : (
        <div className="rounded-xl border bg-card overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40">
                <TableHead className="text-xs">Tenant</TableHead>
                <TableHead className="text-xs">Provedor</TableHead>
                <TableHead className="text-xs">Modelo</TableHead>
                <TableHead className="text-xs">Prioridade</TableHead>
                <TableHead className="text-xs">Chamadas</TableHead>
                <TableHead className="text-xs">Ativo</TableHead>
                <TableHead className="text-xs">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(providers ?? []).map((p) => (
                <ProviderRow key={p.id} provider={p} onRefetch={refetch} />
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
