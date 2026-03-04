# PJeOffice Pro — Setup para Testes Locais

> **Importante:** O PJeOffice **NÃO é necessário em produção**. O scraper em produção usa `page.route()` para interceptar os requests `localhost:8800` diretamente em Python sem daemon local. O PJeOffice é usado apenas para **testes manuais** via browser real.

---

## O que é o PJeOffice

O PJeOffice Pro é um daemon Java que roda localmente e serve como ponte entre o browser (PJe) e o certificado digital (A1/A3). O PJe JavaScript faz requisições HTTP para `http://localhost:8800/pjeOffice/requisicao/?r=<challenge_json>` e o PJeOffice responde com a assinatura.

**Arquitetura:**
```
Browser PJe (HTTPS)
  → JS faz GET http://localhost:8800/pjeOffice/requisicao/?r={challenge}
  → PJeOffice (Java) assina com cert local
  → Resposta 200 OK → PJe protocolam
```

---

## Localização do Instalador

```
/home/wital/jusMonitor/docs/pjeoffice-pro/
├── pjeoffice-pro.sh        ← script de inicialização
├── app/
│   ├── PJeOffice.jar
│   └── ...
└── jre/                    ← JRE embutida (não precisa Java instalado)
```

---

## Como iniciar

### 1. Abrir servidor gráfico (WSL2)

O PJeOffice exige DISPLAY (interface gráfica para seleção de certificado):

**Opção A — VcXsrv (Windows X Server):**
```bash
# No Windows: abrir XLaunch → Multiple Windows → Display 0 → Next → clipboad + public access
export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0
```

**Opção B — Wayland nativo WSL2 (se disponível):**
```bash
export WAYLAND_DISPLAY=wayland-0
export DISPLAY=:0
```

**Verificar se DISPLAY está funcionando:**
```bash
DISPLAY=$DISPLAY xmessage "test" &   # deve abrir janela
```

### 2. Iniciar o PJeOffice

```bash
cd /home/wital/jusMonitor/docs/pjeoffice-pro
bash pjeoffice-pro.sh &
```

### 3. Aguardar as portas

```bash
# Aguardar portas HTTP (8800) e HTTPS (8801) ficarem ativas
watch -n1 "ss -tlnp | grep java"
# Deve mostrar: LISTEN *:8800 e *:8801
```

### 4. Verificar que está rodando

```bash
curl -s http://localhost:8800/pjeOffice/start -o /dev/null -w "%{http_code}"
# Esperado: 200 ou 204
```

---

## Mixed Content (aviso no browser)

Ao usar o browser em `https://pje1g.trf1.jus.br`, o JavaScript do PJe tenta chamar `http://localhost:8800` — isso dispara um aviso de **Mixed Content** porque HTTP está sendo chamado de dentro de uma página HTTPS.

**Chrome/Edge:** Bloqueia por padrão.  
**Correção para testes manuais:**
1. Clique no cadeado na barra de endereços
2. "Configurações do site" → Conteúdo inseguro → Permitir

Ou via flag:
```bash
google-chrome --allow-running-insecure-content https://pje1g.trf1.jus.br
```

> **Lembrete:** O scraper headless não tem esse problema — `page.route()` intercepta antes do browser enviar.

---

## Parar o PJeOffice

```bash
pkill -f PJeOffice.jar
# ou encontrar o PID:
ss -tlnp | grep 8800
kill <PID>
```

---

## PJeOffice NÃO é necessário em produção

Em produção (Docker), o scraper usa `page.route()` para interceptar `localhost:8800`:

```python
# scraper/app/scrapers/pje_peticionamento.py — _assinar_e_enviar()
async def _handle_pjeoffice_route(route, request):
    params = parse_qs(urlparse(request.url).query)
    r_data = json.loads(unquote(params["r"][0]))
    mensagem = json.loads(r_data["tarefa"])["mensagem"]
    assinatura = _sign_md5_rsa(private_key, mensagem)
    await page.context.request.post(
        "https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest",
        data=sign_payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    await route.fulfill(status=200, body="ok", content_type="text/plain")
```

O `page.route("http://localhost:8800/**")` captura o request antes de sair da rede — funciona mesmo em headless Chromium sem daemon.

---

## Troubleshooting

| Problema | Causa | Solução |
|----------|-------|---------|
| `ss -tlnp` não mostra 8800 | PJeOffice não iniciou | Verificar DISPLAY, retentar script |
| Janela PJeOffice não abre | DISPLAY inválido | `echo $DISPLAY` deve retornar `:0` ou `<IP>:0` |
| Modal "PJeOffice Indisponível" no browser | Mixed Content bloqueado | Permitir conteúdo inseguro na URL do PJe |
| `curl localhost:8800` retorna 403 | PJeOffice precisa de configuração de cert | Abrir PJeOffice GUI e selecionar cert A1 |
| Port 8800 em uso | Outro processo | `fuser -k 8800/tcp` |

---

## Certificado de Teste

```
Advogada:  Amanda Alves de Sousa
CPF:       07071649316
Arquivo:   /home/wital/jusMonitor/docs/Amanda Alves de Sousa_07071649316.pfx
Senha:     22051998
TOTP:      MNFTCT2WKBJFKU3NGN2GYNKUJVDVKM3X  (sha1, 6 digits, 30s)
```

**Gerar TOTP atual:**
```bash
python3 /home/wital/jusMonitor/scripts/totp_live.py
```
