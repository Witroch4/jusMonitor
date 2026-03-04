# PJeOffice Signing Flow — Documentacao Completa

Data: 2026-03-04 (atualizado)

## Resumo

Interceptamos com sucesso o payload completo que o PJe envia ao PJeOffice durante a assinatura de documentos no fluxo "Juntar documentos" (peticao avulsa). Tambem testamos o fluxo completo de login via certificado digital com proxy manual.

## Fluxo de Comunicacao

### 1. PJe → PJeOffice (via img.src)

O PJe comunica com o PJeOffice desktop via `img.src` HTTP:

```
http://localhost:8800/pjeOffice/requisicao/?r={payload_json_url_encoded}&u={timestamp}
```

- **Porta**: 8800 (nao 8080 como documentado em alguns lugares)
- **Protocolo**: HTTP (nao HTTPS)
- **Metodo**: GET (via img.src, o browser faz GET automatico)
- **Mixed Content**: Chromium auto-upgrades para HTTPS, quebrando a comunicacao. PJeOffice nao tem HTTPS.

### 2. Payload Decodificado — Tarefa `cnj.assinadorHash`

```json
{
  "aplicacao": "PJe",
  "servidor": "https://pje1g.trf1.jus.br/pje",
  "sessao": "JSESSIONID=...; UqZBpD3n=...; KEYCLOAK_IDENTITY=<JWT>; PJE-TRF1-1G-StickySessionRule=\"pje1gprdwf58:pje-trf1-1g\"; MO=P",
  "codigoSeguranca": "<RSA_ENCRYPTED_BASE64>",
  "tarefaId": "cnj.assinadorHash",
  "tarefa": {
    "algoritmoAssinatura": "ASN1MD5withRSA",
    "modoTeste": "false",
    "uploadUrl": "/arquivoAssinadoUpload.seam?action=consultaProcessoAction&cid=111778&mo=P",
    "arquivos": [
      {
        "id": "2241101138",
        "codIni": "100131276",
        "hash": "eeb510b8bbd9e663b0501dd47937b543",
        "isBin": "true"
      }
    ]
  }
}
```

### 3. Payload Decodificado — Tarefa `sso.autenticador` (Login)

```json
{
  "sessao": "KEYCLOAK_SESSION=pje/c6e25616-.../1297dba3-...; AWSALB=...; AWSALBCORS=...",
  "aplicacao": "PJe",
  "servidor": "https://sso.cloud.pje.jus.br/auth/realms/pje",
  "codigoSeguranca": "<RSA_ENCRYPTED_BASE64>",
  "tarefaId": "sso.autenticador",
  "tarefa": {
    "enviarPara": "/pjeoffice-rest",
    "mensagem": "0.1071459677188139",
    "token": "1dcf1e0f-0801-4a94-aed5-54733bcd0d5e"
  }
}
```

**Nota**: No login SSO, o `servidor` aponta para o Keycloak (`sso.cloud.pje.jus.br`), nao para o PJe diretamente.

### 4. Campos Explicados

| Campo | Descricao |
|-------|-----------|
| `aplicacao` | Sempre "PJe" |
| `servidor` | URL base do PJe (assinatura) ou Keycloak (login SSO) |
| `sessao` | Cookies da sessao do browser (JSESSIONID, KEYCLOAK_IDENTITY JWT, sticky session) |
| `codigoSeguranca` | Codigo de seguranca criptografado com RSA (Base64) — mesmo valor em login e assinatura |
| `tarefaId` | Tipo de tarefa: `cnj.assinadorHash` para assinatura, `sso.autenticador` para login |
| `tarefa.algoritmoAssinatura` | `ASN1MD5withRSA` — algoritmo de assinatura |
| `tarefa.modoTeste` | `"false"` em producao |
| `tarefa.uploadUrl` | Endpoint onde PJeOffice faz POST com bytes assinados |
| `tarefa.arquivos[].id` | ID do arquivo no PJe |
| `tarefa.arquivos[].codIni` | Codigo inicial do arquivo |
| `tarefa.arquivos[].hash` | Hash MD5 do arquivo a assinar |
| `tarefa.arquivos[].isBin` | Se o arquivo e binario |

### 5. Diferenca Login vs Assinatura

| | Login (SSO) | Assinatura |
|---|---|---|
| `tarefaId` | `sso.autenticador` | `cnj.assinadorHash` |
| `servidor` | `https://sso.cloud.pje.jus.br/auth/realms/pje` | `https://pje1g.trf1.jus.br/pje` |
| `tarefa.enviarPara` | `/pjeoffice-rest` | (nao tem) |
| `tarefa.token` | UUID token SSO | (nao tem) |
| `tarefa.mensagem` | Random float | (nao tem) |
| `tarefa.uploadUrl` | (nao tem) | `/arquivoAssinadoUpload.seam?...` |
| `tarefa.arquivos` | (nao tem) | Array com id, hash, codIni |
| Tempo resposta | ~18-20s (pede senha do certificado) | Variavel (pode demorar) |
| PJeOffice faz | Assina token + POST para SSO Keycloak | Assina hash + POST para uploadUrl |

### 6. O que PJeOffice faz internamente

1. **Recebe** o GET request em `localhost:8800/pjeOffice/requisicao/`
2. **Decodifica** o JSON do parametro `r`
3. **Verifica** o `codigoSeguranca` (RSA)
4. **Mostra popup** pedindo senha do certificado PFX (se nao estiver em cache)
5. **Para `sso.autenticador`**:
   - Le o certificado A1 (PFX)
   - Assina o token com o certificado
   - Faz POST para `{servidor}{enviarPara}` com o token assinado
6. **Para `cnj.assinadorHash`**:
   - Le o certificado A1 (PFX)
   - Computa a assinatura `ASN1MD5withRSA` sobre o `hash` de cada arquivo
   - Faz `POST` para `{servidor}{uploadUrl}` com os bytes assinados, usando os cookies da `sessao`
7. **Retorna** imagem GIF/PNG:
   - `width=1, height=1` → sucesso
   - `width=2, height=1` → erro

### 7. O que PJe faz apos resposta

Apos `img.onload` com `width=1`:
- **Login**: Keycloak redireciona para a pagina de TOTP (se configurado) ou direto pro painel
- **Assinatura**: PJe inicia polling A4J para verificar se o documento foi processado, mostra "Por favor aguarde"

## Workaround: Proxy Manual via Playwright + curl

### Problema
Chromium bloqueia Mixed Content (HTTP de pagina HTTPS). O `--allow-insecure-localhost` NAO resolve Mixed Content para img.src.

### Solucao Testada e Funcionando (V3 Interceptor + curl)

1. **Instalar interceptor V3 no browser** — override `HTMLImageElement.prototype.src` setter
2. Quando PJe tenta setar `img.src = "http://localhost:8800/..."`, o interceptor captura a URL e armazena em `window.__pjeoffice_queue[]` SEM setar o src real
3. **Fazer curl externo** com a URL capturada (HTTP direto, sem Mixed Content)
4. **PJeOffice responde** (pode mostrar popup de senha) → retorna imagem GIF
5. **Simular resposta no img** via `canvas.toDataURL()` com as dimensoes corretas (1x1 = sucesso)
6. O PJe continua o fluxo normalmente

```javascript
// Interceptor V3 — instalar na pagina antes de clicar
window.__pjeoffice_queue = [];
const origDescriptor = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, 'src');
Object.defineProperty(HTMLImageElement.prototype, 'src', {
  set: function(val) {
    if (val && val.includes('localhost') && val.includes('8800')) {
      console.log('[PJeOffice-V3] Captured request');
      window.__pjeoffice_queue.push({
        url: val.replace('https://', 'http://'),
        timestamp: Date.now(),
        img: this
      });
      return; // NAO seta src → evita Mixed Content
    }
    origDescriptor.set.call(this, val);
  },
  get: function() { return origDescriptor.get.call(this); }
});

// Apos curl retornar, simular resposta:
window.__pjeoffice_respond = function(index, width, height) {
  const entry = window.__pjeoffice_queue[index];
  if (entry && entry.img) {
    const canvas = document.createElement('canvas');
    canvas.width = width; canvas.height = height;
    origDescriptor.set.call(entry.img, canvas.toDataURL('image/gif'));
  }
};
```

```bash
# curl externo — fazer APOS capturar URL na fila
curl -s -o /tmp/pjeoffice_response.bin \
  -w "HTTP=%{http_code} SIZE=%{size_download} TIME=%{time_total}" \
  --max-time 60 \
  "http://localhost:8800/pjeOffice/requisicao/?r=..."
```

### Resultado Confirmado
- Login SSO via interceptor V3 + curl: **FUNCIONA**
- PJeOffice respondeu em ~19s com 43 bytes (GIF 1x1 = sucesso)
- Apos simular resposta no img, PJe redirecionou para pagina de TOTP
- TOTP validado com sucesso, login completo no painel do PJe

## Abordagens que NAO Funcionam

### 1. `--allow-insecure-localhost` flag do Chrome
- **Nao resolve Mixed Content** — esta flag permite certificados auto-assinados em localhost, mas NAO impede o auto-upgrade de HTTP→HTTPS
- Chromium ainda auto-upgrades `http://localhost:8800` → `https://localhost:8800`
- Testado com Chrome 145.0.7632.6 lancado via remote debugging

### 2. `page.route()` com proxy Node.js http
- `page.route(/localhost.*8800/)` NAO intercepta requests de img.src quando Mixed Content bloqueia
- O bloqueio acontece no nivel do browser engine ANTES do Playwright poder interceptar
- Quando a gente forca via JS, o `require('http')` no handler de page.route trava a conexao MCP (blocking call de ~20s mata o MCP)

### 3. `page.route()` (qualquer variante)
- Playwright route interception nao funciona para Mixed Content blocked requests
- O browser nem chega a fazer o request — cancela antes

### 4. XHR/fetch no contexto da pagina
- Tambem bloqueados por Mixed Content (mesmo origin http://localhost)
- `fetch('http://localhost:8800/...')` → `ERR_FAILED`

### 5. Conectar Playwright MCP via CDP endpoint
- Configurar `--cdp-endpoint http://localhost:9222` no MCP args
- O Playwright MCP NAO releu a config apos browser_close — continuou usando Chrome 140 proprio
- Precisa reiniciar o MCP server inteiro (nao basta fechar o browser)

## PJeOffice Pro (Linux)

### Localizacao
```
docs/pjeoffice-pro/
├── pjeoffice-pro.sh    # Script de lancamento
├── pjeoffice-pro.jar   # JAR principal
├── jre/                # JRE bundled
└── ...
```

### Lancamento
```bash
cd docs/pjeoffice-pro/
./pjeoffice-pro.sh
```

### Verificacao
```bash
# Verificar porta
ss -tlnp | grep 8800
# Deve mostrar: [::1]:8800 ou 0.0.0.0:8800

# Testar conectividade
curl -s -o /dev/null -w "%{http_code}" http://localhost:8800/
# Retorna 404 (normal — endpoint raiz nao existe)
```

### Problemas com PJeOffice
- **Popups de autorizacao**: PJeOffice pode mostrar popups pedindo autorizacao ou senha do certificado. Se nao forem respondidos, o PJeOffice trava (aceita TCP mas nao responde)
- **Solucao**: Manter PJeOffice visivel na tela e responder popups imediatamente
- **Timeout via curl**: Se curl conecta mas recebe 0 bytes apos 120s, provavelmente tem popup nao respondido

## Cookies da Sessao (Decodificados)

### KEYCLOAK_IDENTITY JWT Claims
```json
{
  "exp": 1772672920,
  "iat": 1772644121,
  "auth_time": 1772644120,
  "iss": "https://sso.cloud.pje.jus.br/auth/realms/pje",
  "aud": "pje-trf1-1g",
  "sub": "c6e25616-900d-45e8-b1df-e12472f43ef2",
  "typ": "ID",
  "azp": "pje-trf1-1g",
  "session_state": "b8e0f2a9-fb4f-48c8-b95f-7887eee50630",
  "loginComCertificado": true,
  "name": "AMANDA ALVES DE SOUSA",
  "JTR": "401",
  "preferred_username": "07071649316",
  "given_name": "AMANDA ALVES DE",
  "family_name": "SOUSA",
  "email": "amandasousa22.adv@gmail.com"
}
```

### Outros cookies
- `JSESSIONID`: Session ID do JBoss/Wildfly
- `UqZBpD3n`: Cookie de tracking
- `PJE-TRF1-1G-StickySessionRule`: Load balancer sticky session → `pje1gprdwf58:pje-trf1-1g`
- `MO`: `P` (modo de operacao?)

### Cookies SSO (Login)
- `KEYCLOAK_SESSION`: Session do Keycloak (realm/user-uuid/session-uuid)
- `KEYCLOAK_SESSION_LEGACY`: Idem (compatibilidade)
- `AWSALB` / `AWSALBCORS`: AWS ALB session stickiness

## Implicacoes para o Scraper

1. **O scraper NAO precisa resolver Mixed Content** — ele faz requests HTTP direto via httpx/aiohttp, nao via browser
2. **O scraper ja faz isso** via `pjeoffice-pro` (nosso PJeOffice local) ou via SSO direto
3. **O problema real do scraper** nao e a comunicacao com PJeOffice, mas sim o polling pos-assinatura
4. **A fix do plano** (early exit no polling loop) e a correcao certa — o A4J loading overlay nunca limpa, mas a assinatura ja foi feita com sucesso
5. **PJeOffice pode travar** se houver popups nao respondidos — o scraper deve verificar timeout e reiniciar PJeOffice se necessario

## TOTP

- Secret: `MNFTCT2WKBJFKU3NGN2GYNKUJVDVKM3X`
- Algoritmo: SHA1
- Periodo: 30s
- Digitos: 6
- Uso: `pyotp.TOTP('MNFTCT2WKBJFKU3NGN2GYNKUJVDVKM3X').now()`

## Fluxo Completo Login (testado manualmente 2026-03-04)

1. Navegar para `https://pje1g.trf1.jus.br/pje/login.seam`
2. Instalar interceptor V3 (override img.src)
3. Clicar "CERTIFICADO DIGITAL"
4. Interceptor captura URL `http://localhost:8800/pjeOffice/requisicao/?r=...&u=...`
5. Fazer curl com a URL capturada → PJeOffice mostra popup de senha → responde 43 bytes (GIF 1x1)
6. Simular resposta no img com `__pjeoffice_respond(0, 1, 1)`
7. PJe redireciona para pagina de TOTP
8. Inserir codigo TOTP (secret: MNFTCT2WKBJFKU3NGN2GYNKUJVDVKM3X)
9. Clicar "Validar" → redireciona para Quadro de Avisos (logado como "amanda sousa")

## Arquivos Relacionados

- `scraper/app/scrapers/pje_peticionamento.py` — Scraper de peticionamento
- `docs/PETICIONAMENTO_AVULSO_E2E.md` — Documentacao anterior do fluxo
- `docs/PJEOFFICE_INTEGRACAO.md` — Integracao PJeOffice
- `docs/PJEOFFICE_SETUP.md` — Setup PJeOffice
- `docs/pjeoffice-pro/` — PJeOffice Pro (Linux) binarios + script
- `scripts/totp_live.py` — Script TOTP live viewer
