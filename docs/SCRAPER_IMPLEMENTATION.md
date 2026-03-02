# JusMonitorIA — Scraper Service: Implementação e Próximos Passos

> **Data:** 02/03/2026
> **Status:** Implementado ✅ | Teste E2E pendente ⏳

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

## 3. Problema Atual: A4J não carrega no Playwright headless

### 3.1 Root cause

O botão de pesquisa do TRF1 usa `A4J.AJAX.Submit()` (biblioteca RichFaces). No navegador real, o script `A4J.js` é carregado normalmente. No Playwright headless, **o script A4J não está sendo inicializado** (`A4J is not defined`), então o clique no botão não dispara o POST AJAX.

Cadeia de chamadas:
```
onclick: return executarReCaptcha()
              ↓
         executarPesquisa()     ← captcha desabilitado (if false {...})
              ↓
         A4J.AJAX.Submit('fPP', ...)  ← FALHA: A4J undefined
```

### 3.2 O que foi testado

| Abordagem | Resultado |
|-----------|-----------|
| `select_option(label=uf)` | Falha: Select2 não usa select nativo da mesma forma |
| `wait_until="domcontentloaded"` | Página carrega mas A4J não inicializa |
| `wait_until="load"` | A4J ainda undefined após 15s |
| Chamar `executarPesquisa()` via `page.evaluate()` | `ReferenceError: A4J is not defined` |
| Override `executarReCaptcha` para retornar `true` | Não resolve (problema é A4J, não captcha) |
| Form submit nativo (`form.submit()`) | A testar (ver seção 4) |

### 3.3 O que funciona

- ✅ Chromium lança corretamente
- ✅ Página carrega (título "Consulta pública · Justiça Federal da 1ª Região")
- ✅ Elementos do formulário existem e são preenchíveis
- ✅ UF é setada corretamente via JS (`estadoComboOAB.value = '5'`)
- ✅ Proxy Bright Data funciona (curl retorna 200)
- ✅ S3 client configurado corretamente (credenciais em .env)
- ✅ Download de PDFs via `expect_download()` implementado
- ✅ Upload S3 implementado

---

## 4. Próximos Passos (E2E)

### 4.1 Solução recomendada: POST direto sem A4J

O relatório `docs/webscraping-pje1g-trf1-relatorio.md` (seção 3.1) documenta os parâmetros exatos do POST de pesquisa:

```
POST /consultapublica/ConsultaPublica/listView.seam
Content-Type: application/x-www-form-urlencoded

fPP:Decoration:numeroOAB       = 50784
fPP:Decoration:letraOAB        = (vazio)
fPP:Decoration:estadoComboOAB  = CE
fPP:pesquisar                  = fPP:pesquisar
javax.faces.ViewState          = {ViewState obtido no GET inicial}
```

**Implementação sugerida** em `trf1.py` para substituir o click no botão:

```python
# 1. GET inicial para obter ViewState e cookies
await page.goto(TRF1_URL, wait_until="domcontentloaded", timeout=90_000)
await asyncio.sleep(2)

view_state = await page.evaluate(
    "() => document.querySelector('input[name=\"javax.faces.ViewState\"]')?.value"
)

# 2. POST direto (bypass A4J)
response = await page.context.request.post(
    TRF1_URL,
    headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": TRF1_URL,
    },
    data=(
        f"fPP%3ADecoration%3AnumeroOAB={oab_numero}"
        f"&fPP%3ADecoration%3AletraOAB="
        f"&fPP%3ADecoration%3AestadoComboOAB={oab_uf}"
        f"&fPP%3Apesquisar=fPP%3Apesquisar"
        f"&javax.faces.ViewState={urllib.parse.quote(view_state)}"
    ),
)

# 3. Parse o HTML retornado
html_content = await response.text()
await page.set_content(html_content)
```

### 4.2 Alternativa: form.submit() via JS

```python
# Adicionar o campo de submit ao form e enviar nativamente
await page.evaluate('''([vs]) => {
    const form = document.getElementById("fPP");

    // Setar valores
    document.getElementById("fPP:Decoration:numeroOAB").value = "50784";
    const sel = document.getElementById("fPP:Decoration:estadoComboOAB");
    for (const o of sel.options) { if (o.text === "CE") { sel.value = o.value; break; } }

    // Adicionar campo que o server espera
    const inp = document.createElement("input");
    inp.type = "hidden"; inp.name = "fPP:pesquisar"; inp.value = "fPP:pesquisar";
    form.appendChild(inp);

    form.submit();
}''', [view_state])

await page.wait_for_load_state("domcontentloaded", timeout=30_000)
```

### 4.3 Passos para completar o E2E

1. **Corrigir o submit da pesquisa** (POST direto ou form.submit) — ver 4.1/4.2
2. **Verificar que 7 processos aparecem** para OAB 50784/CE
3. **Clicar "Ver detalhes"** do primeiro processo — verificar que nova aba abre
4. **Verificar extração de partes/movimentações** — log dos dados
5. **Clicar "Visualizar documentos"** — verificar nova aba com viewer HTML
6. **Baixar PDF via "Gerar PDF"** — verificar bytes > 0
7. **Verificar upload S3** — checar URL `https://objstoreapi.witdev.com.br/jusmonitoria/processos/{numero}/documentos/`
8. **Rodar via API** — `POST /api/v1/processos/consultar-oab` com OAB 50784/CE

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
