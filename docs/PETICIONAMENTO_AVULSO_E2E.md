# Peticionamento Avulso PJe — Documentação Técnica E2E

> Documento técnico completo sobre como o JusMonitor emula o PJeOffice para
> assinar e protocolar petições avulsas no PJe TRF1 sem o software instalado.
> Inclui todas as descobertas de depuração da sessão de 04/03/2026.

---

## Índice

1. [Contexto e Problema](#1-contexto-e-problema)
2. [Como o PJe Realmente Funciona](#2-como-o-pje-realmente-funciona)
3. [Por que as Abordagens Triviais Falham](#3-por-que-as-abordagens-triviais-falham)
4. [Solução: JS Monkey-Patching](#4-solução-js-monkey-patching)
5. [Fluxo Completo de Execução](#5-fluxo-completo-de-execução)
6. [Bugs Críticos Encontrados e Corrigidos](#6-bugs-críticos-encontrados-e-corrigidos)
7. [Estrutura do Payload de Assinatura](#7-estrutura-do-payload-de-assinatura)
8. [Código de Referência](#8-código-de-referência)
9. [Diagnóstico e Logs](#9-diagnóstico-e-logs)
10. [Limitações Conhecidas](#10-limitações-conhecidas)
11. [Estado Atual e Descobertas (04/03/2026)](#11-estado-atual-e-descobertas-04032026)
12. [Próximos Passos](#12-próximos-passos)

---

## 1. Contexto e Problema

O PJe (Processo Judicial Eletrônico) exige **assinatura digital com certificado ICP-Brasil** para protocolar petições. Na interface web, o PJe delega essa assinatura ao **PJeOffice** — um software nativo (Java/WebSocket) que o advogado instala localmente.

No fluxo real do advogado:
1. O PJe abre um popup (`peticaoPopUp.seam`)
2. O advogado preenche o formulário e clica **"Assinar documento(s)"**
3. O PJe aciona o PJeOffice via `img.src = "http://localhost:8800/..."`
4. O PJeOffice (rodando na máquina do usuário) assina e responde
5. O PJe recebe `img.onload` e submete o formulário via A4J/RichFaces

**O JusMonitor precisa fazer tudo isso em headless**, sem o PJeOffice instalado, usando apenas o certificado PFX do cliente.

---

## 2. Como o PJe Realmente Funciona

### 2.1 Protocolo de Comunicação PJeOffice

O PJe se comunica com o PJeOffice através de uma `<img>` tag cujo `src` aponta para `http://localhost:8800`. Este é um padrão antigo de cross-origin communication via imagem (pré-CORS).

```
PJe JS:
  const img = new Image();
  img.onload = () => { /* assinou com sucesso → submeter formulário */ };
  img.onerror = () => { /* PJeOffice indisponível → mostrar modal */ };
  img.src = "http://localhost:8800/pjeOffice/requisicao/?r=<JSON_ENCODED>";
```

### 2.2 Função `img.onload` Decodificada (Descoberta 04/03/2026)

```javascript
function() {
    // Quando o PJeOffice retornar uma imagem com 2px de largura é pq houve algum erro
    if (this.width == 2) {
        onErro();
    }
    else {
        // Quando o PJeOffice retornar uma imagem com 1px de largura é pq houve sucesso
        onSucesso();
    }
}
```

**Pontos críticos:**
- Verifica `this.width` (não `naturalWidth`) — precisa definir `img.width = 1`
- `onSucesso()` e `onErro()` são **closures** definidas no escopo inline do A4J response
- `onSucesso()` chama `A4J.AJAX.Submit('j_id312', ...)` — formulário **diferente** de `formularioUpload`

### 2.3 O que `onSucesso()` Faz (Descoberta 04/03/2026)

Capturando via interceptação de `A4J.AJAX.Submit`:

```
onSucesso() dispara:
  1. A4J.AJAX.Submit('j_id312', event, {
       similarityGroupingId: 'j_id312:j_id313',
       parameters: { 'j_id312:j_id313': 'j_id312:j_id313' }
     })
     → POST peticaoPopUp.seam → HTTP 200 (50516 bytes)
     → oncomplete: hideMpProgresso()
     → Ajax-Update-Ids: "expDiv,grdBas,divArquivos,modalPanelMessagesOuter"

  2. A4J.AJAX.Submit('j_id312', ...) [mesma chamada, duplicada]

  3. A4J.AJAX.Submit('formularioUpload', event, {
       similarityGroupingId: 'j_id168',
       parameters: { 'j_id168': 'j_id168' }
     })
```

**O servidor responde re-renderizando o formulário** — sem mensagem de sucesso, sem número de protocolo. O `div_Messages` permanece vazio (`<dt></dt>`).

### 2.4 Endpoint de Assinatura no SSO

```
POST https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest
Content-Type: application/json

{
  "certChain": "<pkipath_base64>",
  "uuid": "<token_uuid>",
  "mensagem": "<dado_assinado>",
  "assinatura": "<rsa_md5_base64>"
}

→ HTTP 204 No Content (sucesso)
```

---

## 3. Por que as Abordagens Triviais Falham

### 3.1 `page.route()` — NÃO FUNCIONA para assinatura

O Playwright intercepta o request no nível de rede e responde com `route.fulfill()`, mas o Chromium headless NÃO dispara `img.onload` para imagens dinâmicas interceptadas assim.

### 3.2 Patchear `window.Image` constructor — NÃO FUNCIONA

O PJe JS já capturou a referência original antes de qualquer `page.evaluate()`.

---

## 4. Solução: JS Monkey-Patching

### 4.1 Princípio

Patcheamos **no nível do DOM/JS** — antes de qualquer tentativa de acesso à rede:

```
PJe JS:  img.src = "http://localhost:8800/..."
          ↓ (setter patcheado intercepta antes de chamar rede)
         _handlePjeUrl(img, url)
          ↓
         _callPjeSign(rParam)  ← chama Python via expose_function
          ↓
         Python: assina + POST SSO (HTTP 204)
          ↓
         JS: define img.width=1, dispara img.onload artificialmente
          ↓
         PJe JS: this.width != 2 → onSucesso()
          ↓
         onSucesso() → A4J.AJAX.Submit('j_id312', ...) → servidor
```

### 4.2 Camadas de Intercepção

1. **`HTMLImageElement.prototype.src` setter** — intercepta toda atribuição `img.src = "..."`
2. **`Element.prototype.setAttribute`** — intercepta `img.setAttribute('src', '...')`
3. **`XMLHttpRequest.prototype.send`** — intercepta tentativas via XHR
4. **`window.fetch`** — intercepta tentativas via fetch API
5. **`MutationObserver`** — captura imagens adicionadas ao DOM com src já definido
6. **`page.route()` safety net** — último recurso se algum request escapar

---

## 5. Fluxo Completo de Execução

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FLUXO PETIÇÃO AVULSA PJe                           │
└─────────────────────────────────────────────────────────────────────────────┘

1. LOGIN COM CERTIFICADO DIGITAL
   ├── GET https://pje1g.trf1.jus.br/pje/login.seam
   │     → redireciona para SSO Keycloak
   ├── Extrai nonce (challenge) do botão "CERTIFICADO DIGITAL" via onclick
   ├── Assina nonce com MD5withRSA usando chave privada do PFX
   ├── POST https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest
   │     {certChain, uuid, mensagem=nonce, assinatura}  → HTTP 204 ✓
   └── Submit form → SSO valida cert → redirect para painel PJe

2. AUTENTICAÇÃO TOTP
   ├── Detecta página de OTP (URL contém /authenticate?execution=...)
   ├── Gera código TOTP com pyotp (SHA1, 6 dígitos, 30s)
   └── Submit → redirect para /QuadroAviso/

3. NAVEGAÇÃO PARA PETIÇÃO AVULSA
   ├── GET peticaoavulsa.seam
   ├── Preenche CNJ do processo
   ├── Clica "Pesquisar" → aguarda A4J
   └── Clica link do processo → abre popup peticaoPopUp.seam

4. PREENCHIMENTO DO FORMULÁRIO (popup)
   ├── Seleciona tipo de documento
   ├── Preenche descrição
   └── Seleciona "Arquivo PDF"

5. UPLOAD DO PDF (RichFaces uploader)
   ├── Detecta input[type=file]
   ├── set_input_files() (NÃO click())
   └── Aguarda A4J confirmando upload

6. CLASSIFICAÇÃO DO DOCUMENTO
   └── btn-assinador habilitado (disabled=false)

7. ASSINATURA (NÚCLEO DA SOLUÇÃO)
   │
   ├── 7a. expose_function('__pjeSignDoc', handler)
   ├── 7b. page.evaluate() → injeta monkey-patches
   ├── 7c. page.route() safety net
   │
   ├── 7d. Clica btn-assinador
   │     → A4J.AJAX.Submit('formularioUpload', event, {similarityGroupingId: 'btn-assinador'})
   │     → POST peticaoPopUp.seam → resposta com script que cria img.src
   │
   ├── 7e. SETTER intercepta img.src → extrai param r → chama Python
   │     → Python assina com RSA+MD5 → POST SSO → HTTP 204
   │
   ├── 7f. JS define img.width=1 → img.onload.call(img, evt)
   │     → this.width != 2 → onSucesso()
   │
   └── 7g. onSucesso() → A4J.AJAX.Submit('j_id312', ...)    ← FORM DIFERENTE!
         → 2x POST peticaoPopUp.seam → HTTP 200 (50516 bytes cada)
         → oncomplete: hideMpProgresso()
         → Ajax-Update-Ids: "expDiv,grdBas,divArquivos,modalPanelMessagesOuter"
         → SERVIDOR RE-RENDERIZA O FORMULÁRIO (sem mensagem de sucesso)

8. ESTADO ATUAL: FORMULÁRIO RE-RENDERIZADO
   ├── Body permanece ~25276 chars (não muda significativamente)
   ├── div_Messages: vazio (<dt></dt>)
   ├── Único botão visível: btn-assinador
   ├── Loading overlay ("Por favor aguarde") persiste no DOM
   └── Petição NÃO aparece no PJe (verificado visualmente no site)
```

---

## 6. Bugs Críticos Encontrados e Corrigidos

### Bug 1: `Array.prototype.toJSON` (Prototype.js)

**Sintoma:** `serializedArgs is not an array`

**Causa:** Prototype.js redefine `Array.prototype.toJSON`, quebrando `JSON.stringify` do Playwright.

**Fix:**
```javascript
function _callPjeSign(rParam) {
    const _saved = Array.prototype.toJSON;
    try { delete Array.prototype.toJSON; } catch(e) {}
    const promise = window.__pjeSignDoc(rParam);
    try { if (_saved !== undefined) Array.prototype.toJSON = _saved; } catch(e) {}
    return promise;
}
```

### Bug 2: Loop de re-signing após modal

**Sintoma:** Modal "PJeOffice Indisponível" aparece após signing OK.

**Fix:** Não re-acionar btn-assinador se `_signed_challenges > 0`.

### Bug 3: `img.width` não definido (Descoberta 04/03/2026)

**Sintoma:** `img.onload()` é chamado mas `this.width` pode ser 0.

**Causa:** O PJe verifica `this.width == 2` (erro) vs `!= 2` (sucesso). Nós definíamos `naturalWidth = 1` mas não `width`.

**Fix:**
```javascript
Object.defineProperty(img, 'width', { value: 1, configurable: true });
Object.defineProperty(img, 'height', { value: 1, configurable: true });
```

**Nota:** Na prática `this.width == 0` (default) também vai para `onSucesso()` porque `0 != 2`. Mas definir explicitamente é mais correto.

### Bug 4: Falso positivo de sucesso (Descoberta 04/03/2026)

**Sintoma:** Scraper retornava `sucesso: true` mas petição NÃO aparecia no PJe.

**Causa:** O código detectava "sucesso" por fallback: assinatura SSO 204 + keywords na página. Mas o A4J re-renderizava o formulário sem confirmar envio.

**Fix:** Removido o fallback que declarava sucesso por `_sucesso_interim_attempt + _signed_challenges`. Agora só declara sucesso se:
- Popup navega para URL diferente, OU
- Keywords de sucesso aparecem SEM loading overlay

---

## 7. Estrutura do Payload de Assinatura

### 7.1 Parâmetro `r` da URL PJeOffice

```json
{
  "aplicacao": "PJe",
  "servidor": "https://pje1g.trf1.jus.br",
  "tarefaId": "cnj.assinadorHash",
  "tarefa": "{\"mensagem\":\"<HASH_BASE64>\",\"enviarPara\":\"/pjeoffice-rest\",\"token\":\"<UUID>\"}"
}
```

### 7.2 Payload enviado ao SSO

```json
POST https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest

{
  "certChain": "<base64 PKIPath>",
  "uuid": "<token>",
  "mensagem": "<hash>",
  "assinatura": "<RSA/MD5 base64>"
}
→ HTTP 204 No Content
```

### 7.3 Algoritmo de Assinatura

```
RSA + MD5 (MD5withRSA) com PKCS1v15 padding
```

---

## 8. Código de Referência

```
scraper/app/scrapers/pje_peticionamento.py
  └── async def _assinar_e_enviar(page, private_key, certchain_b64, tag)
       ├── _browser_sign_handler()      # Python: signing + POST SSO
       ├── page.expose_function()       # Bridge JS→Python
       ├── page.evaluate()              # Injeta todos os patches JS
       ├── page.route()                 # Safety net
       └── Loop de polling (60s)        # Aguarda resultado
```

---

## 9. Diagnóstico e Logs

### 9.1 Prefixos de log

| Prefixo | Descrição |
|---------|-----------|
| `[PJE-PROTOCOLO-TRF1]` | Orquestração geral |
| `[JS-SIGN]` | Python handler de assinatura |
| `[BROWSER-CONSOLE] [PJEPATCH]` | JS monkey-patch no browser |
| `[BROWSER-CONSOLE] [PJEPATCH-XHR]` | XHR debug interceptor (respostas A4J) |
| `[BROWSER-CONSOLE] [PJEPATCH-A4J]` | A4J.AJAX.Submit interceptor (chamadas) |
| `[RESPONSE]` | Respostas HTTP interceptadas via page.on('response') |
| `[XHR-RESPONSE N]` | Análise das respostas XHR salvas pós-loop |
| `[POST-SIGN-STATE]` | Inspeção dos divs após signing |
| `[ONLOAD-SOURCE]` | Source code da img.onload capturada |

### 9.2 Sequência de logs (estado atual 04/03/2026)

```
INFO  expose_function('__pjeSignDoc') OK
INFO  ✓ Monkey-patch JS injetado
INFO  btn-assinador clicado via JS
INFO  [RESPONSE] POST peticaoPopUp.seam → HTTP 200 (1st: btn-assinador response)
INFO  [RESPONSE] POST peticaoPopUp.seam → HTTP 200 (2nd: inline script executa)
INFO  [PJEPATCH] Intercepted img.src: http://localhost:8800/...
INFO  [PJEPATCH] Chamando __pjeSignDoc com rParam...
INFO  [JS-SIGN] POST https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest
INFO  [JS-SIGN] SSO: HTTP 204
INFO  [PJEPATCH] Sign result: OK:204
INFO  [PJEPATCH] ✓ XHR debug interceptor installed
INFO  [PJEPATCH] img.width= 1 this test: → onSucesso()
INFO  [PJEPATCH] Calling img.onload.call(img, evt)...
INFO  [PJEPATCH-A4J] Submit called: {formId: "j_id312", ...}    ← onSucesso() dispara!
INFO  [PJEPATCH-A4J] Submit called: {formId: "j_id312", ...}    ← duplicado
INFO  [PJEPATCH] img.onload() returned OK
INFO  [RESPONSE] POST peticaoPopUp.seam → HTTP 200 (3rd: resposta j_id312)
INFO  [RESPONSE] POST peticaoPopUp.seam → HTTP 200 (4th: resposta j_id312 dup)
INFO  [PJEPATCH-XHR] POST peticaoPopUp.seam status=200 len=50516
INFO  [XHR-RESPONSE 0] ONCOMPLETE: hideMpProgresso()
INFO  Assinatura OK mas A4J ainda processando (attempt=0, loading=True)
INFO  Loading persiste após 5s — forçando hideMpProgresso()...
INFO  [POST-SIGN-STATE] Messages: <dt></dt>                     ← VAZIO!
INFO  [POST-SIGN-STATE] buttons: [{"id": "btn-assinador"}]      ← Só btn-assinador
INFO  Aguardando... (attempt=55, challenges=1, loading=True)
WARNING  Assinatura SSO OK (1 challenges) mas A4J NÃO completou a submissão
WARNING  Resultado indefinido
```

---

## 10. Limitações Conhecidas

### 10.1 Certificado A1 apenas
Suporta apenas certificados A1 (arquivo PFX). A3 (smartcard/token USB) não compatível com headless.

### 10.2 TOTP obrigatório
O SSO do TRF1 exige 2FA via TOTP.

### 10.3 Compatibilidade apenas com TRF1
URL do SSO (`sso.cloud.pje.jus.br`) é específica do PJe TRF1.

---

## 11. Estado Atual e Descobertas (04/03/2026)

### 11.1 O que funciona ✅

| Etapa | Status |
|-------|--------|
| Login no PJe (certificado + TOTP) | ✅ |
| Abertura do popup peticaoPopUp.seam | ✅ |
| Upload do PDF via RichFaces | ✅ |
| Habilitação do btn-assinador | ✅ |
| Injeção do monkey-patch JS | ✅ |
| Interceptação do img.src para localhost:8800 | ✅ |
| Assinatura real via SSO (HTTP 204) | ✅ |
| Disparo de img.onload() com width=1 | ✅ |
| onSucesso() chamada com sucesso | ✅ |
| A4J.AJAX.Submit disparado por onSucesso | ✅ |
| Servidor responde HTTP 200 com XML | ✅ |

### 11.2 O problema em aberto 🔴

**O servidor aceita a assinatura (SSO 204) e responde ao A4J com HTTP 200, mas re-renderiza o formulário em vez de confirmar o envio da petição.**

Evidências detalhadas:

1. **img.onload funciona** — `this.width == 1`, entra em `onSucesso()`
2. **onSucesso() chama A4J.AJAX.Submit** com formulário `j_id312` (NÃO `formularioUpload`)
3. **O servidor responde** — HTTP 200, 50516 bytes, XML com `oncomplete: hideMpProgresso()`
4. **Ajax-Update-Ids:** `"expDiv,grdBas,divArquivos,modalPanelMessagesOuter"`
5. **O formulário é re-renderizado** — mesmos campos, tipo de documento, upload, etc.
6. **Messages div vazio** — `<dt></dt>`, sem erro nem sucesso
7. **Petição NÃO aparece no PJe** — verificado visualmente no site em 04/03/2026

### 11.3 Hipóteses para o problema

| # | Hipótese | Evidência |
|---|----------|-----------|
| 1 | **Formulário `j_id312` é o errado** | onSucesso() submete `j_id312`, não `formularioUpload`. Pode ser que o form correto deveria incluir dados adicionais do signing. |
| 2 | **O A4J Submit do onSucesso() não inclui dados de assinatura** | Os parameters são apenas `{j_id312:j_id313: j_id312:j_id313}` — sem token UUID, sem referência à assinatura. |
| 3 | **O `onSucesso()` é uma closure cujo escopo perdeu variáveis** | A closure pode depender de variáveis que foram garbage collected ou que tinham valores transientes durante o response processing original do A4J. |
| 4 | **A chamada duplicada ao A4J.AJAX.Submit** causa conflito | onSucesso() chama Submit 2 vezes com os mesmos parâmetros — a segunda pode invalidar a primeira. |
| 5 | **O servidor não reconhece o token de assinatura** | O SSO 204 aceita a assinatura, mas quando o formulário é submetido, o servidor pode não encontrar o token na sessão (timing, CSRF, etc.) |
| 6 | **Falta chamar função intermediária antes do Submit** | onSucesso() pode estar incompleta ou depender de um callback chain que não executou corretamente |

### 11.4 Dados técnicos das respostas A4J

**Response após onSucesso() (50516 bytes):**
- `<?xml version="1.0"?>` — XML válido
- Contém re-rendering completo de: expDiv, grdBas (tipos documento), divArquivos (upload form), modalPanelMessagesOuter
- `oncomplete: hideMpProgresso()` — esconde modal de progresso
- Messages div: vazio (sem erro, sem sucesso)
- Body length: ~25276 chars (não muda)

**Todos os A4J.AJAX.Submit interceptados pós-onSucesso:**
```json
[
  {"formId": "j_id312", "similarityGroupingId": "j_id312:j_id313", "parameters": {"j_id312:j_id313": "j_id312:j_id313"}},
  {"formId": "j_id312", "similarityGroupingId": "j_id312:j_id313", "parameters": {"j_id312:j_id313": "j_id312:j_id313"}},
  {"formId": "formularioUpload", "similarityGroupingId": "j_id168", "parameters": {"j_id168": "j_id168"}}
]
```

---

## 12. Próximos Passos

### Passo 1 — Capturar source completo de `onSucesso()` e `onErro()`

As closures `onSucesso`/`onErro` são definidas no inline script do A4J response (do btn-assinador). Precisamos:
1. Interceptar o A4J response XML que contém o script que define estas closures
2. Extrair o script completo para entender o fluxo
3. Verificar se há variáveis de closure (ex: `token`, `uuid`, `signedHash`) que deveriam estar populadas

### Passo 2 — Comparar com fluxo real do PJeOffice

Rodar o teste com `headless=False` e o PJeOffice real instalado para comparar:
1. Quais requests o PJeOffice real faz vs nosso scraper
2. Se o formulário `j_id312` é o correto
3. Se há hidden fields adicionais preenchidos

### Passo 3 — Interceptar o HTML completo do A4J response que define onSucesso

O btn-assinador A4J response contém inline `<script>` que define:
- `onSucesso()` — closure para sucesso
- `onErro()` — closure para erro
- Possivelmente variáveis de estado do signing

Precisamos capturar este script ANTES do img.src ser criado para entender o fluxo completo.

### Passo 4 — Verificar se o form `j_id312` precisa de dados adicionais

Inspecionar o form `j_id312` após o signing para ver se há hidden inputs que deveriam estar preenchidos com dados da assinatura (UUID, hash assinado, etc.).

### Passo 5 — Tentar submeter `formularioUpload` com dados de assinatura

Se o `j_id312` submit não funciona, tentar submeter `formularioUpload` diretamente com os campos corretos preenchidos após a assinatura SSO.

---

## Referências

- [RichFaces 3.x A4J AJAX](https://docs.jboss.org/richfaces/latest_3_3_X/)
- [Prototype.js Array.toJSON issue](http://prototypejs.org/api/array/)
- [PKIPath encoding RFC 2459](https://datatracker.ietf.org/doc/html/rfc2459)
- [Playwright expose_function](https://playwright.dev/python/docs/api/class-page#page-expose-function)
- Implementação: [scraper/app/scrapers/pje_peticionamento.py](../scraper/app/scrapers/pje_peticionamento.py)

---

## 13. Descobertas Sessão 04/03/2026 — Handler `cnj.assinadorHash` e Upload de Documento Assinado

### 13.1 Contexto

Sessão de debug intensivo do fluxo de assinatura de documentos no PJe TRF1.
O `_browser_sign_handler` intercepta requisições PJeOffice via monkey-patch de `HTMLImageElement.prototype.src` e roteia para dois ramos:
- **`cnj.assinadorHash`** — assinatura de documento + upload para PJe
- **`sso.autenticador`** — autenticação SSO (Keycloak) — implementado e funcional

O ramo `cnj.assinadorHash` estava implementado errado (assinar `mensagem` vazia e POSTar para SSO). Esta sessão corrigiu e depurou iterativamente.

---

### 13.2 Causa Raiz Confirmada

O handler anterior lía `tarefa.mensagem` (que é **vazia** para `cnj.assinadorHash`)  
e enviava para o endpoint SSO pjeoffice-rest — completamente errado.

Para `cnj.assinadorHash`, a tarefa contém:
```json
{
  "uploadUrl": "/arquivoAssinadoUpload.seam?action=peticionamentoAction&cid=302239&mo=P",
  "arquivos": [ { "id": "2241101138", "codIni": "100131276", "hash": "eeb510b8bbd9e663b0501dd47937b543", "isBin": "true" } ],
  "algoritmo": "MD5withRSA"
}
```

Não há `mensagem`. O fluxo correto é:
1. Extrair bytes do documento
2. Assinar com `RSA PKCS1v15 + MD5`
3. HTTP POST para `servidor + uploadUrl` com os dados de assinatura

---

### 13.3 Descoberta Crítica — TRF1 Não Envia `conteudoBase64`

TRF1 usa a API antiga do PJeOffice. Cada `arquivo` contém **apenas**:
```json
{ "id": "2241101138", "codIni": "100131276", "hash": "eeb510b8bbd9e663b0501dd47937b543", "isBin": "true" }
```

**Não há `conteudoBase64`** — o PDF não vem embedado na tarefa.

**Solução implementada:** comparar `hashlib.md5(pdf_bytes).hexdigest()` com `arquivo["hash"]`.
Se coincidir, usar o `pdf_bytes` passado como parâmetro (o mesmo PDF que foi uploadado no passo anterior).

**Confirmação em log:**
```
[JS-SIGN] pdf_bytes MD5=eeb510b8bbd9e663b0501dd47937b543 hash_doc=eeb510b8bbd9e663b0501dd47937b543 match=True
[JS-SIGN] Usando pdf_bytes (MD5 confere) 212815 bytes
[JS-SIGN] arquivo[0] assinado hashDoc=eeb510b8bbd9e663b0501dd47937b543 sigLen=256
```

**Fallback (se MD5 não confere):** tentar download de URLs candidatas: `/pje/arquivo/<id>`, `/pje/arquivo/<codIni>`, etc.

---

### 13.4 Signing funciona — sigLen=256 confirmado

```python
sig = private_key.sign(doc_bytes, padding.PKCS1v15(), hashes.MD5())
# len(sig) == 256 (RSA 2048 bits → 256 bytes → 344 chars base64)
```

A assinatura RSA PKCS1v15-MD5 sobre os bytes brutos do PDF está **funcionando corretamente**.

---

### 13.5 Mudanças na assinatura de `_assinar_e_enviar`

Parâmetros adicionados à função:

```python
async def _assinar_e_enviar(
    page: Page,
    private_key,
    certchain_b64: str,
    tag: str,
    pdf_bytes: Optional[bytes] = None,      # NOVO: bytes do PDF para match MD5
    cert_der_b64: str = "",                  # NOVO: DER base64 do certificado folha
) -> Optional[str]:
```

**Call site** (linha ~927):
```python
protocolo = await _assinar_e_enviar(
    page, _private_key, _certchain_b64, tag,
    pdf_bytes=pdf_bytes,
    cert_der_b64=base64.b64encode(_cert_obj.public_bytes(Encoding.DER)).decode("ascii"),
)
```

---

### 13.6 Descoberta dos campos do POST via erros incrementais do servidor

O PJe responde com mensagens de erro explícitas quando falta um campo.
Cada tentativa de POST revelou o próximo campo obrigatório:

| Tentativa | Formato | Campos enviados | Resposta do servidor |
|-----------|---------|-----------------|---------------------|
| JSON lista | `application/json` | `[{hashDoc, assinaturaBase64}]` | `"Erro:A assinatura do arquivo não foi fornecida!"` |
| JSON objeto | `application/json` | `{hashDoc, assinaturaBase64}` | `"Erro:A assinatura do arquivo não foi fornecida!"` |
| form | `application/x-www-form-urlencoded` | `assinatura` | `"Erro:A cadeia de certificado do signatário do arquivo não foi fornecida!"` |
| form | idem | `assinatura` + `cadeiaCertificado` | `"Erro:O hash do arquivo assinado não foi fornecido!"` |

**Campos confirmados:**
- ✅ `assinatura` = base64(RSA-PKCS1v15-MD5(pdf_bytes)) — NÃO `assinaturaBase64`
- ✅ `cadeiaCertificado` = PKIPath base64 ou DER base64 do certificado
- ❓ Campo do hash ainda **desconhecido** — server diz "hash não fornecido" mesmo com `hashDoc`

**Fonte:** decompilação de `PjeWebClient.class` confirmou `UrlEncodedFormEntity` com `assinatura` e `cadeiaCertificado`.

---

### 13.7 Estado atual — campo do hash não confirmado

O servidor continua retornando `"Erro:O hash do arquivo assinado não foi fornecido!"` para todas as tentativas com hash. Candidatos implementados no `post_attempts`:

```python
hash_field_variants = ["hashDoc", "hash", "hashArquivoAssinado", "hashArquivo"]
```

Para cada variante, são tentadas 2 formas de certificado (`certchain_b64` PKIPath e `leaf_cert` DER).
Adicionalmente, tentativas **sem hash** (usando apenas `assinatura` + `cadeiaCertificado`) foram adicionadas para o caso de o servidor identificar o documento pelo parâmetro `cid=` da URL.

**Dados concretos para o teste:**
```
arquivo  = {"id": "2241101138", "codIni": "100131276", "hash": "eeb510b8bbd9e663b0501dd47937b543", "isBin": "true"}
uploadUrl = "https://pje1g.trf1.jus.br/pje/arquivoAssinadoUpload.seam?action=peticionamentoAction&cid=302239&mo=P"
```

O MD5 `eeb510b8bbd9e663b0501dd47937b543` é o hash esperado pelo servidor.

---

### 13.8 Hipóteses para "hash não fornecido"

| # | Hipótese | Ação |
|---|----------|------|
| 1 | Campo é `hash` (não `hashDoc`) | Testar — já está em `hash_field_variants` |
| 2 | Campo é `codIni` com valor numérico `"100131276"` | Adicionar `codIni` aos variants |
| 3 | Campo é necessário mas o **valor** deve ser diferente (SHA1? SHA256? hex vs base64?) | Testar com outras representações do hash |
| 4 | Sem hash — servidor usa `cid=` da URL para identificar o documento | Testar variant sem hash |
| 5 | Upload deve ser multipart (não form-encoded) com o arquivo | Inspecionar PjeWebClient.class — há referência a `ByteArrayBody` |

**Próximo passo recomendado ao retomar:** adicionar `codIni` como candidato a campo de hash e rodar o build+test.

---

### 13.9 Decompilação `PjeWebClient.class` — resumo

Strings extraídas do JAR `pje-assinador-jsf.jar`:

| String | Significado |
|--------|-------------|
| `UrlEncodedFormEntity` | Form POST (não multipart, não JSON) |
| `assinatura` | Campo da assinatura digital |
| `cadeiaCertificado` | Campo da cadeia de certificados |
| `StringEntity` | JSON POJO (outro endpoint) |
| `ByteArrayBody` | Multipart com arquivo binário |

Dois formatos possíveis de POST identificados na classe:
1. **Form-encoded** — para `ISignableURLDocument` (docs referenciados por URL)
2. **JSON** — para POJO/`ISignedData`
3. **Multipart** — para uploads de arquivo binário

O endpoint `/arquivoAssinadoUpload.seam` provavelmente corresponde ao caso 1 (form-encoded).

---

### 13.10 Bug corrigido — `utf-8` decode do response body

O body da resposta HTTP do PJe continha caracteres `latin-1` (ex: byte `0xe3` = `ã`).
O código `await resp.text()` falhava com `UnicodeDecodeError`.

**Correção:**
```python
resp_body = (await resp.body()).decode("utf-8", errors="replace")[:400]
```

---

### 13.11 Resumo do estado funcional após esta sessão

| Etapa | Status |
|-------|--------|
| Interceptação PJeOffice via img.src monkey-patch | ✅ Funcional |
| Roteamento cnj.assinadorHash vs sso.autenticador | ✅ Funcional |
| Login SSO com certificado A1 + TOTP | ✅ Funcional |
| Upload do PDF via RichFaces | ✅ Funcional |
| Extração de bytes do PDF p/ assinar (TRF1 sem conteudoBase64) | ✅ Funcional (MD5 match) |
| Assinatura RSA PKCS1v15 MD5 | ✅ Funcional (sigLen=256) |
| Campos `assinatura` e `cadeiaCertificado` no POST | ✅ Confirmados pelo servidor |
| Campo do hash no POST | ❌ Ainda desconhecido — candidatos em teste |
| Upload bem-sucedido para PJe | ❌ Pendente |
