# Peticionamento PJe Multi-Tribunal — Status da Implementação

**Última atualização:** 04/03/2026  
**Responsável:** JAVIS  
**Objetivo:** Automatizar peticionamento avulso no PJe via Playwright (RPA)  
**Tribunais suportados:** TRF1, TRF3, TRF5, TRF6, TJCE

---

## Correções Aplicadas (04/03/2026) — 3 Bugs Críticos

### Bug 1: Upload PDF — `set_input_files()` não funciona com Dropzone.js
**Sintoma:** `hasTable: False` — documento nunca aparecia na petição.  
**Causa:** O botão `commandLinkAdicionar` abre um file picker nativo via Dropzone.js. O código antigo fazia `set_input_files()` em inputs hidden (ineficaz) e depois `click()` no botão (que abria o picker sem arquivo).  
**Fix:** Usar `page.expect_file_chooser()` + `commandLinkAdicionar.click()` → Dropzone recebe o PDF corretamente.  
**Arquivo:** `scraper/app/scrapers/pje_peticionamento.py` — `_upload_pdf()`

### Bug 2: Endpoint de assinatura — HTTP 405
**Sintoma:** POST para `/pjeoffice-rest` retornava 405, modal "PJeOffice Indisponível".  
**Causa:** `endpoint = servidor + enviarPara` resolvia para `https://pje1g.trf1.jus.br/pje/pjeoffice-rest` (405). O endpoint correto é `https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest` (204 no login).  
**Fix:** Sempre usar SSO Keycloak: `sso_endpoint = "https://sso.cloud.pje.jus.br/auth/realms/pje" + enviar_para`.  
**Arquivo:** `scraper/app/scrapers/pje_peticionamento.py` — `_handle_pjeoffice_route()`

### Bug 3: `btn-assinador` disabled ("Aguardando classificação dos documentos")
**Sintoma:** Após upload, botão de assinar permanecia desabilitado.  
**Causa:** A4J callback de classificação do documento não completava antes do click. Código não esperava a habilitação.  
**Fix:** Polling de 30s aguardando `btn-assinador` ser habilitado. Fallback: `atualizaApplet(true)` via JS.  
**Arquivo:** `scraper/app/scrapers/pje_peticionamento.py` — `_adicionar_documento()`

### Validação via Debug Script
O script `scraper/scripts/debug_peticao_avulsa.py` confirmou todas as hipóteses:
- **H1 CONFIRMADA:** `FILE CHOOSER DISPAROU!` ao clicar `commandLinkAdicionar`
- **H2 CONFIRMADA:** PJe → HTTP 405, SSO → endpoint correto
- **btn-assinador:** Disabled com texto "Aguardando a classificação dos documentos"

---

## Resultado do Teste E2E (04/03/2026) — Processo JOSE IRAN

**Processo:** `1014980-12.2025.4.01.4100` — TRF1 1° Grau  
**Resultado:** ✅ Quase-sucesso — 7/8 steps completados

| Step | Status | Detalhe |
|------|--------|---------|
| Login via cert A1 + MD5withRSA + PKIPath | ✅ | HTTP 204 |
| TOTP 2FA | ✅ | Redirect → TRF1 |
| Busca do processo | ✅ | idProcesso=13192719 |
| Captura popup URL | ✅ | peticaoPopUp.seam?idProcesso=13192719&ca=... |
| Abertura formulário | ✅ | cbTDDecoration:cbTD present |
| Tipo "Outras peças" selecionado | ✅ | (fallback — "peticao_principal" não existe na lista PJe) |
| PDF enviado | ✅ | `pje_doc_2v7fzmg6.pdf` apareceu na tabela |
| Assinatura | ❌ | Modal "PJeOffice Indisponível" — fix implementado |
| Protocolo | ❌ | Não obtido (bloqueado pela assinatura) |

**Root cause da falha de assinatura:**  
O PJe JS faz um `GET http://localhost:8800/pjeOffice/requisicao/?r={challenge}`. O scraper tentava interceptar via JS (`page.evaluate()`), mas o browser já havia enviado o request antes. A solução correta é `page.route()` — intercepta em nível de rede antes do request sair.

---

---

## Fluxo Real Descoberto (validado manualmente)

### TRF1 / TRF3 / TRF5 / TRF6 — Painel do Advogado

```
painel advogado (/pje/painel_usuario/advogado.seam)
  → Aba "PETICIONAR"
  → /pje/Processo/CadastroPeticaoAvulsa/peticaoavulsa.seam
  → Preencher número do processo (7 campos separados)
  → Clicar "Pesquisar"
  → Resultado aparece → clicar botão PETICIONAR (link id="idPet")
  → A4J/AJAX chama openPopUp('Peticionamento', url)
  → Navegar para peticaoPopUp.seam?idProcesso=XXX&ca=HASH
  → Formulário: Tipo de documento + Descrição + [Arquivo PDF / Editor de texto]
  → Selecionar "Arquivo PDF" → abre file picker
  → Escolher PDF → clicar ADICIONAR (commandLinkAdicionar)
  → Documento aparece na tabela de documentos
  → Clicar "ASSINAR DOCUMENTO(S)" (btn-assinador)
  → PJeOffice assina → protocolo gerado
```

### TJCE / TJs Estaduais — Quadro de Avisos

Após login+TOTP, o TJCE redireciona para:
```
https://pje.tjce.jus.br/pje1grau/QuadroAviso/listViewQuadroAvisoMensagem.seam
```
Esta página mostra: "Quadro de avisos", "Último Acesso Em", "Painel", "Processo", etc.  
**Não contém** keywords como `expedientes`, `peticionar` (padrão TRF1).  
A detecção de login é feita via URL (`startswith(base_url)`) — não por keywords.

Fluxo após login:
```
https://pje.tjce.jus.br/pje1grau/QuadroAviso/... (landing pós-TOTP)
  → /pje1grau/Processo/CadastroPeticaoAvulsa/peticaoavulsa.seam
  → (mesmo fluxo do TRF1 a partir daqui)
```

---

> **Observação importante do usuário:** quando clica em ADICIONAR, **abre uma janela de selecionar arquivo** (file picker nativo — não é upload automático via Dropzone). O correto é interceptar o `filechooser` event do Playwright.

---

## Campos do Formulário (IDs reais — validados)

| Campo | Elemento | ID |
|-------|----------|----|
| Número sequencial | input | `fPP:numeroProcesso:numeroSequencial` |
| Dígito verificador | input | `fPP:numeroProcesso:numeroDigitoVerificador` |
| Ano | input | `fPP:numeroProcesso:Ano` |
| Ramo da justiça | input | `fPP:numeroProcesso:ramoJustica` |
| Tribunal | input | `fPP:numeroProcesso:respectivoTribunal` |
| Órgão | input | `fPP:numeroProcesso:NumeroOrgaoJustica` |
| Botão pesquisar | button | `fPP:searchProcessosPeticao` |
| Link PETICIONAR | a | `*idPet*` |
| Tipo de documento | select | `cbTDDecoration:cbTD` (82 opções) |
| Descrição | input | `ipDescDecoration:ipDesc` |
| Modo Arquivo PDF | radio | `raTipoDocPrincipal:0` |
| Modo Editor HTML | radio | `raTipoDocPrincipal:1` |
| Adicionar arquivo | a | `commandLinkAdicionar` → **abre file picker** |
| Botão assinar | button | `btn-assinador` |

---

## Opções de Tipo de Documento (select cbTDDecoration:cbTD)

82 opções disponíveis. Mais usadas para petição avulsa:

| Valor | Texto |
|-------|-------|
| 0 | *(vazio — selecione)* |
| — | Aditamento à inicial |
| — | Alegações/Razões Finais |
| — | Apelação |
| — | Contestação |
| — | Inicial |
| — | Manifestação |
| **62** | **Petição intercorrente** ← recomendado para petição avulsa |
| 49 | Outras peças |
| 64 | Procuração |
| 80 | Substabelecimento |

---

## Arquitetura do Código

```
scraper/app/scrapers/pje_peticionamento.py   ← SCRAPER PRINCIPAL
scraper/app/main.py                           ← Endpoint POST /scrape/protocolar-peticao
backend/app/core/services/scraper_client.py   ← Cliente HTTP (backend → scraper)
backend/app/workers/tasks/peticao_protocolar.py ← Worker Taskiq (orquestra MNI + Playwright)
```

## URLs por Tribunal (PJE_BASE_URLS)

| Código | Base URL | Landing pós-login |
|--------|----------|-------------------|
| `trf1` | `https://pje1g.trf1.jus.br/pje` | `/pje/Painel/painel_usuario/advogado.seam` |
| `trf3` | `https://pje1g.trf3.jus.br/pje` | `/pje/Painel/painel_usuario/advogado.seam` |
| `trf5` | `https://pje.jfce.jus.br/pje` | `/pje/Painel/painel_usuario/advogado.seam` |
| `trf6` | `https://pje1g.trf6.jus.br/pje` | `/pje/Painel/painel_usuario/advogado.seam` |
| `tjce` | `https://pje.tjce.jus.br/pje1grau` | `/pje1grau/QuadroAviso/listViewQuadroAvisoMensagem.seam` |

---

## O que foi implementado e funciona ✅

### Upload do PDF (✅ CORRIGIDO — 04/03/2026)
- `page.expect_file_chooser()` ao clicar `commandLinkAdicionar` — captura o file picker nativo do SO/browser
- `file_chooser.set_files(pdf_path)` + `asyncio.sleep(5)` aguarda upload PJe
- Confirmado pelo log: `pje_doc_2v7fzmg6.pdf` apareceu na tabela de documentos no teste JOSE IRAN

### Assinatura via page.route() (✅ IMPLEMENTADO — 04/03/2026)
**Fix do "PJeOffice Indisponível" modal:**
- Substituiu intercept JS por `page.route("http://localhost:8800/**", _handle_pjeoffice_route)`
- Handler extrai challenge JSON do query param `r`, assina com `_sign_md5_rsa(private_key, mensagem)` em Python, envia POST para `sso.cloud.pje.jus.br/pjeoffice-rest`, devolve `route.fulfill(status=200, body="ok")` ao PJe
- Loop de retry (3x): fecha modal "PJeOffice Indisponível" se aparecer e re-clica assinar
- **Não requer PJeOffice instalado** — o intercept funciona em headless Chromium sem daemon local

```python
async def _handle_pjeoffice_route(route, request):
    r_data = json.loads(unquote(params["r"][0]))
    mensagem = json.loads(r_data["tarefa"])["mensagem"]
    assinatura = _sign_md5_rsa(private_key, mensagem)
    await page.context.request.post(endpoint, data=sign_payload, ...)
    await route.fulfill(status=200, body="ok", ...)
```

### Login + TOTP (100% funcional)
- Login via certificado A1 (.pfx) usando PJeOffice SSO (MD5withRSA + PKIPath DER)
- TOTP 2FA com secret `MNFTCT2WKBJFKU3NGN2GYNKUJVDVKM3X` (sha1, 6 digits, 30s)
- Submit TOTP via `evaluate("el => el.click()")` — evita bug do Playwright com JSF
- `wait_for_url` cobre todos os tribunais: `^https?://pje1g\.trf|^https?://pje\.jf|^https?://pje\.tj`
- Detecção de login por **URL** (`startswith(base_url)`) — robusto para qualquer landing page (TJCE cai em `/QuadroAviso/`, TRFs no painel do advogado)
- Detecção por keywords como fallback: `expedientes`, `peticionar`, `quadro de avisos`, `último acesso em`

### Busca do Processo (100% funcional)
- Navega para `peticaoavulsa.seam`
- Preenche 6 campos do número do processo via JS `dispatchEvent(change)`
- Clica `fPP:searchProcessosPeticao`
- Detecta "resultados encontrados" no body

### Captura do Popup URL (100% funcional)
- Override de `window.openPopUp()` ANTES de clicar `idPet`
- Captura a URL completa montada pelo A4J: `peticaoPopUp.seam?idProcesso=XXX&ca=HASH`

### Abertura do Formulário (100% funcional)
- Navega para `peticaoPopUp.seam`
- Fecha modal "PJeOffice indisponível" se aparecer
- Confirma presença de `cbTDDecoration:cbTD`

### Seleção Tipo de Documento (100% funcional)
- `select_option(label=tipo)` via Playwright nativo → dispara A4J server-side
- Fallback: match parcial → Petição intercorrente / Outras peças

### Preenchimento de Descrição (100% funcional)
- `locator.fill()` via Playwright nativo

### Seleção "Arquivo PDF" (100% funcional)
- Radio `raTipoDocPrincipal:0` via Playwright `locator.click()`
- Aguarda A4J atualizar o formulário (3s)

---

## O que FALTA implementar / validar ⚠️

### Assinatura — Pendente validação em produção
O fix `page.route()` foi implementado mas **ainda não validado** com um processo real (teste E2E completo):
- Correr o teste `1014980-12.2025.4.01.4100` com Docker rebuild
- Verificar que não aparece mais modal "PJeOffice Indisponível"
- Capturar número de protocolo

### Robustez Multi-Tribunal
- TRF3, TRF5, TRF6 e TJCE têm os mesmos IDs de formulário — devem funcionar sem alteração
- TJSP e outros TJs estaduais: não testados

---

## Banco de Dados + Backend API (implementado — 04/03/2026)

### Novas colunas na tabela `peticoes`
```sql
tipo_documento_pje  VARCHAR(200)   -- Label exato do select PJe (ex: "Petição intercorrente")
descricao_pje       VARCHAR(500)   -- Descrição livre para o PJe
```
Migration: `43d36e5bd5b0_add_tipo_documento_pje_descricao_pje` (aplicada)

### Novo endpoint
```
GET /api/v1/peticoes/tipos-documento?tribunal_id=TRF1-1G
```
Retorna os 82 tipos de documento do TRF1 (ou lista genérica para outros tribunais).  
Arquivo de dados: `backend/app/data/tipos_documento_pje.py`

### Worker atualizado
`peticao_protocolar.py` agora:
- Usa `pet.tipo_documento_pje` (label PJe exato) se preenchido, caso contrário usa enum interno
- Usa `pet.descricao_pje` se preenchido, caso contrário usa `pet.assunto`

---

## Frontend (implementado — 04/03/2026)

### Novos campos no formulário de petição
- **Select "Tipo PJe"**: carrega 82 tipos do endpoint `/peticoes/tipos-documento?tribunal_id=...`; ativado apenas quando tribunal selecionado; stale time 1h (sem requests repetidos)
- **Input "Descrição PJe"**: opcional; descrição que aparecerá no documento PJe

### Tipos afetados
- `frontend/types/peticoes.ts` → `tipoPeticaoPje?: string`, `descricaoPje?: string`
- `frontend/hooks/api/usePeticoes.ts` → `useTiposDocumentoPje(tribunalId)` hook
- `frontend/components/peticoes/PeticaoFormDadosProcesso.tsx` → Select + Input no form
- `frontend/components/peticoes/PeticaoForm.tsx` → pre-fill do rascunho

---

## Bugs Corrigidos Nesta Sessão

| Bug | Causa | Correção |
|-----|-------|----------|
| `wait_for_url` prematuro (TRF1) | regex `pje1g\.trf` matcha `redirect_uri` na URL do SSO | Regex com âncora + multi-tribunal: `^https?://pje1g\.trf\|^https?://pje\.jf\|^https?://pje\.tj` |
| TOTP não submetido | `submit_btn.click()` travava aguardando navegação JSF | Trocado por `evaluate("el => el.click()")` |
| Challenge SSO não encontrado | Script errava antes de extrair nonce do botão | Seletor correto: `kc-pje-office` |
| Certchain vazia (HTTP 500) | Parse manual de PEM não incluía chain | Usa `_get_certchain_b64()` do módulo |
| Popup URL corrompida | A4J monta URL em 3 partes via concatenação JS | Override `window.openPopUp()` antes do click |
| Tipo de documento errado | Match parcial "Petição" pegava item errado | Melhorado: match exato → parcial → fallback |
| `is_logged_in` falso negativo (todos tribunais) | Só checava keywords TRF1 — TJCE (e potencialmente outros TJs) caem em `/QuadroAviso/` sem `expedientes`/`peticionar` | Detecção primária via `current_url.startswith(base_url)` (OR) keywords ampliadas — qualquer tribunal coberto |

---

## Inferência Automática de Tribunal

O campo `tribunal` no request passou a ser **opcional**. Se omitido, é inferido automaticamente do número CNJ do processo via `tribunal_from_processo()`.

Formato CNJ: `NNNNNNN-DD.AAAA.**J**.**TT**.OOOO`

| J | TT | Tribunal |
|---|----|---------|
| 4 | 01 | trf1 |
| 4 | 03 | trf3 |
| 4 | 05 | trf5 |
| 4 | 06 | trf6 |
| 8 | 06 | tjce |
| 8 | 25 | tjsp |
| 8 | 19 | tjrj |
| … | … | … |

Exemplo: `1014980-12.2025.4.01.4100` → J=4, TT=01 → **trf1** (automático)

---

## Próximos Passos

1. **Docker rebuild** — `docker compose build scraper worker frontend && docker compose up -d`
2. **Validar assinatura** — correr teste E2E com processo `1014980-12.2025.4.01.4100`:
   ```bash
   curl -X POST http://localhost:8000/api/v1/peticoes/<id>/protocolar
   ```
3. **Capturar protocolo** — número de protocolo deve aparecer no response + log do worker
4. **PDF de teste**: `docs/chamamento JOSE IRAN DE FIGUEIREDO.pdf`
5. **Testar outros tribunais** — TRF3, TRF5, TRF6, TJCE (mesmos form IDs — devem funcionar)

---

## Scripts de Exploração Criados

```
scraper/scripts/login_and_export.py       — login inicial (descartado)
scraper/scripts/explore_pje.py            — mapeou painel do advogado
scraper/scripts/explore_peticionar.py     — testou busca de processo
scraper/scripts/explore_a4j_debug.py      — descobriu openPopUp()
scraper/scripts/explore_juntar_docs.py    — mapeou formulário completo ← MAIS IMPORTANTE
scraper/scripts/testar_peticionamento_v2.py — teste E2E atual
```

---

## Credenciais de Teste

| Campo | Valor |
|-------|-------|
| Advogada | Amanda Alves de Sousa |
| CPF | 07071649316 |
| PFX | `/app/docs/Amanda Alves de Sousa_07071649316.pfx` |
| Senha PFX | `22051998` |
| TOTP secret | `MNFTCT2WKBJFKU3NGN2GYNKUJVDVKM3X` |
| Processo teste | `1014980-12.2025.4.01.4100` |
| Tribunal | TRF1 1° Grau |
