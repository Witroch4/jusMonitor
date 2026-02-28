# Módulo de Petições — v1.0

> Status: Frontend completo com mock data. Backend pendente.

---

## Visão Geral

Sistema de gestão e protocolo eletrônico de petições judiciais via PJe/MNI (Modelo Nacional de Interoperabilidade 2.2.2). Suporta conexão direta com tribunais brasileiros usando certificado digital A1 (ICP-Brasil) e mTLS.

## Arquitetura Frontend

### Rotas

| Rota | Arquivo | Descrição |
|------|---------|-----------|
| `/peticoes` | `app/(dashboard)/peticoes/page.tsx` | Lista + formulário (toggle via state) |
| `/peticoes/[id]` | `app/(dashboard)/peticoes/[id]/page.tsx` | Detalhe com tabs |

### Componentes (`components/peticoes/`)

| Componente | Responsabilidade |
|------------|-----------------|
| `PeticaoList` | Tabela com filtros (busca, status, tribunal), paginação, skeleton loading |
| `PeticaoForm` | Orquestrador do formulário — monta as seções e gerencia estado |
| `PeticaoFormDadosProcesso` | Tribunal (agrupado por jurisdição), nº processo, tipo, assunto |
| `PeticaoFormUpload` | Drag-drop multi-arquivo, validação 5MB, tipo por documento |
| `PeticaoFormCertificado` | Seleção de certificado A1, teste mTLS, alerta de expiração |
| `PeticaoFormRevisao` | Checklist de validação (7 itens) + resumo dos dados |
| `PeticaoAnaliseIA` | Painel gradiente escuro com scores e feedback da IA |
| `CertificadoModal` | Dialog para gerenciar certificados (CRUD + teste) |
| `PeticaoStatusBadge` | Badge colorido para os 7 estados de uma petição |
| `PeticaoStatusTimeline` | Timeline vertical de eventos (página de detalhe) |
| `PeticaoDocumentos` | Tabela de documentos anexados |

### Types (`types/peticoes.ts`)

- `PeticaoStatus`: rascunho → validando → assinando → protocolando → protocolada → aceita | rejeitada
- `TipoPeticao`: 9 tipos (inicial, contestação, recurso, agravo, embargos, HC, MS, manifestação, outro)
- `Tribunal`: id, nome, sistema (PJe/e-SAJ/EPROC), WSDL endpoint, limite arquivo, flag mTLS
- `CertificadoDigital`: titular, emissora ICP-Brasil, serial, validade, criptografia AES-128-CBC
- `AnaliseIA`: scores (consistência, jurisprudência, formatação), feedback, sugestões

### Hooks React Query (`hooks/api/`)

| Hook | Query Key | Fonte (v1.0) |
|------|-----------|--------------|
| `usePeticoes(filters)` | `['peticoes', filters]` | `lib/mock/peticoes-data.ts` |
| `usePeticao(id)` | `['peticoes', id]` | mock |
| `usePeticaoEventos(id)` | `['peticoes', id, 'eventos']` | mock |
| `useCreatePeticao()` | invalida `['peticoes']` | mock |
| `useAnaliseIA()` | mutation | mock (2s delay simulado) |
| `useCertificados()` | `['certificados']` | `lib/mock/certificados-data.ts` |
| `useTestarCertificado()` | invalida `['certificados']` | mock (1.5s delay) |
| `useUploadCertificado()` | invalida `['certificados']` | mock |
| `useRemoverCertificado()` | invalida `['certificados']` | mock |

### Dados de Tribunais (`lib/data/tribunais.ts`)

13 tribunais mapeados com endpoints MNI reais:

| Tribunal | Sistema | Endpoint WSDL |
|----------|---------|---------------|
| TJCE 1º Grau | PJe | `pjews.tjce.jus.br/pje1grau/intercomunicacao` |
| TJCE 2º Grau | e-SAJ | — (roteamento por NPU) |
| TRF5 / JFCE | PJe | `pje.jfce.jus.br/pje/intercomunicacao?wsdl` |
| TRF5 Regional | PJe | `pje.trf5.jus.br/pje/intercomunicacao?wsdl` |
| TRF3 1º Grau | PJe | `pje1g.trf3.jus.br/pje/intercomunicacao?wsdl` |
| TRF3 2º Grau | PJe | `pje2g.trf3.jus.br/pje/intercomunicacao?wsdl` |
| TRF1 1º/2º Grau | PJe | `pje1g.trf1.jus.br/...` (instável, retry obrigatório) |
| TRF4 | EPROC | `eproc.trf4.jus.br/eproc2trf4/intercomunicacao?wsdl` |
| TRT7 | PJe-CSJT | — |
| STF / STJ | PJe | — |
| TJSP | e-SAJ | — |

---

## Mock Data (v1.0)

- **10 petições** cobrindo todos os 7 status, 6 tribunais diferentes
- **3 certificados**: válido (expira set/2026), expirando (expira mar/2026), expirado (dez/2025)
- Todas as funções retornam `Promise` com `setTimeout` simulando latência (200-500ms)

---

## Fluxo do Usuário

```
/peticoes (Lista)
  │
  ├─ [Filtrar] busca + status + tribunal
  ├─ [Click row] → /peticoes/[id] (Detalhe)
  │     ├─ Tab Detalhes: info do processo + análise IA
  │     ├─ Tab Documentos: tabela de PDFs
  │     └─ Tab Histórico: timeline de status
  │
  └─ [Nova Petição] → Formulário
        ├─ 1. Dados do Processo (tribunal, nº, tipo, assunto)
        ├─ 2. Upload (drag-drop, multi-PDF, validação 5MB)
        ├─ 3. Revisão (checklist de 7 itens)
        ├─ [Sidebar] Análise IA (auto-trigger após upload)
        ├─ [Sidebar] Certificado A1 (seleção + teste mTLS)
        └─ [Botão fixo] Protocolar Petição (habilitado quando checklist OK)
```

---

## Pendências para v2.0

### Backend (Python/FastAPI)

- [ ] Model `Petition` estendendo `TenantBaseModel`
- [ ] Repository + CRUD endpoints (`/api/v1/peticoes`)
- [ ] Endpoint upload de documentos (`/api/v1/peticoes/{id}/documentos`)
- [ ] Endpoint de certificados (`/api/v1/certificados`) com criptografia Fernet/AES-128-CBC
- [ ] Integração SOAP/WSDL com `zeep` + `requests` (mTLS)
- [ ] Método `entregarManifestacaoProcessual` do MNI
- [ ] Worker Taskiq para protocolo assíncrono
- [ ] Assinatura digital do PDF com `endesive`/`signxml`

### Frontend

- [ ] Trocar mock data por chamadas `apiClient` reais
- [ ] WebSocket para status updates em tempo real
- [ ] Máscara de input CNJ (formato `NNNNNNN-DD.AAAA.J.TR.OOOO`)
- [ ] Validação Zod no formulário
- [ ] Toast notifications (sucesso/erro no protocolo)
- [ ] Tela de onboarding de certificado com leitura de `not_valid_after`
- [ ] Splitter de PDF para arquivos >5MB

### Segurança

- [ ] Criptografia do PFX com Fernet (chave via `ENCRYPKEY` env var)
- [ ] Descriptografia em RAM only (tempfile + unlink)
- [ ] Validação de cadeia ICP-Brasil
- [ ] Rate limiting por tribunal
- [ ] Audit log de protocolo

---

## Árvore de Arquivos

```
frontend/
├── types/peticoes.ts
├── lib/
│   ├── data/tribunais.ts
│   └── mock/
│       ├── peticoes-data.ts
│       └── certificados-data.ts
├── hooks/api/
│   ├── usePeticoes.ts
│   └── useCertificados.ts
├── components/peticoes/
│   ├── PeticaoStatusBadge.tsx
│   ├── PeticaoList.tsx
│   ├── PeticaoForm.tsx
│   ├── PeticaoFormDadosProcesso.tsx
│   ├── PeticaoFormUpload.tsx
│   ├── PeticaoFormCertificado.tsx
│   ├── PeticaoFormRevisao.tsx
│   ├── PeticaoAnaliseIA.tsx
│   ├── CertificadoModal.tsx
│   ├── PeticaoStatusTimeline.tsx
│   └── PeticaoDocumentos.tsx
└── app/(dashboard)/peticoes/
    ├── page.tsx
    └── [id]/page.tsx
```
