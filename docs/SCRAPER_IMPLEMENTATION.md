# JusMonitorIA — Scraper Service: Implementação e Próximos Passos

> **Data:** 02/03/2026
> **Status:** ✅ FUNCIONANDO — 7/7 processos, partes, movimentações e PDFs extraídos com sucesso

---

## 0. Resultados dos Testes (02/03/2026) — LEIA PRIMEIRO

### 0.1 Teste Final — Docker headless SEM stealth, SEM proxy

**Resultado: ✅ FUNCIONA COMPLETAMENTE**

| Passo | Resultado |
|-------|-----------|
| GET listView.seam | ✅ Página carrega |
| Preencher OAB 50784 + UF CE | ✅ Campos preenchidos |
| `executarPesquisa()` via JS | ✅ A4J.AJAX.Submit dispara, **7 resultados em 2s** |
| Parse da lista | ✅ 7 processos com classe, assunto, partes, última movimentação |
| Ver detalhes (7 abas) | ✅ Partes detalhadas (15-23/processo), movimentações (7-22/processo) |
| Download PDFs | ✅ 8 PDFs baixados via "Gerar PDF" |
| Upload S3 | ✅ Todos os PDFs uploaded para `objstoreapi.witdev.com.br` |

### 0.2 Root Cause: playwright-stealth quebrava A4J

**Confirmado por teste A/B:**
- **SEM stealth** → `A4J=True` imediatamente após page load
- **COM stealth** → `A4J=False` mesmo após 17s de espera

O `playwright-stealth` injeta um polyfill de JSON que o hCaptcha detecta
(`"[hCaptcha] Custom JSON polyfill detected"`) e que impede o RichFaces
A4J de inicializar. **Solução: remover stealth** — o site é consulta
pública e não tem proteção anti-bot.

### 0.3 Root Cause: onclick do botão bloqueava A4J.AJAX.Submit

O `onclick` do botão Pesquisar é:
```
return executarReCaptcha();;A4J.AJAX.Submit(...)
```

Quando `executarReCaptcha()` retorna truthy, o `return` sai do handler
**antes** de `A4J.AJAX.Submit` executar. A função `executarPesquisa()`
(chamada internamente por `executarReCaptcha` quando captcha está
desabilitado) chama `A4J.AJAX.Submit` diretamente.

**Solução:** chamar `executarPesquisa()` via JS em vez de `click()`.

### 0.4 Proxy Bright Data — NÃO necessário

O scraper funciona sem proxy (acesso direto ao site). O Bright Data em
modo Immediate Access (sem KYC) bloqueia POSTs (402). Como o site não
tem rate limiting agressivo para consulta pública, proxy não é necessário
para o fluxo atual.

---

---

## 1. O Que Foi Feito

### 1.1 Arquitetura

Criado um **microserviço isolado de scraping** (`scraper/`) separado do backend, rodando em container Docker dedicado com limite de 2 CPU / 4 GB RAM. O Chromium/Playwright não roda mais no backend.

```
Backend (FastAPI:8000) ──HTTP──► Scraper (FastAPI:8001) ──Bright Data Proxy──► TRF1 PJe
                                        │
                                   S3 (objstoreapi.witdev.com.br)
                                        ↑
                                   PDFs baixados e salvos
```

### 1.2 Arquivos Criados/Modificados

#### Scraper (novo serviço)

| Arquivo | Descrição |
|---------|-----------|
| `scraper/app/main.py` | FastAPI app, rota `POST /scrape/consultar-oab`, rota `GET /health` |
| `scraper/app/config.py` | Settings: BD_HOST, BD_USERNAME, BD_PASSWORD, S3_*, NAVIGATION_TIMEOUT |
| `scraper/app/schemas.py` | `ConsultarOABRequest`, `ProcessoResumo`, `DocumentoAnexo`, `ConsultarOABResponse` |
| `scraper/app/s3_client.py` | Upload de PDFs via boto3 com endpoint customizado (`objstoreapi.witdev.com.br`) |
| `scraper/app/scrapers/base.py` | `BaseScraper`: Playwright + Bright Data proxy + playwright-stealth |
| `scraper/app/scrapers/trf1.py` | Scraper completo TRF1 (ver seção 2) |
| `scraper/pyproject.toml` | Dependências: playwright==1.58.0, playwright-stealth, boto3, setuptools<71 |
| `scraper/poetry.lock` | Lock file gerado |

#### Docker

| Arquivo | Descrição |
|---------|-----------|
| `docker/scraper/Dockerfile` | Dev: `playwright:v1.58.0-noble` + Poetry + hot-reload |
| `docker/scraper/Dockerfile.prod` | Prod: multi-stage build, mesma imagem base |
| `docker-compose.yml` | Serviço `scraper` com limite de recursos, healthcheck, rede interna |
| `docker-compose.prod.yaml` | Serviço `scraper` para Swarm com Traefik |

#### Backend (modificado)

| Arquivo | Mudança |
|---------|---------|
| `backend/app/core/services/oab_finder_service.py` | Substituído: era scraper Playwright inline (306 linhas), agora é cliente HTTP simples (~30 linhas) que chama `http://scraper:8001/scrape/consultar-oab` |
| `backend/app/schemas/processo.py` | Adicionado `OABDocumentoAnexo` e campos `partes_detalhadas`, `movimentacoes`, `documentos` em `OABProcessoResumo` |
| `docker/backend/Dockerfile` | Removido `playwright install chromium` |
| `backend/pyproject.toml` | Removido `playwright = "^1.49.0"` |
| `build.sh` | Adicionado `IMAGE_SCRAPER`, `--scraper-only`, lógica de build/push/deploy do scraper |

---

## 2. Scraper TRF1 — Implementação Atual

Baseado no **relatório de análise** `docs/webscraping-pje1g-trf1-relatorio.md` que documentou o sistema PJe1g TRF1 (JBoss Seam + RichFaces/JSF).

### 2.1 Fluxo implementado em `scraper/app/scrapers/trf1.py`

```
1. GET listView.seam          → carregar formulário
2. Preencher fPP:Decoration:numeroOAB + fPP:Decoration:estadoComboOAB (via JS/Select2)
3. Clicar fPP:searchProcessos → resultado AJAX (A4J.AJAX.Submit)
4. Para cada processo:
   a. Clicar "Ver detalhes" → nova aba (DetalheProcessoConsultaPublica)
   b. Extrair: partes (polo ativo/passivo), movimentações (paginadas, 15/pág)
   c. Para cada documento:
      - Clicar "Visualizar documentos" → nova aba viewer HTML
      - Extrair idProcessoDoc + ca da URL
      - Clicar "Gerar PDF" → expect_download()
      - Upload PDF → S3 (key: processos/{numero}/documentos/{id}.pdf)
      - Retornar s3_url no response
```

### 2.2 IDs JSF identificados (estáveis entre sessões)

| Campo | ID/Name | Observação |
|-------|---------|-----------|
| OAB número | `fPP:Decoration:numeroOAB` | Fixo |
| OAB UF select | `fPP:Decoration:estadoComboOAB` | Fixo; valores são índices (CE=5) |
| Botão pesquisar | `fPP:searchProcessos` | Fixo; type=button, aciona A4J.AJAX |
| Form PDF | `j_id43` | Fixo entre sessões |
| Botão Gerar PDF | `j_id43:downloadPDF` | Fixo entre sessões |
| ViewState | `javax.faces.ViewState` | **Muda por sessão** — sempre ler do DOM |
| Token `ca` do processo | em URL do detalhe | Fixo por processo (hash determinístico) |
| Token `ca` do documento | em URL do viewer | **Muda por sessão** — capturar da URL da nova aba |

---

## 3. Problemas Resolvidos

### 3.1 playwright-stealth quebrava A4J (RESOLVIDO)

O `playwright-stealth` injetava um JSON polyfill que impedia o RichFaces A4J de inicializar.
**Fix:** Removido `stealth_async()` de `base.py`. O site é consulta pública sem anti-bot.

### 3.2 onclick do botão bloqueava A4J.AJAX.Submit (RESOLVIDO)

O `onclick` do botão faz `return executarReCaptcha();;A4J.AJAX.Submit(...)` — o `return`
sai antes do A4J executar. **Fix:** Chamar `executarPesquisa()` via JS diretamente.

### 3.3 CSS selector com `:` nos IDs JSF (RESOLVIDO)

`#fPP:Decoration:estadoComboOAB` falhava porque `:` é interpretado como pseudo-class CSS.
**Fix:** Usar `[id='fPP:Decoration:estadoComboOAB']` (attribute selector).

### 3.4 wait_for_selector com rows invisíveis (RESOLVIDO)

`wait_for_selector("tbody tr")` esperava visibilidade, mas rows da tabela podem estar hidden.
**Fix:** Usar `state="attached"` em vez do default `state="visible"`.

---

## 4. Próximos Passos

### 4.1 Integrar com endpoint backend

Testar o fluxo E2E via API:
```bash
POST /api/v1/processos/consultar-oab
{"oab_numero": "50784", "oab_uf": "CE", "tribunal": "trf1"}
```

### 4.2 Melhorar parsing de partes

Ainda há entradas espúrias como "Ativo" (status da parte) sendo parseadas como nomes.
Refinar a lógica em `_extract_parties()`.

### 4.3 Adicionar outros tribunais

Implementar scrapers para TJCE, TRF5-JFCE seguindo o mesmo padrão de `trf1.py`.

---

---

## 5. Configuração de Ambiente

### .env necessário

```env
# Bright Data proxy
BD_HOST=brd.superproxy.io:33335
BD_USERNAME=brd-customer-hl_1311c64c-zone-jusmonitoria
BD_PASSWORD=hm29tlz8nmbn

# S3 (MinIO compatível)
S3_ACCESS_KEY=witalo
S3_SECRET_KEY=g3IoVa0N51NjPGaMnbYsMhNdcrUX7UxUegOmCCre
S3_BUCKET=jusmonitoria
S3_ENDPOINT=objstoreapi.witdev.com.br
```

### Comandos

```bash
# Iniciar tudo
docker compose up -d

# Rebuildar scraper (após mudanças no Dockerfile/deps)
docker compose build scraper --no-cache && docker compose up -d scraper

# Ver logs do scraper em tempo real
docker compose logs -f scraper

# Testar health
curl http://localhost:8001/health   # direto no scraper (via docker exec)
docker compose exec scraper curl http://localhost:8001/health

# Rodar migrations (se necessário)
docker compose exec backend alembic upgrade head

# Criar super admin (se necessário)
docker compose exec backend python3 scripts/create_super_admin.py

# Testar E2E (script pronto)
docker compose exec backend python3 scripts/test_oab_scraper.py
```

---

## 6. Estrutura de Arquivos do Scraper

```
scraper/
├── app/
│   ├── main.py              # FastAPI app, rotas
│   ├── config.py            # Settings (BD, S3, timeouts)
│   ├── schemas.py           # Pydantic models
│   ├── s3_client.py         # Upload S3 via boto3
│   └── scrapers/
│       ├── base.py          # BaseScraper: Playwright + proxy + stealth
│       └── trf1.py          # TRF1 scraper (PROBLEMA: A4J submit)
├── pyproject.toml           # playwright==1.58.0, setuptools<71, boto3
└── poetry.lock

docker/scraper/
├── Dockerfile               # Dev (hot-reload)
└── Dockerfile.prod          # Prod (multi-stage)
```

---

## 7. Dados Esperados para OAB 50784/CE (TRF1)

7 processos encontrados (confirmado visualmente no browser):

| Número CNJ | Assunto | Última Movimentação |
|-----------|---------|---------------------|
| 1013264-53.2025.4.01.3904 | Exame da Ordem OAB | Conclusos p/ julgamento (24/02/2026) |
| 1014980-12.2025.4.01.4100 | Anulação e Correção de Provas | Conclusos p/ julgamento (11/02/2026) |
| 1089764-32.2025.4.01.3300 | Anulação e Correção de Provas | Decorrido prazo (23/01/2026) |
| 1098298-53.2025.4.01.3400 | Exame da Ordem OAB | Juntada de apelação (13/02/2026) |
| 1000511-48.2026.4.01.3704 | Anulação e Correção de Provas | Cancelada a Distribuição (02/02/2026) |
| 1000589-45.2026.4.01.3315 | Anulação e Correção de Provas | Juntada de petição intercorrente (23/02/2026) |
| 1000654-37.2026.4.01.3704 | Anulação e Correção de Provas | Conclusos para decisão (02/02/2026) |

Processo 1013264-53.2025.4.01.3904 tem **2 documentos**:
- Ato ordinatório (`idProcessoDoc=2238908250`)
- Despacho

---

## 8. Referências

- `docs/webscraping-pje1g-trf1-relatorio.md` — Relatório completo de análise do PJe1g TRF1 (IDs JSF, endpoints, parâmetros POST, estratégia de download)
- `backend/app/core/services/oab_finder_service.py` — Cliente HTTP que chama o scraper
- `backend/app/api/v1/endpoints/processos.py` — Endpoint `/processos/consultar-oab`
- `backend/scripts/test_oab_scraper.py` — Script de teste E2E
