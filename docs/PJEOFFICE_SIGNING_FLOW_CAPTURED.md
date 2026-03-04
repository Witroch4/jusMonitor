# PJeOffice — Fluxo Completo de Assinatura Capturado (cnj.assinadorHash)

> **Data da captura:** 2026-03-04  
> **Método:** Interceptor V3 (block + queue + curl + inject) via Playwright MCP  
> **Tribunal:** TRF1 — PJe 1º Grau  
> **Processo:** 1098298-53.2025.4.01.3400 (MANDADO DE SEGURANÇA CÍVEL)  
> **Parte:** Eduardo Cavalcante Lemos  
> **Advogada:** Amanda Alves de Sousa (CPF 07071649316)  
> **Resultado:** ✅ **"Documento(s) assinado(s) com sucesso. O peticionamento foi concluído com sucesso"**

---

## Índice

1. [Visão Geral do Fluxo](#1-visão-geral-do-fluxo)
2. [Payload Capturado — cnj.assinadorHash](#2-payload-capturado--cnjassinadorhash)
3. [Callbacks onload/onerror Capturados](#3-callbacks-onloadonerror-capturados)
4. [Execução: curl → PJeOffice → Resultado](#4-execução-curl--pjeoffice--resultado)
5. [Resposta Injetada → Sucesso no PJe](#5-resposta-injetada--sucesso-no-pje)
6. [Decompilação do PJeOffice Pro — POST Exato](#6-decompilação-do-pjeoffice-pro--post-exato)
7. [Comparação: Login (sso.autenticador) vs Assinatura (cnj.assinadorHash)](#7-comparação-login-vs-assinatura)
8. [O que o PJeOffice Faz Internamente](#8-o-que-o-pjeoffice-faz-internamente)
9. [Formato do POST para uploadUrl — Confirmado por Decompilação](#9-formato-do-post-para-uploadurl)
10. [Algoritmo de Assinatura](#10-algoritmo-de-assinatura)
11. [Erros do Servidor e Campos Obrigatórios](#11-erros-do-servidor-e-campos-obrigatórios)
12. [Como Replicar Sem PJeOffice (Scraper)](#12-como-replicar-sem-pjeoffice)
13. [Referências e Arquivos](#13-referências-e-arquivos)

---

## 1. Visão Geral do Fluxo

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    FLUXO E2E CAPTURADO — PETIÇÃO AVULSA                      │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. Login PJe (intercept sso.autenticador → curl → PJeOffice → GIF 1x1)     │
│  2. TOTP (pyotp → código 6 dígitos → "Validar")                             │
│  3. Navegar para peticionamento avulso                                       │
│  4. Pesquisar processo 1098298-53.2025.4.01.3400                             │
│  5. Abrir popup peticaoPopUp.seam                                            │
│  6. Selecionar "Arquivo PDF", fazer upload do PDF                            │
│  7. Clicar "Assinar documento(s)"                                            │
│     ↓                                                                        │
│  8. PJe JS cria: img.src = "http://localhost:8800/pjeOffice/requisicao/?r=…" │
│     ↓                                                                        │
│  9. INTERCEPTOR V3 BLOQUEIA o img.src (não vai pra rede)                     │
│ 10. Captura URL + payload na fila window.__pjeoffice_queue[]                 │
│ 11. Lê URL capturada e envia via CURL externo pro PJeOffice                  │
│     ↓                                                                        │
│ 12. PJeOffice recebe, assina, faz POST pro uploadUrl do PJe                  │
│ 13. PJeOffice retorna GIF 1x1 (43 bytes) = SUCESSO                          │
│     ↓                                                                        │
│ 14. Injetamos resposta no img via canvas.toDataURL (width=1, height=1)       │
│ 15. PJe JS verifica: this.width != 2 → chama onSucesso()                    │
│ 16. onSucesso() → A4J.AJAX.Submit → servidor confirma                       │
│     ↓                                                                        │
│ 17. ✅ "Documento(s) assinado(s) com sucesso"                                │
│ 18. ✅ "O peticionamento foi concluído com sucesso"                           │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Payload Capturado — cnj.assinadorHash

### 2.1 URL Completa Interceptada

Quando o advogado clica "Assinar documento(s)", o PJe JS executa:
```javascript
var img = new Image();
img.onload = function() { /* ver seção 3 */ };
img.onerror = function() { /* ver seção 3 */ };
img.src = "http://localhost:8800/pjeOffice/requisicao/?r=" + encodeURIComponent(JSON.stringify(payload));
```

**URL capturada pelo Interceptor V3 (length: 2606 chars):**
```
http://localhost:8800/pjeOffice/requisicao/?r=%7B%22aplicacao%22%3A%22PJe%22%2C%22servidor%22%3A%22https%3A%2F%2Fpje1g.trf1.jus.br%2Fpje%22%2C%22sessao%22%3A%22JSESSIONID%3D...%22%2C%22codigoSeguranca%22%3A%22lXiw1e3N...%22%2C%22tarefaId%22%3A%22cnj.assinadorHash%22%2C%22tarefa%22%3A%22...%22%7D
```

### 2.2 Payload JSON Decodificado (COMPLETO)

```json
{
  "aplicacao": "PJe",
  "servidor": "https://pje1g.trf1.jus.br/pje",
  "sessao": "JSESSIONID=D08B99...F167A8BE.pje1g2; KEYCLOAK_IDENTITY=eyJhbGciOiJSUzI1NiIs...<JWT_COMPLETO>; PJE-TRF1-1G-StickySessionRule=pje1g.trf1.jus.br|pje1g2; MO=P",
  "codigoSeguranca": "lXiw1e3NgriI1KGbtvkWdNBON1B6ZPxkijAzWXTcbw23eAhYzQskeWjV2R/uMuqr7m52/U1B95ckKDTHymutUtayCv8HwwUo/YcVpb6CLC3oBjbJscjhuXCiaAfYYZnNrRp1dao1zLr8VRW+1rdvXAhlHzxJdzofx62TZH1ZrXrRRyRlmswaAILj4yMSgpr9JTZ19HtQWk7gz4u0loPqHOGOJ1b3oCgkq6j3CPViGNEe8mIDuorUK2M2sZ0c1OUIHzAQv6bTL89cLxEOCU+5lXRHab+B6MCW2pKj3oyrHDauXy2PPuybErID/5IW0MVL47dC5iA7cb2ObZqiX41xhA==",
  "tarefaId": "cnj.assinadorHash",
  "tarefa": {
    "algoritmoAssinatura": "ASN1MD5withRSA",
    "modoTeste": "false",
    "uploadUrl": "/arquivoAssinadoUpload.seam?action=peticionamentoAction&cid=296527&mo=P",
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

### 2.3 Descrição de Cada Campo

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `aplicacao` | string | Sempre `"PJe"` |
| `servidor` | string | URL base do tribunal — `https://pje1g.trf1.jus.br/pje` |
| `sessao` | string | Cookies da sessão PJe (JSESSIONID + KEYCLOAK_IDENTITY JWT + StickySession + MO) |
| `codigoSeguranca` | string | RSA encrypted security code (base64) — validação de origem |
| `tarefaId` | string | **`"cnj.assinadorHash"`** — identifica a tarefa de assinatura de documento |
| `tarefa` | object | Parâmetros específicos da tarefa (ver abaixo) |

### 2.4 Campos da `tarefa` (cnj.assinadorHash)

| Campo | Tipo | Valor Capturado | Descrição |
|-------|------|-----------------|-----------|
| `algoritmoAssinatura` | string | `"ASN1MD5withRSA"` | Algoritmo de assinatura digital a usar |
| `modoTeste` | string | `"false"` | Se `"true"`, PJeOffice não envia realmente |
| `uploadUrl` | string | `"/arquivoAssinadoUpload.seam?action=peticionamentoAction&cid=296527&mo=P"` | Endpoint relativo para POST dos dados assinados |
| `arquivos` | array | `[{...}]` | Lista de documentos a assinar |

### 2.5 Campos de Cada `arquivo`

| Campo | Tipo | Valor Capturado | Descrição |
|-------|------|-----------------|-----------|
| `id` | string | `"2241101138"` | ID do documento no PJe |
| `codIni` | string | `"100131276"` | Código inicial do arquivo no banco |
| `hash` | string | `"eeb510b8bbd9e663b0501dd47937b543"` | **Hash MD5 hex do PDF** (32 chars = 128 bits MD5) |
| `isBin` | string | `"true"` | Flag indicando que é arquivo binário |

### 2.6 O que NÃO existe no payload TRF1

| Campo Ausente | Significado |
|---------------|-------------|
| `conteudoBase64` | O PDF **NÃO** vem embedado no payload. O PJeOffice precisa obter os bytes de outra forma |
| `mensagem` | Não tem nonce/challenge como no sso.autenticador |
| `enviarPara` | Não tem endpoint SSO como no login |
| `token` | Não tem UUID de token como no login |

**NOTA CRÍTICA:** O `hash` (`eeb510b8bbd9e663b0501dd47937b543`) é o MD5 hexadecimal do PDF que foi feito upload anteriormente. Confirmado:
```python
import hashlib
pdf_md5 = hashlib.md5(pdf_bytes).hexdigest()
# "eeb510b8bbd9e663b0501dd47937b543" == arquivo["hash"]  ✅ CONFERE
```

---

## 3. Callbacks onload/onerror Capturados

### 3.1 img.onload (capturado via interceptor)

```javascript
function () {
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

**Lógica:**
- `this.width == 2` → **ERRO** → chama `onErro()`
- `this.width != 2` (qualquer outro valor, incluindo 1) → **SUCESSO** → chama `onSucesso()`

### 3.2 img.onerror (capturado via interceptor)

```javascript
function () {
    hideMpProgresso();
    Richfaces.showModalPanel('mpPJeOfficeIndisponivel');
}
```

**Lógica:** Esconde o modal de progresso e mostra o modal "PJeOffice Indisponível".

### 3.3 O que onSucesso() faz (capturado em sessão anterior)

```javascript
// onSucesso() dispara A4J.AJAX.Submit:
A4J.AJAX.Submit('j_id312', event, {
    similarityGroupingId: 'j_id312:j_id313',
    parameters: { 'j_id312:j_id313': 'j_id312:j_id313' }
});
```

Isso faz POST para `peticaoPopUp.seam` que sinaliza ao servidor que o PJeOffice concluiu a assinatura. O servidor então finaliza o peticionamento.

---

## 4. Execução: curl → PJeOffice → Resultado

### 4.1 Envio via curl

Após capturar a URL com o Interceptor V3, enviamos diretamente via curl (HTTP puro, sem restrição de Mixed Content do browser):

```bash
curl -s \
  -o /tmp/pjeoffice_sign_response.bin \
  -w "HTTP=%{http_code} SIZE=%{size_download} TIME=%{time_total}" \
  --max-time 120 \
  "http://localhost:8800/pjeOffice/requisicao/?r=<URL_CAPTURADA_COMPLETA>"
```

### 4.2 Resultado do curl

```
HTTP=200  SIZE=43  TIME=9.671103
```

| Métrica | Valor | Significado |
|---------|-------|-------------|
| HTTP Code | `200` | PJeOffice processou a requisição |
| Size | `43 bytes` | Imagem GIF |
| Time | `9.67 segundos` | Tempo que o PJeOffice levou para assinar e fazer upload (APARECEU PRO USUARIOP digitar a senha 22051998 pra desbloquear por isso demoriu tanto|

### 4.3 Verificação da Imagem de Resposta

```python
from PIL import Image
import io

data = open('/tmp/pjeoffice_sign_response.bin', 'rb').read()
img = Image.open(io.BytesIO(data))
print(f'{img.size[0]}x{img.size[1]} {img.format}')
# Resultado: "1x1 GIF"
```

**43 bytes = GIF 1x1 pixel = SUCESSO** ✅

| Tamanho GIF | Dimensões | Significado |
|-------------|-----------|-------------|
| 43 bytes | 1×1 pixel | **SUCESSO** — PJeOffice assinou e fez upload com sucesso |
| ~90 bytes | 2×1 pixel (PNG) | **ERRO** — PJeOffice falhou na assinatura ou upload |

---

## 5. Resposta Injetada → Sucesso no PJe

### 5.1 Injeção da Resposta

Após confirmar GIF 1x1 (sucesso), injetamos a resposta de volta na página:

```javascript
// window.__pjeoffice_respond(index, width, height)
window.__pjeoffice_respond(0, 1, 1);
```

Isso faz internamente:
1. Cria `<canvas>` 1×1 pixel
2. Define `img.width = 1` e `img.height = 1` via `Object.defineProperty`
3. Seta `img.src = canvas.toDataURL('image/gif')` — dispara `onload`
4. PJe JS verifica `this.width == 2` → **NÃO** (é 1) → chama `onSucesso()`
5. `onSucesso()` → `A4J.AJAX.Submit` → POST para servidor

### 5.2 Resultado na Página (capturado via browser snapshot)

Após a injeção, a página mostrou:

```
✅ "Documento(s) assinado(s) com sucesso."
✅ "O peticionamento foi concluído com sucesso"
```

**A petição foi protocolada com sucesso no PJe TRF1.** 🎉

---

## 6. Decompilação do PJeOffice Pro — POST Exato

### 6.1 Arquivos Decompilados

Decompilados com CFR 0.152 a partir de `/home/wital/jusMonitor/docs/pjeoffice-pro/pjeoffice-pro.jar`:

| Classe Java | Localização | Função |
|-------------|-------------|--------|
| `PjeWebClient` | `.../core/imp/PjeWebClient.class` | **Constrói e envia os HTTP POSTs** |
| `PjeBase64SignerTask` | `.../task/imp/PjeBase64SignerTask.class` | **Orquestra a assinatura de documentos** |
| `SignedOutputDocument` | `.../task/imp/TarefaAssinadorBase64Reader$SignedOutputDocument.class` | **POJO com hashDoc + assinaturaBase64** |
| `InputDocument64` | `.../task/imp/TarefaAssinadorBase64Reader$InputDocument64.class` | **POJO de entrada: hashDoc + conteudoBase64** |
| `SignedURLDocument` | `.../task/imp/SignedURLDocument.class` | **Doc assinado para upload multipart** |
| `URLDocument` | `.../task/imp/URLDocument.class` | **Wrapper de documento com URL** |

### 6.2 PjeWebClient.java — Os 5 Formatos de POST

```java
class PjeWebClient extends PjeClient<HttpPost> {

    // ═══ FORMATO 1: Form-encoded — assinatura + cadeiaCertificado ═══
    // Usado por: send(endpoint, signedData) → verificação getIfError()
    @Override
    protected HttpPost createOutput(IPjeEndpoint endpoint, ISignedData signedData) {
        HttpPost post = createPost(endpoint);
        post.setEntity(new UrlEncodedFormEntity(Arrays.asList(
            new BasicNameValuePair("assinatura", signedData.getSignature64()),
            new BasicNameValuePair("cadeiaCertificado", signedData.getCertificateChain64())
        )));
        return post;
    }

    // ═══ FORMATO 2: Form-encoded — assinatura + cadeia + campos doc (giveBack) ═══
    // Usado por: send(endpoint, signedData, document) → verificação getIfNotSuccess()
    @Override
    protected HttpPost createOutput(IPjeEndpoint endpoint, ISignedData signedData, 
                                     IOutputDocument document) {
        HttpPost post = createPost(endpoint);
        List<BasicNameValuePair> parameters = new ArrayList<>();
        parameters.add(new BasicNameValuePair("assinatura", signedData.getSignature64()));
        parameters.add(new BasicNameValuePair("cadeiaCertificado", signedData.getCertificateChain64()));
        // giveBack() adiciona pares chave-valor extras do documento
        // Para SignedOutputDocument: ("hashDoc", hash) e ("assinaturaBase64", sig)
        document.giveBack(nv -> parameters.add(new BasicNameValuePair(nv.getKey(), nv.getValue())));
        post.setEntity(new UrlEncodedFormEntity(parameters));
        return post;
    }

    // ═══ FORMATO 3: Multipart — arquivo binário assinado ═══
    // Usado por: send(endpoint, file, contentType) → verificação getIfNotSuccess()
    @Override
    protected HttpPost createOutput(IPjeEndpoint endpoint, ISignableURLDocument file, 
                                     IContentType contentType) {
        byte[] signature = file.getSignedData().orElseThrow(FileNotSignedException::new).getSignature();
        MultipartEntityBuilder builder = MultipartEntityBuilder.create();
        builder.addPart(
            file.getSignatureFieldName(), // campo dinâmico = "nomeDoCampoDoArquivo" do documento
            new ByteArrayBody(signature, 
                ContentType.create(contentType.getMineType(), contentType.getCharset()),
                file.getNome().orElse("arquivo") + contentType.getExtension())
        );
        // giveBack() adiciona StringBody extras
        file.giveBack(nv -> builder.addPart(nv.getKey(), new StringBody(nv.getValue(), ContentType.TEXT_PLAIN)));
        HttpPost post = createPost(endpoint);
        post.setEntity(builder.build());
        return post;
    }

    // ═══ FORMATO 4: Form-encoded — só cadeiaDeCertificadosBase64 ═══
    // Usado por: send(endpoint, certificateChain64)
    @Override
    protected HttpPost createOutput(IPjeEndpoint endpoint, String certificateChain64) {
        HttpPost post = createPost(endpoint);
        post.setEntity(new UrlEncodedFormEntity(Arrays.asList(
            new BasicNameValuePair("cadeiaDeCertificadosBase64", certificateChain64)
        )));
        return post;
    }

    // ═══ FORMATO 5: JSON — objeto POJO serializado ═══
    // Usado por: send(endpoint, Object pojo) ← ESTE É O USADO POR cnj.assinadorHash!
    @Override
    protected HttpPost createOutput(IPjeEndpoint endpoint, Object pojo) {
        HttpPost post = createPost(endpoint);
        post.setHeader("Accept", ContentType.APPLICATION_JSON.getMimeType());
        post.setEntity(new StringEntity(Objects.toJson(pojo), ContentType.APPLICATION_JSON));
        return post;
    }
}
```

### 6.3 Verificação de Resposta do Servidor

```java
// O servidor DEVE responder com texto começando com "Sucesso"
// Se responder com "Erro:..." → PjeClientException
// Se NÃO começar com "Sucesso" → PjeClientException

static final String SERVER_SUCCESS_RESPONSE = "Sucesso";
static final String SERVER_FAIL_RESPONSE = "Erro:";

// THROW_IF_ERROR: verifica se começa com "Erro:"
// THROW_IF_NOT_SUCCESS: verifica se começa com "Sucesso" (mais restritivo)
```

---

## 7. Comparação: Login vs Assinatura

| Campo | Login (`sso.autenticador`) | Assinatura (`cnj.assinadorHash`) |
|-------|---------------------------|----------------------------------|
| `tarefaId` | `sso.autenticador` | `cnj.assinadorHash` |
| `servidor` | `https://sso.cloud.pje.jus.br/auth/realms/pje` | `https://pje1g.trf1.jus.br/pje` |
| `sessao` | Cookies do SSO Keycloak | Cookies do PJe (JSESSIONID + KEYCLOAK_IDENTITY) |
| `tarefa.mensagem` | Random float nonce (`"0.60815471443755"`) | ❌ **NÃO EXISTE** |
| `tarefa.enviarPara` | `/pjeoffice-rest` | ❌ **NÃO EXISTE** |
| `tarefa.token` | UUID do SSO | ❌ **NÃO EXISTE** |
| `tarefa.uploadUrl` | ❌ **NÃO EXISTE** | `/arquivoAssinadoUpload.seam?action=...&cid=...&mo=P` |
| `tarefa.arquivos` | ❌ **NÃO EXISTE** | `[{id, codIni, hash, isBin}]` |
| `tarefa.algoritmoAssinatura` | ❌ **NÃO EXISTE** | `ASN1MD5withRSA` |
| `tarefa.modoTeste` | ❌ **NÃO EXISTE** | `"false"` |
| O que PJeOffice faz | Assina nonce → POST JSON ao SSO `/pjeoffice-rest` | Assina doc → POST ao PJe `uploadUrl` |
| Endpoint de POST | `https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest` | `https://pje1g.trf1.jus.br/pje/arquivoAssinadoUpload.seam?...` |
| Tempo resposta | ~18-22s (pede senha certificado) | ~9.7s (senha já cacheada mas pedou novamnete o usuario digitou) |
| GIF retorno | 1×1 = sucesso | 1×1 = sucesso |

---

## 8. O que o PJeOffice Faz Internamente

### 8.1 Fluxo Interno para cnj.assinadorHash (Decompilado — CORRIGIDO)

> **NOTA:** A análise anterior estava baseada em `PjeBase64SignerTask` (handler errado).  
> O handler CORRETO é `PjeHashSigningTask` — confirmado pela decompilação profunda.

```
PJeOffice Pro recebe GET http://localhost:8800/pjeOffice/requisicao/?r={payload}
  │
  ├── 1. Decodifica JSON do parâmetro `r`
  ├── 2. Verifica `codigoSeguranca` (RSA encrypted) para autenticidade
  ├── 3. Identifica tarefaId = "cnj.assinadorHash"
  ├── 4. Cria PjeHashSigningTask (NÃO PjeBase64SignerTask!)
  │     └── TarefaAssinadorHashReader → PjeHashSigningTask
  │
  ├── 5. Para cada arquivo em tarefa.arquivos:
  │     ├── 5a. HashedOutputDocument wraps HashMap<String,String> do JSON
  │     ├── 5b. Extrai hash via getHash() → json.get("hash")
  │     ├── 5c. hashToBytes(hash): hex string → 16 raw bytes
  │     ├── 5d. signer.process(hashBytes):
  │     │         ASN1MD5withRSA → TWOSTEPSwithRSA:
  │     │         1. Construir ASN.1 DigestInfo (MD5 OID + 16 bytes)
  │     │         2. PKCS#1 v1.5 padding
  │     │         3. RSA encrypt com chave privada
  │     │         NÃO re-hash! Input já é o MD5 do documento.
  │     └── 5e. Resultado: ISignedData com signature[] e certChain
  │
  ├── 6. Envia ao servidor (PjeWebClient FORMAT 2 — form-encoded):
  │     client.send(target, signedData, (IOutputDocument)document)
  │     ↓ createOutput(endpoint, signedData, document):
  │     ↓ POST form-encoded:
  │        Content-Type: application/x-www-form-urlencoded
  │        Body:
  │          assinatura=<base64_sig>
  │          &cadeiaCertificado=<base64_PKIPath>
  │          &id=2241101138         ← giveBack()
  │          &codIni=100131276      ← giveBack()
  │          &hash=eeb510b8...      ← giveBack()
  │          &isBin=true            ← giveBack()
  │     ↓ Verifica resposta começa com "Sucesso"
  │
  └── 7. Retorna GIF:
        ├── 1×1 pixel → SUCESSO
        └── 2×1 pixel → ERRO
```

### 8.2 RESOLUÇÃO: PjeHashSigningTask (NÃO PjeBase64SignerTask!)

A análise anterior estava errada — usava a classe errada. A decompilação profunda revelou:

| Classe Errada | Classe Correta |
|---------------|----------------|
| `PjeBase64SignerTask` | **`PjeHashSigningTask`** |
| Usa `conteudoBase64` (obrigatório) | Usa apenas `hash` (hex string) |
| Assina bytes completos do doc | Assina 16 bytes do hash |
| POST JSON (FORMAT 5) | POST form-encoded (FORMAT 2) |
| `SignedOutputDocument.giveBack()` | `HashedOutputDocument.giveBack()` → ALL fields |

**Por que o PJeOffice Pro funcionou SEM `conteudoBase64`:** Porque `PjeHashSigningTask` não precisa! Ele assina apenas os 16 bytes do hash via `hashToBytes(hash)`.

Classes decompiladas (PJeOffice Pro):
- `PjeHashSigningTask` — orquestra assinatura de hash (10364 bytes)
- `TarefaAssinadorHashReader` — converte JSON → POJOs
- `TarefaAssinadorHashReader$HashedOutputDocument` — implementa giveBack(ALL fields)
- `TarefaAssinadorHashReader$TarefaAssinadorHash` — reads `arquivos` como `List<HashMap<String,String>>`

---

## 9. Formato do POST para uploadUrl — CONFIRMADO DEFINITIVAMENTE

### 9.1 Formato CORRETO: FORMAT 2 (form-encoded) — PjeHashSigningTask

O `PjeHashSigningTask.doGet()` chama:
```java
response = this.withClient(c -> c.send(target, signedData, (IOutputDocument)document));
```

Isso usa **3 argumentos** → vai para `PjeWebClient.createOutput(endpoint, signedData, document)` → **FORMAT 2**:

```java
protected HttpPost createOutput(IPjeEndpoint endpoint, ISignedData signedData, IOutputDocument document) {
    List<BasicNameValuePair> parameters = new ArrayList<>();
    parameters.add(new BasicNameValuePair("assinatura", signedData.getSignature64()));
    parameters.add(new BasicNameValuePair("cadeiaCertificado", signedData.getCertificateChain64()));
    document.giveBack((name, value) -> parameters.add(new BasicNameValuePair(name, value)));
    post.setEntity(new UrlEncodedFormEntity(parameters));
}
```

### 9.2 POST Resultante

```
POST https://pje1g.trf1.jus.br/pje/arquivoAssinadoUpload.seam?action=peticionamentoAction&cid=296527&mo=P
Content-Type: application/x-www-form-urlencoded
Cookie: JSESSIONID=...; KEYCLOAK_IDENTITY=...; ...

assinatura=<base64_sig>&cadeiaCertificado=<base64_PKIPath>&id=2241101138&codIni=100131276&hash=eeb510b8bbd9e663b0501dd47937b543&isBin=true
```

### 9.3 HashedOutputDocument — giveBack() envia TUDO

```java
static final class HashedOutputDocument extends OutputDocument implements IHashedOutputDocument {
    private Map<String, String> json = new HashMap<>();  // TODOS os campos do JSON!
    
    @Override
    protected final void giveBack(BiConsumer<String, String> consumer) {
        this.json.forEach(consumer);  // ← ENVIA TUDO: id, codIni, hash, isBin
    }
}
```

### 9.4 Resposta Esperada do Servidor

| Resposta | Significado |
|----------|-------------|
| `"Sucesso"` ou `"Sucesso:..."` | ✅ Upload aceito |
| `"Erro:A assinatura do arquivo não foi fornecida!"` | ❌ Falta campo `assinatura` |
| `"Erro:A cadeia de certificado do signatário do arquivo não foi fornecida!"` | ❌ Falta `cadeiaCertificado` |
| `"Erro:O hash do arquivo assinado não foi fornecido!"` | ❌ Falta `id`/`codIni` ou `hash` |

---

## 10. Algoritmo de Assinatura — CONFIRMADO DEFINITIVAMENTE

### 10.1 ASN1MD5withRSA = Prehashed(MD5) + PKCS1v15

O campo `algoritmoAssinatura` da tarefa é `"ASN1MD5withRSA"`.

**Decompilação de `SignatureAlgorithm.java`:**
```java
ASN1MD5withRSA("ASN1MD5withRSA", HashAlgorithm.ASN1MD5)

// supportsTwoSteps() = true → usa TWOSTEPSwithRSA
// Significado: input é hash PRÉ-COMPUTADO, NÃO re-hash
```

**Decompilação de `PjeHashSigningTask.java`:**
```java
private static byte[] hashToBytes(String hash) {
    int mid = hash.length() / 2;
    byte[] b = new byte[mid];
    for (int i = 0; i < mid; ++i) {
        b[i] = (byte)(Integer.parseInt(hash.substring(i << 1, i + 1 << 1), 16) & 0xFF);
    }
    return b;
}

// Uso:
signedData = signer.process(hashToBytes(document.getHash()));
```

### 10.2 Em Python (cryptography) — CÓDIGO CORRETO

```python
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed

# hash_hex vem do payload: "eeb510b8bbd9e663b0501dd47937b543"
hash_bytes = bytes.fromhex(hash_hex)  # 16 bytes (MD5 pré-computado)

signature = private_key.sign(
    hash_bytes,
    padding.PKCS1v15(),
    Prehashed(hashes.MD5())  # NÃO re-hash! Input já é MD5 do documento
)

assinatura_base64 = base64.b64encode(signature).decode('ascii')
# len(signature) == 256 bytes para RSA 2048-bit key
```

### 10.3 O que Prehashed faz

| Sem Prehashed | Com Prehashed |
|---------------|---------------|
| `PKCS1v15() + MD5()` | `PKCS1v15() + Prehashed(MD5())` |
| Computa MD5(input) | Usa input diretamente como hash |
| Wraps em DigestInfo | Wraps em DigestInfo |
| PKCS#1 pad + RSA | PKCS#1 pad + RSA |
| Input: PDF bytes inteiro | Input: 16 bytes hex-decoded do hash |

### 10.4 Certificate Chain Format

```java
// CertificateAware.getCertificateChain64():
private static final String CERTIFICATION_CHAIN_ENCODING = "PkiPath";
// Certificates.toByteArray(chain):
return getFactory().generateCertPath(chain).getEncoded("PkiPath");
```

A cadeia de certificados é codificada como **PkiPath** (ASN.1 SEQUENCE OF Certificate) + base64.
Em Python: `base64.b64encode(_build_pkipath_der(cert_ders))` — já implementado no scraper.

# RSA PKCS#1 v1.5 raw (sem re-hash):
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
signature = private_key.sign(
    digest_info,
    padding.PKCS1v15(),
    Prehashed(hashes.MD5())  # ou usar raw RSA sem hash
)
```

**NOTA:** Esta é uma hipótese. Na sessão de captura, o PJeOffice Pro assinou com sucesso usando apenas `hash` (sem `conteudoBase64`), o que sugere que ele pode estar assinando o hash e NÃO os bytes completos do documento.

---

## 11. Erros do Servidor e Campos Obrigatórios

### 11.1 Erros Capturados em Sessões Anteriores (tentativa e erro)

| Tentativa | Formato | Campos | Resposta do Servidor |
|-----------|---------|--------|---------------------|
| 1 | JSON lista | `[{hashDoc, assinaturaBase64}]` | `"Erro:A assinatura do arquivo não foi fornecida!"` |
| 2 | JSON objeto | `{hashDoc, assinaturaBase64}` | `"Erro:A assinatura do arquivo não foi fornecida!"` |
| 3 | form-encoded | `assinatura` | `"Erro:A cadeia de certificado do signatário do arquivo não foi fornecida!"` |
| 4 | form-encoded | `assinatura` + `cadeiaCertificado` | `"Erro:O hash do arquivo assinado não foi fornecido!"` |
| 5 | form-encoded | `assinatura` + `cadeiaCertificado` + `hashDoc` | `"Erro:O hash do arquivo assinado não foi fornecido!"` |
| 6 | form-encoded | `assinatura` + `cadeiaCertificado` + `hash` | `"Erro:O hash do arquivo assinado não foi fornecido!"` |

### 11.2 Análise dos Erros — RESOLVIDO PELA DECOMPILAÇÃO PROFUNDA

**CAUSA RAIZ**: As tentativas 5 e 6 falharam porque enviavam APENAS `assinatura` + `cadeiaCertificado` + hash field. A decompilação de `PjeHashSigningTask` + `HashedOutputDocument.giveBack()` revelou que o PJeOffice envia **TODOS os campos** do JSON arquivo como form params!

**giveBack() envia:** `id`, `codIni`, `hash`, `isBin` — NÃO apenas `hash`!

O servidor provavelmente usa `id` ou `codIni` para localizar o documento e SÓ ENTÃO verifica o hash. Sem `id`/`codIni`, o servidor não sabe qual documento verificar → retorna "hash não fornecido".

**ALÉM DISSO**: a assinatura estava errada! O scraper assinava os bytes completos do PDF com MD5withRSA, mas o PJeOffice assina os **16 bytes do hash hex-decoded** com `Prehashed(MD5)` (DigestInfo wrapping sem re-hash).

### 11.3 POST Correto (Confirmado por Decompilação — PjeHashSigningTask + PjeWebClient FORMAT 2)

```
POST {servidor}/arquivoAssinadoUpload.seam?action=peticionamentoAction&cid=...&mo=P
Content-Type: application/x-www-form-urlencoded
Cookie: JSESSIONID=...; KEYCLOAK_IDENTITY=...; ...

assinatura=<base64_RSA_sig>&cadeiaCertificado=<base64_PKIPath>&id=2241101138&codIni=100131276&hash=eeb510b8bbd9e663b0501dd47937b543&isBin=true
```

---

## 12. Como Replicar Sem PJeOffice — IMPLEMENTADO

### 12.1 Abordagem V3 (CONFIRMADA FUNCIONANDO com PJeOffice real)

```
Playwright intercepta img.src → captura URL → curl envia pro PJeOffice → PJeOffice assina e POSTa → retorna GIF → injeta resposta
```

**PRÓS:** Funciona 100% — peticionamento confirmado com sucesso  
**CONTRAS:** Requer PJeOffice Pro rodando na máquina (Java GUI app com DISPLAY)

### 12.2 Abordagem Scraper (sem PJeOffice — IMPLEMENTADO)

```
Playwright intercepta img.src → extrai payload → Python assina HASH BYTES com Prehashed(MD5) + PKCS1v15 → Python faz POST form-encoded para uploadUrl com TODOS os campos do arquivo → injeta GIF 1x1 de volta
```

**Implementado em:** `scraper/app/scrapers/pje_peticionamento.py` → `_browser_sign_handler()`

**Detalhes confirmados por decompilação:**
1. ✅ `hash` é o campo correto (decompilado de `HashedOutputDocument.getHash()`)
2. ✅ ALL arquivo fields enviados como form params (decompilado de `giveBack()`)
3. ✅ Assinatura: `Prehashed(MD5())` sobre 16 bytes hex-decoded (decompilado de `PjeHashSigningTask.hashToBytes()`)
4. ✅ Cert chain: PkiPath base64 (decompilado de `Certificates.toByteArray()`)
5. ✅ POST format: form-encoded FORMAT 2 (decompilado de `PjeWebClient.createOutput()`)

### 12.3 Código de Referência para o Scraper

```python
import base64
import hashlib
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

async def sign_and_upload(
    page, private_key, certchain_b64, servidor, tarefa
):
    """CONFIRMADO POR DECOMPILAÇÃO DO PJEOFFICE PRO - Janeiro 2026"""
    from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
    from urllib.parse import urlencode
    
    upload_url_path = tarefa["uploadUrl"]
    full_url = servidor.rstrip("/") + upload_url_path
    
    for arquivo in tarefa["arquivos"]:
        hash_hex = arquivo["hash"]       # "eeb510b8bbd9e663b0501dd47937b543"
        
        # ══ ASSINATURA: PjeHashSigningTask.hashToBytes(hash) ══
        # Converte hex → bytes (16 bytes para MD5)
        # ASN1MD5withRSA = Prehashed(MD5) = DigestInfo wrapping sem re-hash
        hash_bytes = bytes.fromhex(hash_hex)
        
        signature = private_key.sign(
            hash_bytes,
            padding.PKCS1v15(),
            Prehashed(hashes.MD5())  # NÃO re-hash! Input já é MD5
        )
        sig_b64 = base64.b64encode(signature).decode("ascii")
        
        # ══ POST: PjeWebClient FORMAT 2 (form-encoded) ══
        # assinatura + cadeiaCertificado + TODOS os campos do arquivo (giveBack)
        form_params = {
            "assinatura": sig_b64,
            "cadeiaCertificado": certchain_b64,  # PKIPath base64
        }
        # HashedOutputDocument.giveBack() → envia TODOS os campos do JSON
        for key, val in arquivo.items():
            form_params[key] = str(val)
        # form_params agora tem: assinatura, cadeiaCertificado, id, codIni, hash, isBin
        
        form_data = urlencode(form_params)
        
        resp = await page.context.request.post(
            full_url,
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        body = (await resp.body()).decode("utf-8", errors="replace")
        
        if body.startswith("Sucesso") or not body.startswith("Erro:"):
            return True  # ✅
        else:
            print(f"Erro: {body}")
            return False
```

---

## 13. Referências e Arquivos

### 13.1 Arquivos de Certificado

| Arquivo | Caminho |
|---------|---------|
| PFX (A1) | `/home/wital/jusMonitor/docs/Amanda Alves de Sousa_07071649316.pfx` |
| Senha PFX | `22051998` |
| TOTP Secret | `MNFTCT2WKBJFKU3NGN2GYNKUJVDVKM3X` (SHA1, 6 dígitos, 30s) |

### 13.2 Arquivos PJeOffice Pro

| Arquivo | Caminho |
|---------|---------|
| JAR principal | `/home/wital/jusMonitor/docs/pjeoffice-pro/pjeoffice-pro.jar` |
| JRE bundled | `/home/wital/jusMonitor/docs/pjeoffice-pro/jre/bin/java` |
| Config | `/mnt/c/Users/wital/.pjeoffice-pro/pjeoffice-pro.config` |
| Classes decompiladas | `/tmp/pjeoffice_decompile/br/jus/cnj/pje/office/` |
| CFR decompiler | `/tmp/cfr.jar` |

### 13.3 Documentos Relacionados

| Documento | Caminho |
|-----------|---------|
| Interceptor V3 | `docs/INTERCEPTOR_V3_PJEOFFICE.md` |
| Peticionamento E2E | `docs/PETICIONAMENTO_AVULSO_E2E.md` |
| PJeOffice Setup | `docs/PJEOFFICE_SETUP.md` |
| PJeOffice Signing Flow | `docs/PJEOFFICE_SIGNING_FLOW.md` |
| PDF petição Eduardo | `docs/chamamento EDUARDO CAVALCANTE LEMOS (1).pdf` |

### 13.4 Processo de Teste

| Dado | Valor |
|------|-------|
| Processo | 1098298-53.2025.4.01.3400 |
| Parte | Eduardo Cavalcante Lemos |
| Tipo | MANDADO DE SEGURANÇA CÍVEL |
| Vara | 21ª Vara Federal Cível da SJDF |
| idProcesso | 13249143 |

### 13.5 Comando de Decompilação

```bash
JAVA=/home/wital/jusMonitor/docs/pjeoffice-pro/jre/bin/java

# Decompile uma classe:
$JAVA -jar /tmp/cfr.jar /tmp/pjeoffice_decompile/br/jus/cnj/pje/office/core/imp/PjeWebClient.class

# Decompile JAR completo:
$JAVA -jar /tmp/cfr.jar /home/wital/jusMonitor/docs/pjeoffice-pro/pjeoffice-pro.jar --methodname doGet
```

---

## Apêndice A — Payload de Login (sso.autenticador) para Comparação

```json
{
  "sessao": "KEYCLOAK_SESSION=pje/<user-uuid>/<session-uuid>; AWSALB=...; AWSALBCORS=...",
  "aplicacao": "PJe",
  "servidor": "https://sso.cloud.pje.jus.br/auth/realms/pje",
  "codigoSeguranca": "<RSA_ENCRYPTED_BASE64>",
  "tarefaId": "sso.autenticador",
  "tarefa": {
    "enviarPara": "/pjeoffice-rest",
    "mensagem": "0.60815471443755",
    "token": "5bfa97fb-b5a2-4769-9a2d-ecddad95200d"
  }
}
```

**POST que o PJeOffice faz para login:**
```
POST https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest
Content-Type: application/json

{
  "certChain": "<PKIPath_base64>",
  "uuid": "5bfa97fb-b5a2-4769-9a2d-ecddad95200d",
  "mensagem": "0.60815471443755",
  "assinatura": "<base64(RSA_MD5(mensagem))>"
}
→ HTTP 204 No Content (sucesso)
```

---

## Apêndice B — Interceptor V3 (Código JS Completo)

```javascript
(() => {
  window.__pjeoffice_queue = [];
  window.__pje_intercepted_full = [];
  var origDescriptor = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, 'src');

  Object.defineProperty(HTMLImageElement.prototype, 'src', {
    set: function(val) {
      if (val && typeof val === 'string' &&
          val.indexOf('localhost') !== -1 &&
          (val.indexOf('8800') !== -1 || val.indexOf('8801') !== -1)) {

        console.log('[PJeOffice-V3] Captured request - BLOCKED');
        var httpUrl = val.replace('https://', 'http://');
        var entry = {
          url: httpUrl, timestamp: Date.now(), img: this,
          decodedParams: null, onloadSrc: null, onerrorSrc: null
        };

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

        if (this.onload) entry.onloadSrc = this.onload.toString().substring(0, 3000);
        if (this.onerror) entry.onerrorSrc = this.onerror.toString().substring(0, 3000);

        window.__pjeoffice_queue.push(entry);
        window.__pje_intercepted_full.push({
          url: httpUrl, decodedParams: entry.decodedParams,
          onloadSrc: entry.onloadSrc, onerrorSrc: entry.onerrorSrc,
          ts: entry.timestamp
        });
        return; // *** BLOQUEIA — não seta src real ***
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
      Object.defineProperty(entry.img, 'width', { value: width, configurable: true });
      Object.defineProperty(entry.img, 'height', { value: height, configurable: true });
      origDescriptor.set.call(entry.img, canvas.toDataURL('image/gif'));
      console.log('[PJeOffice-V3] Response injected: ' + width + 'x' + height);
    }
  };
})();
```

---

## Apêndice C — Timeline da Sessão de Captura (2026-03-04)

| Hora (aprox) | Evento | Resultado |
|--------------|--------|-----------|
| T+0 | Navegar para `login.seam` | SSO Keycloak |
| T+1 | Instalar Interceptor V3 | OK |
| T+2 | Clicar "CERTIFICADO DIGITAL" | Capturado sso.autenticador |
| T+3 | curl → PJeOffice (login) | HTTP=200, 43 bytes, 19.4s, GIF 1×1 |
| T+4 | Injetar resposta + TOTP | Logado como "amanda sousa" |
| T+5 | Navegar para peticionamento avulso | OK |
| T+6 | Pesquisar processo Eduardo | Encontrado |
| T+7 | Abrir popup petição | peticaoPopUp.seam |
| T+8 | Selecionar "Arquivo PDF" + upload | PDF aceito |
| T+9 | Instalar Interceptor V3 (signing) | OK |
| T+10 | Clicar "Assinar documento(s)" | **CAPTURADO cnj.assinadorHash** |
| T+11 | curl → PJeOffice (signing) | **HTTP=200, 43 bytes, 9.67s, GIF 1×1** |
| T+12 | Injetar resposta (1×1) | onSucesso() → A4J.AJAX.Submit |
| T+13 | Resultado na página | **✅ "peticionamento foi concluído com sucesso"** |
