# Peticionamento PJe TRF1 — Implementação via SSO Certificado A1

> **Data:** 03/03/2026
> **Status:** SSO funcional (HTTP 204 confirmado) — aguardando segredo TOTP para homologação completa
> **Arquivo principal:** `scraper/app/scrapers/pje_peticionamento.py`

---

## 1. Contexto e Problema

O MNI SOAP (`https://pje1g.trf1.jus.br/pje/intercomunicacao`) está **bloqueado por firewall** para acesso externo no TRF1. A alternativa foi automatizar o peticionamento via interface web usando Playwright (RPA).

O desafio central era a autenticação: o PJe TRF1 usa **Keycloak** com login por certificado digital A1, mediado pelo aplicativo desktop **PJeOffice** (porta `localhost:8800`). O backend não tem acesso a esse app local.

A solução foi reverter o protocolo do PJeOffice e replicá-lo programaticamente.

---

## 2. Descoberta do Protocolo SSO

### 2.1 Como o PJeOffice funciona

O botão "CERTIFICADO DIGITAL" na página de login do PJe aciona o seguinte fluxo via JavaScript:

```js
// onclick do botão #kc-pje-office:
autenticar('uuid-da-sessao', 'nonce-do-keycloak')
```

Internamente, o PJeOffice intercepta esse evento, assina o nonce com o certificado e faz um POST para:

```
POST https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest
Content-Type: application/json

{
  "certChain": "<PKIPath base64>",
  "uuid": "<codigoSeguranca da sessão>",
  "mensagem": "<nonce do Keycloak>",
  "assinatura": "<MD5withRSA base64>"
}
```

Se válido, o servidor retorna **HTTP 204** e registra a autenticação na sessão Keycloak. O formulário é então submetido com o campo `pjeoffice-code=uuid`.

### 2.2 Detalhes técnicos do protocolo

| Campo | Formato | Descrição |
|---|---|---|
| `certChain` | PKIPath DER → base64 | `ASN.1 SEQUENCE OF Certificate`, certificado folha primeiro |
| `uuid` | UUID v4 | Identificador da sessão SSO (campo `codigoSeguranca` do onclick) |
| `mensagem` | string float | Nonce gerado pelo Keycloak (ex: `"0.7135113776428498"`) |
| `assinatura` | base64 | Assinatura MD5withRSA PKCS#1v15 da `mensagem` com a chave privada do PFX |

### 2.3 PKIPath DER — formato exato

O signer4j (biblioteca usada pelo PJeOffice) codifica a cadeia assim:

```
30 <len> [DER do cert folha] [DER da CA intermediária] [DER da raiz]
```

Implementado em `_build_pkipath_der()`:

```python
def _build_pkipath_der(cert_ders: list) -> bytes:
    content = b"".join(cert_ders)
    n = len(content)
    if n < 0x80:    lb = bytes([n])
    elif n < 0x100: lb = bytes([0x81, n])
    else:           lb = bytes([0x82, n >> 8, n & 0xFF])
    return bytes([0x30]) + lb + content
```

---

## 3. Fluxo Completo de Autenticação

```
[1] GET https://pje1g.trf1.jus.br/pje/login.seam
        → redireciona para SSO Keycloak
        → extrai codigoSeguranca + mensagem do onclick do botão #kc-pje-office

[2] Assinar mensagem com certificado PFX (RAM)
        → MD5withRSA PKCS#1v15
        → base64 → campo "assinatura"

[3] Montar PKIPath DER da cadeia certificca
        → SEQUENCE OF [cert_folha, cert_ca, cert_raiz]
        → base64 → campo "certChain"

[4] POST pjeoffice-rest (com cookies da sessão Keycloak)
        → HTTP 204 = autenticação registrada no servidor SSO ✅

[5] Submeter formulário HTML via page.evaluate()
        → pjeoffice-code = uuid
        → login-pje-office = "CERTIFICADO DIGITAL"
        → form.submit()

[6] Aguardar redirect → pode cair em /login-actions?execution=a85574ce... (TOTP)
        → Se TOTP: gerar código com pyotp.TOTP(secret).now() e submeter
        → Se PJe: verificar presença de "expedientes", "localizar processo" etc.
```

---

## 4. Autenticação TOTP (2FA)

### 4.1 Descoberta

Após o certificado ser aceito, o Keycloak redireciona para uma segunda página de verificação TOTP:

```
URL: https://sso.cloud.pje.jus.br/auth/realms/pje/login-actions/authenticate
     ?execution=a85574ce-7134-42cb-b177-3147783607c5
     &client_id=pje-trf1-1g
```

O `execution=a85574ce-...` é fixo (step de TOTP do realm PJe).

### 4.2 Estrutura da página OTP

```html
<input type="text" name="otp" id="otp" autocomplete="one-time-code" />
<input type="submit" name="login" id="kc-login" value="Validar" />
```

Não há opção de pular ou desativar o TOTP pelo fluxo normal.

### 4.3 Como o código lida com isso

```python
otp_input = page.locator("input[name='otp'], input[id='otp']")
if await otp_input.count() > 0:
    if not totp_secret:
        return PeticionamentoResult(sucesso=False, mensagem="Login requer TOTP...")
    totp_code = pyotp.TOTP(totp_secret.strip().upper()).now()
    await otp_input.first.fill(totp_code)
    await submit_btn.first.click()
```

---

## 5. Arquitetura da Implementação

### 5.1 Camadas (de baixo para cima)

```
scraper/app/scrapers/pje_peticionamento.py
    └── protocolar_peticao_pje()          ← Playwright RPA, SSO, TOTP, upload

scraper/app/schemas.py
    └── ProtocolarPeticaoRequest          ← inclui totp_secret

scraper/app/main.py
    └── POST /scrape/protocolar-peticao   ← endpoint FastAPI do scraper

backend/app/core/services/scraper_client.py
    └── protocolar_via_scraper()          ← cliente HTTP para o scraper

backend/app/workers/tasks/peticao_protocolar.py
    └── protocolar_peticao_task()         ← worker Taskiq — extrai TOTP do cert

backend/app/db/models/certificado_digital.py
    └── CertificadoDigital.totp_secret_encrypted  ← coluna LargeBinary nullable

backend/app/api/v1/endpoints/certificados.py
    └── PATCH /certificados/{id}/totp     ← endpoint para configurar TOTP
```

### 5.2 Fluxo de dados do TOTP

```
Usuário configura via UI:
  PATCH /api/v1/certificados/{cert_id}/totp
  Body: {"totp_secret": "JBSWY3DPEHPK3PXP"}
        ↓ Fernet.encrypt(secret.encode())
        → salvo em certificados_digitais.totp_secret_encrypted

Ao protocolar petição:
  peticao_protocolar.py
    → Fernet.decrypt(cert.totp_secret_encrypted) → totp_secret_raw
    → protocolar_via_scraper(..., totp_secret=totp_secret_raw)
    → HTTP POST /scrape/protocolar-peticao com totp_secret no body
    → protocolar_peticao_pje(..., totp_secret=totp_secret_raw)
    → pyotp.TOTP(totp_secret_raw).now() → código de 6 dígitos
```

---

## 6. Helpers Implementados

Todos em `scraper/app/scrapers/pje_peticionamento.py` (linhas ~58–84):

```python
_build_pkipath_der(cert_ders: list[bytes]) -> bytes
    # ASN.1 SEQUENCE OF Certificate — formato PKIPath conforme signer4j

_get_certchain_b64(cert_obj, additional_certs) -> str
    # Wraps _build_pkipath_der, retorna base64 prontal para certChain

_sign_md5_rsa(private_key, mensagem: str) -> str
    # MD5withRSA PKCS1v15, retorna base64 da assinatura
```

---

## 7. Debug — Screenshots e Logs

### 7.1 Screenshots automáticas

A função `protocolar_peticao_pje()` tira screenshots em pontos críticos e salva em `/tmp/`:

| Arquivo | Momento |
|---|---|
| `pje_peticionamento_01_login_page_<ts>.png` | Página de login SSO após carregamento |
| `pje_peticionamento_02b_otp_page_<ts>.png` | Página TOTP detectada (quando aplicável) |
| `pje_peticionamento_03_pos_login_<ts>.png` | Depois do login (painel PJe ou falha) |
| `pje_peticionamento_04_processo_<ts>.png` | Após localizar o processo |
| `pje_peticionamento_05_juntar_<ts>.png` | Formulário "Juntar Petição" aberto |
| `pje_peticionamento_06_confirmacao_<ts>.png` | Confirmação de protocolo |

As screenshots também são retornadas na resposta da API como lista `screenshots`.

Para recuperar do container:
```bash
docker compose cp scraper:/tmp/pje_peticionamento_01_login_page_*.png ./debug/
# ou todos de uma vez:
docker compose exec scraper ls /tmp/pje_peticionamento_*.png
docker compose cp scraper:/tmp/ ./debug/
```

### 7.2 Logs estruturados

O tag de prefixo nos logs é `[PJE-PROTOCOLO-{TRIBUNAL}]`. Filtrar assim:

```bash
docker compose logs scraper --tail=200 | grep "PJE-PROTOCOLO"
```

Linhas importantes a observar:

```
PKIPath certChain preparado (3 certs, 9600 chars b64)   ← cadeia cert OK
pjeoffice-rest: HTTP 204                                 ← SSO aceito ✅
Página de TOTP detectada (URL=...execution=a85574ce...)  ← 2FA necessário
✓ Login OK                                               ← authenticated
```

### 7.3 Script de teste manual

```bash
# Rodar o script de teste no container do scraper
docker compose exec scraper python -m scripts.testar_peticionamento_v2

# Passar TOTP secret via variável de ambiente (editar o script):
# scraper/scripts/testar_peticionamento_v2.py → linha TOTP_SECRET = "..."
```

---

## 8. Configuração TOTP no Frontend

Para adicionar o TOTP de um advogado/certificado:

1. Acessar as configurações do certificado digital
2. Na app do autenticador (Google Authenticator, Authy etc), escolher "configurar conta manualmente"
3. Copiar o segredo base32 (ex: `JBSWY3DPEHPK3PXP`)
4. Chamar o endpoint:

```http
PATCH /api/v1/certificados/{cert_id}/totp
Authorization: Bearer <token>
Content-Type: application/json

{"totp_secret": "JBSWY3DPEHPK3PXP"}
```

Para remover:
```json
{"totp_secret": null}
```

O segredo é armazenado criptografado com Fernet no banco (coluna `totp_secret_encrypted`).

---

## 9. Falso Positivo Identificado e Descartado

Durante a investigação, um script `requests`-based mostrou a keyword `expedientes` na página após o login com certificado. Parecia um login bem-sucedido mas era um **falso positivo**:

- URL final ainda era `/login-actions?execution=...` (página de autenticação)
- HTTP 200 (não redirect para PJe)
- A palavra "expedientes" aparece nos links de navegação da **própria página de login** do SSO

A confirmação do login real usa as keywords:
```python
["expedientes", "localizar processo", "meu painel",
 "nova tarefa", "fila de tarefas", "avisos do sistema"]
```
combinada com verificação da URL (`pje1g.trf1.jus.br` e não `sso.cloud.pje.jus.br`).

---

## 10. Dependências Adicionadas

`scraper/pyproject.toml`:
```toml
pyotp = "^2.9.0"   # Geração de códigos TOTP para 2FA
```

---

## 11. Migração de Banco

```
backend/alembic/versions/68a38600a6bc_add_totp_secret_to_certificado_digital.py
```

Adiciona coluna `totp_secret_encrypted BYTEA NULL` à tabela `certificados_digitais`.

Aplicar (se necessário):
```bash
docker compose exec backend alembic upgrade head
```

---

## 12. Estado Atual e Próximos Passos

| Etapa | Status |
|---|---|
| SSO pjeoffice-rest HTTP 204 | ✅ Funcional |
| TOTP — detecção da página | ✅ Funcional |
| TOTP — envio do código via pyotp | ✅ Implementado (não testado com secret real) |
| Armazenamento do TOTP no certificado | ✅ Migração aplicada |
| Endpoint PATCH /certificados/{id}/totp | ✅ Disponível |
| Login completo → painel PJe | ⏳ Aguardando secret TOTP da Amanda |
| Navegação pós-login → localizar processo | ⏳ Pendente |
| Formulário "Juntar Petição" → upload PDF | ⏳ Pendente |
| Captura do número de protocolo | ⏳ Pendente |

O próximo passo é obter o segredo TOTP base32 do autenticador da advogada Amanda Alves de Sousa e chamar `PATCH /api/v1/certificados/{cert_id}/totp` para habilitar o fluxo completo.
