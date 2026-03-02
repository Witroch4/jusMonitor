"""Quick E2E test for OAB scraper via backend API."""
import json
import urllib.request
import sys

API_URL = "http://localhost:8000/api/v1"
EMAIL = "witalo_rocha@hotmail.com"
PASSWORD = "W#@@%\u00a8&!B!!!UN<L="


def main():
    # Login
    data = json.dumps({"email": EMAIL, "password": PASSWORD}).encode()
    req = urllib.request.Request(
        f"{API_URL}/auth/login", data=data, headers={"Content-Type": "application/json"}
    )
    resp = urllib.request.urlopen(req)
    token = json.loads(resp.read().decode())["access_token"]
    print("LOGIN OK")

    # Consultar OAB
    oab_data = json.dumps({"oabNumero": "50784", "oabUf": "CE"}).encode()
    req2 = urllib.request.Request(
        f"{API_URL}/processos/consultar-oab",
        data=oab_data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        resp2 = urllib.request.urlopen(req2, timeout=600)
        result = json.loads(resp2.read().decode())
    except Exception as e:
        print(f"Error: {e}")
        if hasattr(e, "read"):
            print(e.read().decode()[:3000])
        sys.exit(1)

    # Summary
    print(f"Sucesso: {result['sucesso']}")
    print(f"Mensagem: {result['mensagem']}")
    print(f"Total: {result['total']}")
    print(f"Processos retornados: {len(result['processos'])}")
    print()

    for i, p in enumerate(result["processos"]):
        print(f"  [{i+1}] {p['numero']} | {p.get('classe', '?')} | {p.get('assunto', '?')}")
        print(
            f"      Partes: {len(p.get('partes_detalhadas', []))} | "
            f"Movs: {len(p.get('movimentacoes', []))} | "
            f"Docs: {len(p.get('documentos', []))}"
        )

    # Full JSON of first process
    if result["processos"]:
        print()
        print("=== PRIMEIRO PROCESSO (JSON) ===")
        print(json.dumps(result["processos"][0], indent=2, ensure_ascii=False)[:5000])


if __name__ == "__main__":
    main()
