# Interceptor V3 — PJeOffice via Playwright + curl

> Data: 2026-03-04 | Sessao testada e confirmada com sucesso

---

## Resumo

O PJe comunica com o PJeOffice desktop via `img.src = "http://localhost:8800/..."`.
O Chromium bloqueia isso por **Mixed Content** (HTTPS page → HTTP localhost).

O **Interceptor V3** resolve isso:
1. **Bloqueia** o `img.src` no JS antes do browser tentar carregar (evita Mixed Content)
2. **Captura** a URL na fila `window.__pjeoffice_queue[]`
3. **Envia** a URL via `curl` externo (HTTP direto, sem restricao de browser)
4. O PJeOffice processa (assina com certificado, faz POST pro SSO)
5. **Injeta** a resposta de volta no `<img>` via `canvas.toDataURL()`
6. O PJe continua normalmente (onSucesso / onErro)

---

## Fluxo Completo de Login (testado 2026-03-04)

### Passo 1 — Navegar para login

```
https://pje1g.trf1.jus.br/pje/login.seam
→ Redireciona para SSO Keycloak
→ Pagina mostra botao "CERTIFICADO DIGITAL"
```

### Passo 2 — Instalar Interceptor V3

**ANTES de clicar no botao**, injetar o interceptor via `page.evaluate()`:

```javascript
// ==========================================
// INTERCEPTOR V3 — PJeOffice (block + queue + respond)
// ==========================================
(() => {
  window.__pjeoffice_queue = [];
  window.__pje_intercepted_full = [];

  var origDescriptor = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, 'src');

  Object.defineProperty(HTMLImageElement.prototype, 'src', {
    set: function(val) {
      if (val && typeof val === 'string' &&
          val.indexOf('localhost') !== -1 &&
          (val.indexOf('8800') !== -1 || val.indexOf('8801') !== -1)) {

        console.log('[PJeOffice-V3] Captured request - BLOCKED from browser');

        var httpUrl = val.replace('https://', 'http://');
        var entry = {
          url: httpUrl,
          timestamp: Date.now(),
          img: this,
          decodedParams: null,
          onloadSrc: null,
          onerrorSrc: null
        };

        // Decodificar payload r=...
        try {
          var qIdx = httpUrl.indexOf('?r=');
          if (qIdx !== -1) {
            var rRaw = httpUrl.substring(qIdx + 3);
            var ampIdx = rRaw.indexOf('&');
            if (ampIdx !== -1) rRaw = rRaw.substring(0, ampIdx);
            var decoded = JSON.parse(decodeURIComponent(rRaw));
            if (typeof decoded.tarefa === 'string') {
              try { decoded.tarefa = JSON.parse(decoded.tarefa); } catch(e2) {}
            }
            entry.decodedParams = decoded;
          }
        } catch(e) { entry.parseError = e.message; }

        // Capturar onload/onerror para referencia
        if (this.onload) entry.onloadSrc = this.onload.toString().substring(0, 3000);
        if (this.onerror) entry.onerrorSrc = this.onerror.toString().substring(0, 3000);

        window.__pjeoffice_queue.push(entry);
        window.__pje_intercepted_full.push({
          url: httpUrl,
          decodedParams: entry.decodedParams,
          onloadSrc: entry.onloadSrc,
          onerrorSrc: entry.onerrorSrc,
          ts: entry.timestamp
        });

        // *** NAO SETA SRC REAL → evita Mixed Content ***
        return;
      }

      // Tudo que nao e PJeOffice passa normalmente
      origDescriptor.set.call(this, val);
    },
    get: function() { return origDescriptor.get.call(this); }
  });

  // Funcao para injetar resposta de volta no img
  window.__pjeoffice_respond = function(index, width, height) {
    var entry = window.__pjeoffice_queue[index];
    if (entry && entry.img) {
      var canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;

      // Definir width/height no img (PJe usa this.width para verificar sucesso)
      Object.defineProperty(entry.img, 'width', { value: width, configurable: true });
      Object.defineProperty(entry.img, 'height', { value: height, configurable: true });

      // Setar src como data URI (dispara onload sem request de rede)
      origDescriptor.set.call(entry.img, canvas.toDataURL('image/gif'));

      console.log('[PJeOffice-V3] Response injected: ' + width + 'x' + height);
    }
  };
})();
```

### Passo 3 — Clicar "CERTIFICADO DIGITAL"

```javascript
// Playwright
await page.getByRole('button', { name: 'CERTIFICADO DIGITAL' }).click();
```

O console vai mostrar:
```
[PJeOffice-V3] Captured request - BLOCKED from browser
```

### Passo 4 — Ler a URL capturada

```javascript
// Aguardar captura
await page.waitForFunction('window.__pjeoffice_queue.length > 0');

// Ler URL e payload decodificado
const captured = await page.evaluate(() => ({
  url: window.__pjeoffice_queue[0].url,
  params: window.__pjeoffice_queue[0].decodedParams
}));
```

**Payload capturado (LOGIN SSO):**

```json
{
  "sessao": "KEYCLOAK_SESSION=pje/<user-uuid>/<session-uuid>; ...; AWSALB=...; AWSALBCORS=...",
  "aplicacao": "PJe",
  "servidor": "https://sso.cloud.pje.jus.br/auth/realms/pje",
  "codigoSeguranca": "<RSA_ENCRYPTED_BASE64>",
  "tarefaId": "sso.autenticador",
  "tarefa": {
    "enviarPara": "/pjeoffice-rest",
    "mensagem": "0.60815471443755",
    "token": "9ea3aad8-eff4-43a9-925b-162e4d2c9a7d"
  }
}
```

**onload capturado:**
```javascript
function(token) {
  if (this.width == 2) {
    onErro();        // PJeOffice retornou erro
  } else {
    onSucesso(token); // PJeOffice retornou sucesso
  }
}
```

**onerror capturado:**
```javascript
function () {
  alert("Nao foi possivel encontrar o PJe Office.");
}
```

### Passo 5 — Enviar via curl para o PJeOffice

```bash
curl -s \
  -o /tmp/pjeoffice_login_response.bin \
  -w "HTTP=%{http_code} SIZE=%{size_download} TIME=%{time_total}" \
  --max-time 120 \
  "<URL_CAPTURADA_DO_PASSO_4>"
```

**Resultado real (sessao 2026-03-04):**
```
HTTP=200  SIZE=43  TIME=22.73
```

- 43 bytes = GIF 1x1 = **SUCESSO**
- 22.7s = tempo que o PJeOffice levou (popup de senha do certificado)
- O PJeOffice internamente:
  1. Leu o certificado A1 (PFX)
  2. Pediu a senha via popup GUI
  3. Assinou o `mensagem` com MD5withRSA
  4. Fez POST para `https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest`
  5. SSO respondeu HTTP 204 (sucesso)
  6. PJeOffice retornou GIF 1x1

### Passo 6 — Injetar resposta de volta na pagina

```javascript
// Simular sucesso (1x1 = width 1 → onSucesso())
await page.evaluate(() => {
  window.__pjeoffice_respond(0, 1, 1);
});
```

Isso faz:
1. Cria `<canvas>` 1x1
2. Define `img.width = 1`, `img.height = 1`
3. Seta `img.src = canvas.toDataURL('image/gif')`
4. Browser dispara `img.onload`
5. `onload` verifica `this.width == 2` → **nao** → chama `onSucesso()`
6. SSO/Keycloak redireciona para tela de **TOTP**

### Passo 7 — Preencher TOTP

```python
import pyotp
code = pyotp.TOTP('MNFTCT2WKBJFKU3NGN2GYNKUJVDVKM3X').now()
```

```javascript
await page.getByRole('textbox').fill(code);
await page.getByRole('button', { name: 'Validar' }).click();
```

**Resultado:** Redireciona para `https://pje1g.trf1.jus.br/pje/QuadroAviso/listViewQuadroAvisoMensagem.seam`
→ Logado como **"amanda sousa"** no Quadro de Avisos.

---

## Verificacao da Imagem de Resposta

```python
from PIL import Image
import io

data = open('/tmp/pjeoffice_login_response.bin', 'rb').read()
img = Image.open(io.BytesIO(data))

# width=1, height=1 → SUCESSO
# width=2, height=1 → ERRO
print(f'{img.size[0]}x{img.size[1]} {img.format}')  # "1x1 GIF"
```

---

## Diferenca entre Login (SSO) e Assinatura de Documento

| Campo | Login (sso.autenticador) | Assinatura (cnj.assinadorHash) |
|-------|--------------------------|-------------------------------|
| `tarefaId` | `sso.autenticador` | `cnj.assinadorHash` |
| `servidor` | `https://sso.cloud.pje.jus.br/auth/realms/pje` | `https://pje1g.trf1.jus.br/pje` |
| `tarefa.enviarPara` | `/pjeoffice-rest` | _(nao tem)_ |
| `tarefa.token` | UUID do SSO | _(nao tem)_ |
| `tarefa.mensagem` | Random float (nonce) | _(nao tem)_ |
| `tarefa.uploadUrl` | _(nao tem)_ | `/arquivoAssinadoUpload.seam?...` |
| `tarefa.arquivos` | _(nao tem)_ | `[{id, codIni, hash, isBin}]` |
| O que PJeOffice faz | Assina nonce → POST SSO `/pjeoffice-rest` | Assina hash do PDF → POST `uploadUrl` |
| Tempo resposta | ~18-22s (pede senha) | Variavel |

---

## O que o PJeOffice Faz Internamente (sso.autenticador)

```
1. Recebe GET http://localhost:8800/pjeOffice/requisicao/?r={payload}
2. Decodifica JSON do parametro r
3. Verifica codigoSeguranca (RSA)
4. Mostra popup pedindo senha do certificado PFX (se nao cacheada)
5. Le certificado A1 do arquivo PFX
6. Assina tarefa.mensagem com RSA PKCS1v15 + MD5
7. Monta payload JSON:
   {
     "certChain": "<PKIPath base64>",
     "uuid": "<tarefa.token>",
     "mensagem": "<tarefa.mensagem>",
     "assinatura": "<base64(RSA_MD5(mensagem))>"
   }
8. POST para {servidor}{tarefa.enviarPara}
   → https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest
   → Content-Type: application/json
   → Resposta esperada: HTTP 204 No Content
9. Retorna imagem GIF:
   - 1x1 = sucesso
   - 2x1 = erro
```

---

## O que o PJeOffice Faz Internamente (cnj.assinadorHash)

```
1. Recebe GET http://localhost:8800/pjeOffice/requisicao/?r={payload}
2. Decodifica JSON
3. Para cada arquivo em tarefa.arquivos:
   a. Usa o hash MD5 do arquivo (campo "hash")
   b. Assina os bytes do documento com RSA PKCS1v15 + MD5
   c. POST para {servidor}{tarefa.uploadUrl}
      Content-Type: application/x-www-form-urlencoded
      Campos:
        - assinatura = base64(RSA_PKCS1v15_MD5(doc_bytes))
        - cadeiaCertificado = base64(PKIPath DER ou cert DER)
        - ??? (campo do hash — ainda desconhecido)
4. Retorna imagem GIF 1x1 (sucesso) ou 2x1 (erro)
```

---

## Erros Comuns

### Mixed Content (sem interceptor)
```
Mixed Content: The page at 'https://sso.cloud.pje.jus.br/...'
was loaded over HTTPS, but requested an insecure image
'http://localhost:8800/...'
```
**Solucao:** Usar Interceptor V3 (bloquear img.src, enviar via curl)

### PJeOffice retorna 2x1 (erro)
```
HTTP=200 SIZE=90 (PNG 2x1)
```
**Causa 1:** Token ja consumido (sessao duplicada)
**Causa 2:** PJeOffice nao conseguiu fazer POST pro SSO (HTTP 500 no servidor)
**Causa 3:** Senha do certificado incorreta ou cancelada

**Erro capturado na sessao:**
```
PjeClientException: Servidor retornando - HTTP Code: 500
Content: {"error":"Exception","errorDescription":"javax.persistence.PersistenceException:
org.hibernate.exception.ConstraintViolationException: could not execute statement"}
```
→ Isso acontece quando o mesmo token e enviado 2 vezes (login duplo na mesma sessao)

### PJeOffice nao responde (timeout)
```
curl: (28) Operation timed out after 120000 milliseconds
```
**Causa:** Popup de senha aberto esperando interacao do usuario, ou PJeOffice travado

---

## Codigo Playwright Completo (Login)

```python
import pyotp
from playwright.async_api import async_playwright

TOTP_SECRET = "MNFTCT2WKBJFKU3NGN2GYNKUJVDVKM3X"

INTERCEPTOR_V3_JS = """
(() => {
  window.__pjeoffice_queue = [];
  var origDescriptor = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, 'src');
  Object.defineProperty(HTMLImageElement.prototype, 'src', {
    set: function(val) {
      if (val && typeof val === 'string' && val.indexOf('localhost') !== -1 &&
          (val.indexOf('8800') !== -1 || val.indexOf('8801') !== -1)) {
        console.log('[PJeOffice-V3] Captured request');
        var httpUrl = val.replace('https://', 'http://');
        window.__pjeoffice_queue.push({ url: httpUrl, timestamp: Date.now(), img: this });
        return;  // BLOQUEIA — nao seta src real
      }
      origDescriptor.set.call(this, val);
    },
    get: function() { return origDescriptor.get.call(this); }
  });
  window.__pjeoffice_respond = function(index, width, height) {
    var entry = window.__pjeoffice_queue[index];
    if (entry && entry.img) {
      var canvas = document.createElement('canvas');
      canvas.width = width; canvas.height = height;
      Object.defineProperty(entry.img, 'width', {value: width, configurable: true});
      Object.defineProperty(entry.img, 'height', {value: height, configurable: true});
      origDescriptor.set.call(entry.img, canvas.toDataURL('image/gif'));
    }
  };
})();
"""

async def login_pje_trf1():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # 1. Navegar para login
        await page.goto("https://pje1g.trf1.jus.br/pje/login.seam")

        # 2. Instalar interceptor V3
        await page.evaluate(INTERCEPTOR_V3_JS)

        # 3. Clicar certificado digital
        await page.get_by_role("button", name="CERTIFICADO DIGITAL").click()

        # 4. Aguardar captura
        await page.wait_for_function("window.__pjeoffice_queue.length > 0")
        url = await page.evaluate("() => window.__pjeoffice_queue[0].url")

        # 5. Enviar via subprocess (curl)
        import subprocess
        result = subprocess.run(
            ["curl", "-s", "-o", "/tmp/pjeoffice_resp.bin",
             "-w", "%{http_code}|%{size_download}", "--max-time", "120", url],
            capture_output=True, text=True
        )
        http_code, size = result.stdout.split("|")

        # 6. Verificar resposta
        from PIL import Image
        import io
        data = open("/tmp/pjeoffice_resp.bin", "rb").read()
        img = Image.open(io.BytesIO(data))
        success = img.size[0] == 1  # 1x1 = sucesso

        if success:
            # 7. Injetar resposta
            await page.evaluate("() => window.__pjeoffice_respond(0, 1, 1)")

            # 8. Preencher TOTP
            await page.wait_for_url("**/authenticate*", timeout=30000)
            totp_code = pyotp.TOTP(TOTP_SECRET).now()
            await page.get_by_role("textbox").fill(totp_code)
            await page.get_by_role("button", name="Validar").click()

            # 9. Aguardar painel
            await page.wait_for_url("**/QuadroAviso/**", timeout=30000)
            print("Login OK!")
        else:
            print(f"PJeOffice retornou ERRO: {img.size[0]}x{img.size[1]}")

        await browser.close()
```

---

## Certificado de Teste

```
Advogada:   Amanda Alves de Sousa
CPF:        07071649316
PFX:        /home/wital/jusMonitor/docs/Amanda Alves de Sousa_07071649316.pfx
Senha PFX:  22051998
TOTP:       MNFTCT2WKBJFKU3NGN2GYNKUJVDVKM3X (SHA1, 6 digitos, 30s)
```

---

## Proximos Passos

- [ ] Capturar fluxo completo de assinatura (`cnj.assinadorHash`) com interceptor V3
- [ ] Descobrir campos exatos do POST para `uploadUrl` (campo do hash ainda desconhecido)
- [ ] Automatizar sem PJeOffice (assinar direto em Python com a chave privada)
- [ ] Integrar no scraper Docker (sem GUI, sem PJeOffice)
