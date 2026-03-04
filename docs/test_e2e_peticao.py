#!/usr/bin/env python3
"""
Teste E2E: petição avulsa real via scraper container.
Roda dentro do container: docker exec jusmonitoria-scraper python3 /app/shared-docs/../test_e2e.py
"""
import base64
import json
import urllib.request
import urllib.error
import sys

# ── Configurações ──
PFX_PATH  = "/app/shared-docs/Amanda Alves de Sousa_07071649316.pfx"
PDF_PATH  = "/app/shared-docs/eduardo_peticao.pdf"
PFX_PASS  = "22051998"
TOTP_SECRET = "MNFTCT2WKBJFKU3NGN2GYNKUJVDVKM3X"
PROCESSO  = "1098298-53.2025.4.01.3400"
TRIBUNAL  = "trf1"
TIPO      = "peticao_principal"
DESCRICAO = "Chamamento"
SCRAPER_URL = "http://localhost:8001/scrape/protocolar-peticao"

def encode_file(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def main():
    print(f"[E2E] Lendo PFX: {PFX_PATH}")
    pfx_b64 = encode_file(PFX_PATH)
    print(f"[E2E] PFX: {len(pfx_b64)} chars base64")

    print(f"[E2E] Lendo PDF: {PDF_PATH}")
    pdf_b64 = encode_file(PDF_PATH)
    print(f"[E2E] PDF: {len(pdf_b64)} chars base64")

    payload = {
        "tribunal": TRIBUNAL,
        "numero_processo": PROCESSO,
        "pfx_base64": pfx_b64,
        "pfx_password": PFX_PASS,
        "pdf_base64": pdf_b64,
        "totp_secret": TOTP_SECRET,
        "tipo_documento": TIPO,
        "descricao": DESCRICAO,
    }

    data = json.dumps(payload).encode()
    print(f"\n[E2E] POST {SCRAPER_URL}")
    print(f"[E2E] processo={PROCESSO} tipo={TIPO}")

    req = urllib.request.Request(
        SCRAPER_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = resp.read().decode()
            print(f"\n[E2E] HTTP {resp.status}")
            result = json.loads(body)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            if result.get("sucesso"):
                print("\n✅ SUCESSO!")
                protocolo = result.get("numero_protocolo")
                if protocolo:
                    print(f"   Protocolo: {protocolo}")
                else:
                    print("   Petição avulsa enviada (sem número de protocolo)")
            else:
                print(f"\n❌ FALHOU: {result.get('mensagem', 'sem mensagem')}")
                sys.exit(1)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"\n[E2E] HTTP {e.code}: {body[:500]}")
        sys.exit(1)
    except Exception as e:
        print(f"[E2E] Erro: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
