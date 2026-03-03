# JusMonitorIA — Pipeline de Scraping OAB

> **Última atualização:** 03/03/2026  
> **Status:** ✅ Pipeline 3-fases funcional — TRF1 (7 processos) e TRF5 (4 processos) validados  
> **Autor:** JAVIS

---

## Índice

1. [Visão Geral](#1-visão-geral)
2. [Arquitetura do Pipeline](#2-arquitetura-do-pipeline)
3. [Fases do Pipeline](#3-fases-do-pipeline)
4. [Microserviço Scraper](#4-microserviço-scraper)
5. [Backend — Orquestrador](#5-backend--orquestrador)
6. [API REST](#6-api-rest)
7. [Modelos de Dados](#7-modelos-de-dados)
8. [Tribunais Suportados](#8-tribunais-suportados)
9. [Download de PDFs (JSF)](#9-download-de-pdfs-jsf)
10. [Configurações e Variáveis de Ambiente](#10-configurações-e-variáveis-de-ambiente)
11. [Comandos de Operação](#11-comandos-de-operação)
12. [Resultados de Teste](#12-resultados-de-teste)
13. [Problemas Conhecidos e Soluções](#13-problemas-conhecidos-e-soluções)
14. [Próximos Passos](#14-próximos-passos)

---

## 1. Visão Geral

O sistema de scraping OAB permite a um advogado sincronizar automaticamente **todos os processos vinculados ao seu número de OAB** em tribunais brasileiros PJe. O sistema:

- **Busca** processos por OAB + UF em múltiplos tribunais
- **Extrai** partes, movimentações (paginadas) e links de documentos
- **Baixa** PDFs dos documentos e armazena no S3
- **Persiste** tudo no PostgreSQL com notificação em tempo real via WebSocket

### Fluxo do Usuário

```
1. Usuário acessa "Processos OAB" no frontend
2. Clica "Sincronizar"
3. Backend enfileira tarefa Taskiq
4. Worker orquestra o pipeline em 3 fases para cada tribunal
5. Frontend recebe progresso em tempo real via WebSocket
6. Processos aparecem na listagem com docs baixados
```

---

## 2. Arquitetura do Pipeline

### 2.1 Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────────────┐
│  Frontend (Next.js :3000)                                           │
│  POST /api/v1/casos-oab/sync  ──►  WebSocket /ws (progresso)       │
└──────────────────┬──────────────────────────────────────────────────┘
                   │ HTTP
┌──────────────────▼──────────────────────────────────────────────────┐
│  Backend API (FastAPI :8000)                                        │
│  ┌──────────────────┐  ┌─────────────────────────────────────────┐  │
│  │ casos_oab.py     │  │ caso_oab_service.py                    │  │
│  │ (endpoints)      │──│ enqueue_sync_oab() → Taskiq dispatch   │  │
│  └──────────────────┘  └─────────────────────────────────────────┘  │
└──────────────────┬──────────────────────────────────────────────────┘
                   │ Taskiq
┌──────────────────▼──────────────────────────────────────────────────┐
│  Worker (Taskiq)                                                    │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ scrape_pipeline.py → task_orquestrar_pipeline               │    │
│  │   Para cada tribunal da UF:                                 │    │
│  │     ├─ Fase 1: listar_processos()                           │    │
│  │     ├─ Fase 2: detalhar_processo() × N                      │    │
│  │     └─ Fase 3: baixar_documento() × M                       │    │
│  └─────────────────────────────────────────────────────────────┘    │
└──────────────────┬──────────────────────────────────────────────────┘
                   │ HTTP (httpx)
┌──────────────────▼──────────────────────────────────────────────────┐
│  Scraper (FastAPI :8001 — container dedicado com Playwright)        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ main.py      │  │ browser_pool │  │ pje_generic.py           │  │
│  │ (3 rotas)    │──│ (2 instâncias│──│ Motor genérico PJe       │  │
│  │              │  │  Chromium)   │  │ (6 tribunais suportados) │  │
│  └──────────────┘  └──────────────┘  └────────────┬─────────────┘  │
└───────────────────────────────────────────────────┬─────────────────┘
          │                                         │
          ▼                                         ▼
┌──────────────────┐                    ┌───────────────────────┐
│  S3 (objstore)   │                    │  Tribunais PJe        │
│  PDFs baixados   │                    │  (acesso direto HTTP) │
└──────────────────┘                    └───────────────────────┘
```

### 2.2 Comunicação entre serviços

| De | Para | Protocolo | Porta |
|---|---|---|---|
| Frontend | Backend | HTTP REST | 3000 → 8000 |
| Frontend | Backend | WebSocket | 3000 → 8000/ws |
| Backend | Worker | Taskiq (Redis) | — |
| Worker | Scraper | HTTP (httpx) | 8000 → 8001 |
| Scraper | Tribunais PJe | HTTP (Playwright) | 8001 → 443 |
| Scraper | S3 | HTTPS (boto3) | 8001 → objstoreapi |
| Worker | PostgreSQL | asyncpg | — → 5433 |

---

## 3. Fases do Pipeline

### 3.1 Fase 1 — Listar Processos

**Entrada:** `oab_numero`, `oab_uf`, `tribunal`  
**Saída:** Lista de processos básicos (número CNJ, classe, assunto, partes)  
**Timeout:** 180s

```
Scraper:
  1. Navega para {search_url} do tribunal
  2. Preenche campo OAB (fPP:Decoration:numeroOAB)
  3. Seleciona UF no Select2 (fPP:Decoration:estadoComboOAB)
  4. Executa pesquisa via JS: executarPesquisa()
  5. Aguarda AJAX (A4J.AJAX.Submit) completar
  6. Parse da tabela de resultados
  7. Retorna: [{numero, classe, assunto, partes}]
```

### 3.2 Fase 2 — Detalhar Processo

**Entrada:** `tribunal`, `numero_processo`, `oab_numero`, `oab_uf`  
**Saída:** Partes detalhadas, movimentações (paginadas), links de documentos  
**Timeout:** 60s

```
Scraper:
  1. Navega para formulário de busca
  2. Pesquisa pelo número CNJ específico
  3. Abre detalhes do processo (nova aba)
  4. Extrai partes: polo ativo, passivo, outros
  5. Extrai movimentações: paginação de 15/página, até 10 páginas (150 máx)
  6. Extrai links de documentos: href/onclick de cada item com ícone de documento
  7. Filtra apenas links válidos: documentoSemLoginHTML ou idProcessoDoc
  8. Retorna: {partes_detalhadas, movimentacoes, doc_links}
```

### 3.3 Fase 3 — Baixar Documento

**Entrada:** `tribunal`, `numero_processo`, `doc_url`, `doc_index`, `doc_description`  
**Saída:** URL S3 do PDF, tamanho, tipo classificado  
**Timeout:** 120s

```
Scraper:
  1. Abre o doc_url no navegador
  2. Tenta 3 estratégias de download (ver seção 9)
  3. Upload do PDF para S3
  4. Classifica tipo: SENTENCA, PETICAO, DESPACHO, DECISAO, ACORDAO, etc.
  5. Retorna: {s3_url, tamanho_bytes, nome, tipo}
```

### 3.4 Delays e Throttling

| Operação | Delay |
|---|---|
| Entre tribunais | 10s |
| Entre processos | 5s |
| Entre documentos | 3s |
| Per-tribunal (configurável) | 5-18s entre requests |
| Backoff on error | 30s |

---

## 4. Microserviço Scraper

### 4.1 Estrutura de Arquivos

```
scraper/
├── app/
│   ├── main.py              # FastAPI, lifespan, 4 endpoints
│   ├── config.py            # Settings: proxy, S3, timeouts, throttle
│   ├── schemas.py           # Pydantic: request/response para cada fase
│   ├── s3_client.py         # Upload S3 via boto3
│   ├── browser_pool.py      # Pool de 2 Chromium reutilizáveis
│   └── scrapers/
│       ├── base.py          # BaseScraper: Playwright + stealth v2
│       ├── pje_generic.py   # Motor PJe genérico (6 tribunais)
│       └── trf1.py          # Wrapper retrocompatível
├── pyproject.toml
└── Dockerfile
```

### 4.2 Endpoints do Scraper

| Método | Rota | Fase | Request | Response |
|---|---|---|---|---|
| `GET` | `/health` | — | — | `{status, tribunais}` |
| `POST` | `/scrape/listar-processos` | 1 | `{oab_numero, oab_uf, tribunal}` | `{sucesso, processos: [ProcessoBasico], total, tribunal}` |
| `POST` | `/scrape/detalhar-processo` | 2 | `{tribunal, numero_processo, oab_numero, oab_uf}` | `{sucesso, partes_detalhadas, movimentacoes, doc_links: [DocLink]}` |
| `POST` | `/scrape/baixar-documento` | 3 | `{tribunal, numero_processo, doc_url, doc_index, doc_description}` | `{sucesso, s3_url, tamanho_bytes, nome, tipo}` |
| `POST` | `/scrape/consultar-oab` | ⚠️ | `{oab_numero, oab_uf, tribunal}` | Legado (monolítico, deprecated) |

### 4.3 Browser Pool

- **Tamanho:** 2 instâncias Chromium simultâneas
- **Reciclagem:** Cada instância é reciclada após 20 usos
- **Stealth:** playwright-stealth v2 (compatível com A4J/RichFaces)
- **Locale:** `pt-BR`, timezone `America/Sao_Paulo`
- **User-Agent:** Chrome 131 (atualizar periodicamente)
- **Downloads:** `accept_downloads=True` habilitado
- **Isolamento:** Contexto limpo por request (sem cookies persistentes)
- **Anti-detecção:** `human_delay(min, max)` com jitter ±30%

### 4.4 Schemas do Scraper

```python
# Fase 1
class ProcessoBasico:
    numero: str          # "1013264-53.2025.4.01.3904"
    classe: str          # "Procedimento Comum Cível"
    assunto: str         # "Anulação e Correção de Provas"
    partes: str          # "FABIO JUNIOR x INEP"
    ultima_movimentacao: str | None
    data_ultima_movimentacao: str | None

# Fase 2
class DocLink:
    index: int           # Posição na lista de docs
    description: str     # "Sentença", "Despacho", etc.
    url: str             # URL absoluta do documento
    id_processo_doc: str | None  # ID único do doc no PJe

# Fase 3 (response)
class BaixarDocumentoResponse:
    sucesso: bool
    s3_url: str          # URL pública do PDF no S3
    tamanho_bytes: int
    nome: str            # "doc_0_Sentença.pdf"
    tipo: str            # "SENTENCA", "DESPACHO", etc.
```

---

## 5. Backend — Orquestrador

### 5.1 Task Taskiq: `task_orquestrar_pipeline`

**Arquivo:** `backend/app/workers/tasks/scrape_pipeline.py`

```python
@broker.task
async def task_orquestrar_pipeline(
    tenant_id_str: str,
    sync_config_id_str: str,
    oab_numero: str,
    oab_uf: str,
    tribunais: list[str],
    user_id_str: str
) -> dict
```

**Fluxo:**

```
1. Atualiza status → "running"
2. Para cada tribunal em tribunais:
   a. _pipeline_tribunal(tribunal, oab_numero, oab_uf, ...)
   b. Delay 10s entre tribunais
3. Atualiza status → "idle" (ou "error")
4. Retorna resumo: {total, novos_processos, novas_movimentacoes, docs_baixados}
```

**Progresso em tempo real:** A cada operação, atualiza `oab_sync_configs.progresso_detalhado` e emite WebSocket:

```json
{
  "fase_atual": "detalhando",
  "tribunal_atual": "trf1",
  "total_processos": 7,
  "processados": 3,
  "docs_baixados": 4,
  "mensagem": "Detalhando processo 3/7 no trf1..."
}
```

### 5.2 Mapeamento UF → Tribunais

**Constante:** `UF_TRIBUNAIS` em `scrape_pipeline.py`

Todas as UFs buscam nos 4 TRFs federais, pois um advogado pode ter processos em qualquer região:

```python
_ALL_TRFS = ["trf1", "trf3", "trf5", "trf6"]

UF_TRIBUNAIS = {
    "AC": _ALL_TRFS, "AL": _ALL_TRFS, "AM": _ALL_TRFS, ...
    "CE": _ALL_TRFS + ["tjce", "tjce2g"],  # CE inclui tribunais estaduais
    ...
}
```

| TRF | Região | UFs |
|---|---|---|
| TRF1 | 1ª Região | AC, AM, AP, BA, DF, GO, MA, MG*, MT, PA, PI, RO, RR, TO |
| TRF3 | 3ª Região | MS, SP |
| TRF5 | 5ª Região | AL, CE, PB, PE, RN, SE |
| TRF6 | 6ª Região | MG |

_*MG migrou do TRF1 para o TRF6 em outubro 2024, mas processos antigos permanecem no TRF1._

### 5.3 Scraper Client (HTTP)

**Arquivo:** `backend/app/core/services/scraper_client.py`

Wrapper `httpx` que chama o scraper via rede Docker (`http://scraper:8001`).

| Função | Timeout | Observação |
|---|---|---|
| `listar_processos()` | 180s | TRF3/TRF6 podem ser lentos |
| `detalhar_processo()` | 60s | 1 processo por vez |
| `baixar_documento()` | 120s | Inclui download + upload S3 |

### 5.4 Caso OAB Service

**Arquivo:** `backend/app/core/services/caso_oab_service.py`

| Método | Descrição |
|---|---|
| `enqueue_sync_oab()` | Enfileira sync no Taskiq. Cooldown de 5 min entre syncs manuais. |
| `get_sync_status()` | Retorna status do `oab_sync_configs` (idle/running/error + progresso). |

---

## 6. API REST

### 6.1 Endpoints — Router `/api/v1/casos-oab`

Todos requerem autenticação JWT (`Authorization: Bearer {token}`).

| Método | Rota | Descrição |
|---|---|---|
| `POST /sync` | Dispara sincronização manual da OAB do usuário |
| `GET /sync-status` | Status da sincronização (progresso, erros) |
| `GET /` | Lista processos sincronizados (paginado) |
| `GET /{caso_id}` | Detalhe completo: partes, movimentações, documentos |
| `POST /` | Adicionar processo manualmente (por nº CNJ) |
| `DELETE /{caso_id}` | Remover processo |
| `POST /{caso_id}/visto` | Marcar movimentações como lidas |

### 6.2 Exemplos de Uso

**Disparar sync:**
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"usuario@example.com","password":"senha"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -s -X POST http://localhost:8000/api/v1/casos-oab/sync \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Response sync:**
```json
{
    "sucesso": true,
    "mensagem": "Sincronização iniciada em background",
    "queued": true
}
```

**Verificar status:**
```bash
curl -s http://localhost:8000/api/v1/casos-oab/sync-status \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Listar processos:**
```bash
curl -s "http://localhost:8000/api/v1/casos-oab/?skip=0&limit=50" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

## 7. Modelos de Dados

### 7.1 Tabela `casos_oab`

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | UUID | PK |
| `tenant_id` | UUID FK | Multi-tenant |
| `numero` | VARCHAR(25) | Número CNJ (unique por tenant) |
| `classe` | VARCHAR(255) | Classe judicial |
| `assunto` | VARCHAR(255) | Assunto processual |
| `partes_resumo` | VARCHAR(500) | Partes (resumo texto) |
| `oab_numero` | VARCHAR(20) | Número OAB (indexado) |
| `oab_uf` | VARCHAR(2) | UF da OAB |
| `tribunal` | VARCHAR(20) | Código do tribunal (trf1, trf5, etc) |
| `partes_json` | JSONB | `[{polo, nome, papel, oab, documento}]` |
| `movimentacoes_json` | JSONB | `[{descricao, documento_vinculado, tem_documento}]` |
| `documentos_json` | JSONB | `[{nome, tipo, s3_url, tamanho_bytes, id_processo_doc}]` |
| `ultima_sincronizacao` | TIMESTAMPTZ | Último sync bem-sucedido |
| `total_movimentacoes` | INTEGER | Total de movimentações |
| `novas_movimentacoes` | INTEGER | Novas desde última visualização |
| `total_documentos` | INTEGER | Total de documentos |
| `monitoramento_ativo` | BOOLEAN | Monitoramento ativo/inativo |
| `criado_por` | UUID FK | Usuário que criou |

**Constraint:** `uq_casos_oab_tenant_numero` → (tenant_id, numero)

**Exemplo `partes_json`:**
```json
[
  {"polo": "ATIVO", "nome": "FABIO JUNIOR SANTOS REGO", "papel": "AUTOR", "oab": null, "documento": null},
  {"polo": "PASSIVO", "nome": "INEP", "papel": "RÉU", "oab": null, "documento": null},
  {"polo": "OUTROS", "nome": "AMANDA ALVES DE SOUSA", "papel": "ADVOGADO", "oab": "50784/CE", "documento": null}
]
```

**Exemplo `documentos_json`:**
```json
[
  {
    "nome": "doc_0_Sentença.pdf",
    "tipo": "SENTENCA",
    "s3_url": "https://objstoreapi.witdev.com.br/jusmonitoria/oab/50784-CE/1013264-53.2025.4.01.3904/doc_0_Sentenca.pdf",
    "tamanho_bytes": 52431,
    "id_processo_doc": "abc123"
  }
]
```

### 7.2 Tabela `oab_sync_configs`

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | UUID | PK |
| `tenant_id` | UUID FK | Multi-tenant |
| `oab_numero` | VARCHAR(20) | Número OAB |
| `oab_uf` | VARCHAR(2) | UF da OAB |
| `tribunal` | VARCHAR(20) | Tribunal alvo |
| `ultimo_sync` | TIMESTAMPTZ | Timestamp do último sync |
| `status` | VARCHAR(20) | `idle` / `running` / `error` |
| `erro_mensagem` | TEXT | Mensagem do último erro |
| `total_processos` | INTEGER | Processos encontrados |
| `progresso_detalhado` | JSONB | Progresso em tempo real (ver 5.1) |
| `tribunais` | JSONB | Lista de tribunais a sincronizar |

**Constraint:** `uq_oab_sync_tenant_oab` → (tenant_id, oab_numero, oab_uf)

### 7.3 Tabela `scrape_jobs`

Rastreamento granular de cada unidade de trabalho no pipeline (atualmente informacional, não usado para retry automático).

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | UUID | PK |
| `parent_job_id` | UUID FK | Job pai (árvore: listing → detail → document) |
| `fase` | VARCHAR(20) | `listing` / `detail` / `document` |
| `status` | VARCHAR(20) | `pending` / `running` / `completed` / `failed` / `blocked` |
| `tribunal` | VARCHAR(20) | Tribunal |
| `oab_numero` / `oab_uf` | VARCHAR | Contexto OAB |
| `numero_processo` | VARCHAR(25) | Nº CNJ (fases 2 e 3) |
| `doc_id` / `doc_url` | VARCHAR/TEXT | Contexto do documento (fase 3) |
| `tentativas` / `max_tentativas` | INTEGER | Retry tracking (máx padrão: 3) |
| `resultado_json` | JSONB | Resultado em caso de sucesso |
| `sync_config_id` | UUID FK | Configuração de sync pai |

---

## 8. Tribunais Suportados

### 8.1 Motor PJe Genérico

Todos os tribunais PJe usam a mesma interface (JBoss Seam + RichFaces/JSF). Um único scraper genérico atende todos — a diferença é apenas a URL base.

| Tribunal | Código | URL Consulta Pública | Status |
|----------|--------|----------------------|--------|
| TRF1 — 1ª Região | `trf1` | `pje1g-consultapublica.trf1.jus.br` | ✅ 7 processos |
| TRF3 — 3ª Região (SP/MS) | `trf3` | `pje1g.trf3.jus.br` | ⏳ Site lento (Akamai) |
| TRF5 — 5ª Região (NE) | `trf5` | `pje1g.trf5.jus.br` | ✅ 4 processos |
| TRF6 — 6ª Região (MG) | `trf6` | `pje1g.trf6.jus.br` | ⏳ Pendente teste |
| TJCE 1º Grau | `tjce` | `pje.tjce.jus.br/pje1grau` | ✅ (0 resultados) |
| TJCE 2º Grau | `tjce2g` | `pje.tjce.jus.br/pje2grau` | ✅ (0 resultados) |

### 8.2 Tribunais Futuros (EPROC — motor diferente)

| Tribunal | URL | Sistema |
|----------|-----|---------|
| TRF2 — 2ª Região (RJ/ES) | `eproc-consulta.trf2.jus.br` | EPROC (PHP) |
| TRF4 — 4ª Região (PR/SC/RS) | `www.trf4.jus.br` | EPROC (PHP) |

### 8.3 Registro de Tribunais

**Arquivo:** `scraper/app/scrapers/pje_generic.py` → `PJE_TRIBUNALS`

```python
@dataclass
class PJeTribunalConfig:
    code: str       # "trf1"
    name: str       # "TRF1 - 1ª Região"
    base_url: str   # "https://pje1g-consultapublica.trf1.jus.br/consultapublica"
    search_url: str # "{base_url}/ConsultaPublica/listView.seam"

PJE_TRIBUNALS = {
    "trf1": PJeTribunalConfig(code="trf1", name="TRF1 - 1ª Região", ...),
    "trf3": PJeTribunalConfig(code="trf3", name="TRF3 - 3ª Região", ...),
    "trf5": PJeTribunalConfig(code="trf5", name="TRF5 - 5ª Região", ...),
    "trf6": PJeTribunalConfig(code="trf6", name="TRF6 - 6ª Região", ...),
    "tjce": PJeTribunalConfig(code="tjce", name="TJCE 1º Grau", ...),
    "tjce2g": PJeTribunalConfig(code="tjce2g", name="TJCE 2º Grau", ...),
}
```

Para adicionar um novo tribunal PJe, basta adicionar uma entrada ao dicionário.

---

## 9. Download de PDFs (JSF)

### 9.1 Mecanismo JSF do PJe

O botão "Gerar PDF" nos documentos PJe usa JavaServer Faces (JSF) com a função `jsfcljs()`:

```html
<a onclick="if(typeof jsfcljs == 'function'){
    jsfcljs(document.getElementById('j_id43'),{
        'j_id43:downloadPDF':'j_id43:downloadPDF',
        'ca':'WxVVFSY6fxM%3D',
        'idProcDocBin':'1234567'
    },'')
}" id="j_id43:downloadPDF" href="#">GERAR PDF</a>
```

**Parâmetros necessários:**
- `j_id43:downloadPDF` — ID do botão
- `ca` — Token de autenticação (muda por sessão/doc)
- `idProcDocBin` — ID binário do documento no PJe
- `javax.faces.ViewState` — Estado JSF (hidden input)

### 9.2 Estratégias de Download (3 fallbacks)

O scraper tenta 3 estratégias na ordem, com fallback automático:

#### Estratégia 1 — JSF Form POST (`_download_pdf_via_jsf_form`)

```
1. Localiza onclick do botão "Gerar PDF" na página
2. Extrai ca, idProcDocBin via JavaScript
3. Extrai javax.faces.ViewState do form j_id43
4. POST form-encoded para a URL da página
5. Espera response com content-type application/pdf
```

**Vantagem:** PDF nativo do tribunal (qualidade original).  
**Requer:** Página do documento aberta no navegador com form JSF presente.

#### Estratégia 2 — Click + expect_download

```
1. Localiza botão "Gerar PDF" por texto
2. Clica e aguarda evento download do Playwright
3. Lê bytes do arquivo baixado
```

**Vantagem:** Mais simples, funciona se JSF gerar download direto.  
**Limitação:** Nem sempre dispara download (JSF pode abrir em nova aba).

#### Estratégia 3 — page.pdf() (fallback final)

```
1. Renderiza a página atual como PDF via Playwright
2. Formato A4 com cabeçalho de data/hora
```

**Vantagem:** Sempre funciona.  
**Limitação:** PDF renderizado (não nativo), ~44-62KB.

### 9.3 IDs Fixos JSF (padrão em todos os PJe)

| Campo | ID | Notas |
|---|---|---|
| Formulário de busca | `fPP` | Formulário principal |
| OAB número | `fPP:Decoration:numeroOAB` | Input text |
| OAB UF | `fPP:Decoration:estadoComboOAB` | Select2 dropdown |
| Botão pesquisar | `fPP:searchProcessos` | Dispara AJAX A4J |
| Form do PDF | `j_id43` | Presente na página do doc |
| Botão Gerar PDF | `j_id43:downloadPDF` | Onclick com jsfcljs() |
| ViewState | `javax.faces.ViewState` | Hidden input (muda por sessão) |

---

## 10. Configurações e Variáveis de Ambiente

### 10.1 Scraper

```env
# S3 Storage
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
S3_BUCKET=jusmonitoria
S3_ENDPOINT=objstoreapi.witdev.com.br

# Proxy (configurado mas NÃO usado para .jus.br)
SMARTPROXY_DECODO=true
PROXY_HOST=gate.decodo.com
PROXY_PORT=7000
PROXY_USER=...
PROXY_PASS=...

# Browser Pool
BROWSER_POOL_SIZE=2
BROWSER_MAX_USES=20
NAVIGATION_TIMEOUT=60
WAIT_TIMEOUT=20
```

### 10.2 Backend (Timeouts do scraper client)

```python
# backend/app/core/services/scraper_client.py
TIMEOUT_LISTAR = 180.0    # Fase 1 (tribunais lentos como TRF3)
TIMEOUT_DETALHAR = 60.0   # Fase 2
TIMEOUT_DOCUMENTO = 120.0 # Fase 3 (download + S3)
```

### 10.3 Throttling por Tribunal

```python
# scraper/app/config.py → TribunalThrottleConfig
tribunal_throttle = {
    "trf1":  {max_concurrent: 1, delay_between: 8s,  docs_delay: 5s, max/h: 30},
    "trf3":  {max_concurrent: 1, delay_between: 18s, docs_delay: 8s, max/h: 25},
    "trf5":  {max_concurrent: 1, delay_between: 5s,  docs_delay: 3s, max/h: 40},
    "trf6":  {max_concurrent: 1, delay_between: 10s, docs_delay: 5s, max/h: 30},
    "tjce":  {max_concurrent: 1, delay_between: 8s,  docs_delay: 5s, max/h: 30},
    "tjce2g":{max_concurrent: 1, delay_between: 8s,  docs_delay: 5s, max/h: 30},
}
```

### 10.4 Proxy

**IMPORTANTE:** O proxy Decodo bloqueia domínios `.jus.br` (403 Forbidden). Todo o scraping de tribunais usa **acesso direto** (IP do servidor).

O proxy Decodo está configurado para uso futuro em scraping de sites não-governamentais.

---

## 11. Comandos de Operação

### 11.1 Iniciar Serviços

```bash
# Todos os serviços
./dev.sh
# Ou
docker compose up -d

# Apenas scraper (após rebuild)
docker compose build scraper --no-cache && docker compose up -d --force-recreate scraper
```

### 11.2 Monitorar

```bash
# Logs do scraper
docker compose logs -f scraper

# Logs do worker (pipeline)
docker compose logs -f worker

# Health check
docker exec jusmonitoria-backend curl -s http://scraper:8001/health | python3 -m json.tool
```

### 11.3 Consultar Dados

```bash
# Ver processos salvos
docker exec jusmonitoria-postgres sh -c "PAGER=cat psql -U jusmonitoria -d jusmonitoria -c \
  \"SELECT numero, tribunal, total_movimentacoes, total_documentos, \
   jsonb_array_length(COALESCE(documentos_json, '[]'::jsonb)) as docs_saved FROM casos_oab;\""

# Status do sync
docker exec jusmonitoria-postgres sh -c "PAGER=cat psql -U jusmonitoria -d jusmonitoria -c \
  \"SELECT oab_numero, oab_uf, status, total_processos, erro_mensagem FROM oab_sync_configs;\""

# Resetar para novo teste
docker exec jusmonitoria-postgres sh -c "PAGER=cat psql -U jusmonitoria -d jusmonitoria -c \
  \"UPDATE oab_sync_configs SET ultimo_sync = NULL, status = 'idle'; DELETE FROM casos_oab;\""
```

### 11.4 Disparar Sync Manual

```bash
# Login + sync em um comando
MYTOKEN=$(docker exec jusmonitoria-backend curl -s -X POST \
  http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])") && \
docker exec jusmonitoria-backend curl -s -X POST \
  http://localhost:8000/api/v1/casos-oab/sync \
  -H "Authorization: Bearer $MYTOKEN" \
  -H "Content-Type: application/json" | python3 -m json.tool
```

---

## 12. Resultados de Teste

### 12.1 Resumo (03/03/2026)

| Tribunal | Status | Processos | Documentos | Observação |
|----------|--------|-----------|------------|------------|
| **TRF1** | ✅ OK | 7 | 8 PDFs | Testado e validado |
| **TRF5** | ✅ OK | 4 | 7 PDFs | Testado e validado |
| **TRF3** | ⏳ Timeout | 0 | 0 | Site Akamai lento (timeout aumentado para 180s) |
| **TRF6** | ⏳ Pendente | — | — | Configurado, pendente teste |
| **TJCE 1G** | ✅ (0 result) | 0 | 0 | OAB sem processos ativos |
| **TJCE 2G** | ✅ (0 result) | 0 | 0 | OAB sem processos ativos |

### 12.2 TRF1 — 7 Processos

| Nº CNJ | Assunto | Docs |
|--------|---------|------|
| 1013264-53.2025.4.01.3904 | Exame da Ordem OAB | 1 |
| 1014980-12.2025.4.01.4100 | Anulação e Correção de Provas | 1 |
| 1089764-32.2025.4.01.3300 | Anulação e Correção de Provas | 1 |
| 1098298-53.2025.4.01.3400 | Exame da Ordem OAB | 2 |
| 1000511-48.2026.4.01.3704 | Anulação e Correção de Provas | 1 |
| 1000589-45.2026.4.01.3315 | Anulação e Correção de Provas | 1 |
| 1000654-37.2026.4.01.3704 | Anulação e Correção de Provas | 0 |

### 12.3 TRF5 — 4 Processos

| Nº CNJ | Cliente | Docs |
|--------|---------|------|
| 0013862-35.2025.4.05.8100 | JENNIFFER ALVES MACHADO | 1 (Sentença) |
| 0016468-42.2025.4.05.8001 | ALADSON SILVA DOS SANTOS | 4 (Sentença, 2 Despachos, Decisão) |
| 0017908-67.2025.4.05.8100 | ANTONIO CARLOS DE SOUSA HOLANDA | 1 (Acórdão) |
| 0001440-85.2026.4.05.8102 | JOSE JOAQUIM DOS SANTOS | 1 (Decisão) |

### 12.4 Planilha Completa de Processos (OAB 50784/CE)

| Cliente | Nº Processo | Tribunal | Status |
|---------|-------------|----------|--------|
| ALEX SILVA MICIO DOS SANTOS | 1089764-32.2025.4.01.3300 | TRF1 | ✅ |
| EDUARDO CAVALCANTE LEMOS | 1098298-53.2025.4.01.3400 | TRF1 | ✅ |
| JOSE IRAN DE FIGUEIREDO | 1014980-12.2025.4.01.4100 | TRF1 | ✅ |
| FABIO JUNIOR SANTOS REGO | 1013264-53.2025.4.01.3904 | TRF1 | ✅ |
| GUSTAVO MULLER OLIVEIRA SAMPAIO | 1000589-45.2026.4.01.3315 | TRF1 | ✅ |
| ALAN CASSIO JORGE DE MELO | 1000511-48.2026.4.01.3704 | TRF1 | ✅ |
| JENNIFFER ALVES MACHADO | 0013862-35.2025.4.05.8100 | TRF5 | ✅ |
| ALADSON SILVA DOS SANTOS | 0016468-42.2025.4.05.8001 | TRF5 | ✅ |
| ANTONIO CARLOS DE SOUSA HOLANDA | 0017908-67.2025.4.05.8100 | TRF5 | ✅ |
| JOSE JOAQUIM DOS SANTOS | 0001440-85.2026.4.05.8102 | TRF5 | ✅ |
| ENZO MAXUEL DUARTE | 0004233-37.2025.4.05.8100 | TRF5 | ⚠️ Encerrado |
| WILSON MOURA DE ALMEIDA | 5026738-74.2025.4.03.6100 | TRF3 | ⏳ Timeout |
| ELIZABETH DE LIMA ALVES | 5002323-21.2025.4.03.6005 | TRF3 | ⏳ Timeout |
| RENATA CANDIDA M. R. SILVEIRA | 6008485-08.2025.4.06.3814 | TRF6 | ⏳ Pendente |
| KATIA APARECIDA DA C. F. SANTOS | 6397294-40.2025.4.06.3800 | TRF6 | ⏳ Pendente |
| GRAZIELA GONCALVES NASCIMENTO | 6005564-73.2025.4.06.3815 | TRF6 | ⏳ Pendente |
| STELLA CARVALHO FERNANDES | 6000791-84.2026.4.06.3803 | TRF6 | ⏳ Pendente |
| FRANCISCA ANGELICA F. FARIAS | 0206561-11.2023.8.06.0001 | TJCE 1G | ⚠️ Arquivado |
| BRUNO DA SILVA THOMAS | 3037553-48.2024.8.06.0001 | TJCE 2G | ⚠️ Trânsito julgado |

---

## 13. Problemas Conhecidos e Soluções

| # | Problema | Causa Raiz | Solução Aplicada |
|---|----------|------------|------------------|
| 1 | A4J não inicializa com stealth | playwright-stealth v1 JSON polyfill | Atualizado para stealth v2.0.2 |
| 2 | Botão pesquisar não dispara AJAX | `onclick` retorna `executarReCaptcha()` | Chamar `executarPesquisa()` via JS |
| 3 | CSS selectors com `:` falham | IDs JSF têm `:` | Usar `[id='...']` attribute selector |
| 4 | `wait_for_selector` timeout | Rows ficam hidden | Usar `state="attached"` |
| 5 | TRF3 ERR_HTTP2_PROTOCOL_ERROR | Akamai CDN | `--disable-http2` no Chromium args |
| 6 | Proxy 403 em .jus.br | Decodo bloqueia .gov | Acesso direto (sem proxy) |
| 7 | Campo `tribunal` sempre "trf1" | Hardcoded no `upsert_from_scraper()` | Parametrizado via argumento `tribunal` |
| 8 | PDFs vazios (0 bytes) | POST sem `ca` e `idProcDocBin` | Reescrito extração de params JSF |
| 9 | Doc links com `openPopUp()` ignorados | Regex só capturava `window.open()` | Adicionado padrão `openPopUp\(` |
| 10 | URLs relativas causavam erro | `page.goto` recebia path sem domínio | Prepend `config.base_url` para paths relativos |
| 11 | Links de recibos/certidões baixados | Sem filtro de tipo de documento | Filtro: apenas `documentoSemLoginHTML` ou `idProcessoDoc` |
| 12 | TRF1 não encontrado para OAB do CE | `UF_TRIBUNAIS["CE"]` não incluía TRF1 | Todas as UFs agora buscam em todos os 4 TRFs |
| 13 | TRF3 timeout em 90s | Site Akamai muito lento | Timeout aumentado para 180s (client) e 120s (goto) |

### 13.1 playwright-stealth: v1 vs v2

| Configuração | A4J AJAX | webdriver detect |
|---|---|---|
| Sem stealth | ✅ Funciona | Detectável |
| Stealth v2.0.2 | ✅ Funciona | Não detectável |
| Stealth v1.0.6 | ❌ Quebra A4J | Não detectável |

**Conclusão:** Usar apenas stealth v2+ para sites PJe.

---

## 14. Próximos Passos

### Alta Prioridade
- [ ] Retestar TRF3 (timeout aumentado, verificar se Akamai resolve)
- [ ] Testar TRF6 com OAB 50784/CE (4 processos esperados)
- [ ] Validar Estratégia 1 de PDF (JSF form POST) — logging INFO adicionado

### Média Prioridade
- [ ] Retry com backoff exponencial para processos que falharem
- [ ] Scheduler automático (cron) para sync periódico (ex: a cada 6h)
- [ ] Melhorar parsing de partes (limpar entradas espúrias)
- [ ] Dead code cleanup: remover `_find_embedded_pdf` e `consultar_oab_pje`

### Baixa Prioridade
- [ ] Scrapers EPROC para TRF2 e TRF4 (motor PHP diferente)
- [ ] Dashboard no frontend com filtros por tribunal/status/data
- [ ] Notificações push para novas movimentações
- [ ] OCR para PDFs escaneados (Tesseract/Vision)

---

## Apêndice A — Estrutura Completa de Arquivos

```
scraper/
├── app/
│   ├── main.py              # FastAPI app, 4 endpoints, lifespan
│   ├── config.py            # Settings, throttle, proxy, S3
│   ├── schemas.py           # Pydantic: ListarProcessos, Detalhar, Baixar
│   ├── s3_client.py         # Upload boto3 → objstoreapi.witdev.com.br
│   ├── browser_pool.py      # Pool 2× Chromium, recicla cada 20 usos
│   └── scrapers/
│       ├── base.py          # BaseScraper: context manager Playwright
│       ├── pje_generic.py   # Motor PJe genérico (1379 linhas)
│       └── trf1.py          # Retrocompatibilidade

backend/
├── app/
│   ├── api/v1/endpoints/
│   │   └── casos_oab.py     # 7 endpoints REST
│   ├── core/services/
│   │   ├── caso_oab_service.py     # Service layer + Taskiq dispatch
│   │   ├── scraper_client.py       # HTTP client → scraper:8001
│   │   └── oab_finder_service.py   # Legado (monolítico)
│   ├── db/
│   │   ├── models/
│   │   │   ├── caso_oab.py         # Table casos_oab
│   │   │   ├── oab_sync_config.py  # Table oab_sync_configs
│   │   │   └── scrape_job.py       # Table scrape_jobs
│   │   └── repositories/
│   │       ├── caso_oab.py         # upsert_from_scraper, add_document
│   │       └── scrape_job.py       # CRUD scrape_jobs
│   ├── schemas/
│   │   └── caso_oab.py     # Pydantic: Create, ListItem, Detail, SyncStatus
│   └── workers/tasks/
│       └── scrape_pipeline.py  # Taskiq: task_orquestrar_pipeline
```
