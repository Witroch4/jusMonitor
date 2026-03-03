"""Testa o protocolar_peticao_pje() com o novo fluxo SSO (MD5withRSA + PKIPath).

Usa o certificado da Amanda para login no TRF1 e navega até o processo.
Não chega a protocolar de verdade — interrompe antes do envio final.
"""

import asyncio
import base64
import logging
import os
import sys

# Configura logging detalhado
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
# Silenciar loggers muito verbosos
for noisy in ["playwright", "asyncio", "urllib3", "httpx"]:
    logging.getLogger(noisy).setLevel(logging.WARNING)

logger = logging.getLogger("test_peticionamento_v2")


PFX_PATH = "/app/docs/Amanda Alves de Sousa_07071649316.pfx"
PFX_PASSWORD = "22051998"
TRIBUNAL = "trf1"
PROCESSO = "1000654-37.2026.4.01.3704"

# PDF mínimo válido para teste
MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f\n"
    b"0000000009 00000 n\n0000000052 00000 n\n0000000101 00000 n\n"
    b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n173\n%%EOF\n"
)


async def main():
    logger.info("=" * 60)
    logger.info("  TESTE PETICIONAMENTO v2 — SSO MD5withRSA + PKIPath DER")
    logger.info("=" * 60)

    # Ler certificado
    if not os.path.exists(PFX_PATH):
        logger.error("PFX não encontrado: %s", PFX_PATH)
        sys.exit(1)

    with open(PFX_PATH, "rb") as f:
        pfx_bytes = f.read()
    pfx_b64 = base64.b64encode(pfx_bytes).decode()
    pdf_b64 = base64.b64encode(MINIMAL_PDF).decode()

    logger.info("PFX: %d bytes → b64: %d chars", len(pfx_bytes), len(pfx_b64))

    # Importar a função alvo
    from app.scrapers.pje_peticionamento import protocolar_peticao_pje

    logger.info("Iniciando protocolar_peticao_pje()...")
    result = await protocolar_peticao_pje(
        tribunal_code=TRIBUNAL,
        numero_processo=PROCESSO,
        pfx_base64=pfx_b64,
        pfx_password=PFX_PASSWORD,
        pdf_base64=pdf_b64,
        tipo_documento="Petição",
        descricao="TESTE AUTOMATIZADO — NÃO PROTOCOLAR",
    )

    logger.info("=" * 60)
    logger.info("  RESULTADO:")
    logger.info("  sucesso=%s", result.sucesso)
    logger.info("  mensagem=%s", result.mensagem)
    logger.info("  protocolo=%s", result.numero_protocolo)
    logger.info("  screenshots=%s", result.screenshots)
    logger.info("=" * 60)

    return result.sucesso


if __name__ == "__main__":
    success = asyncio.run(main())
    print(f"\n{'✅ SUCESSO' if success else '❌ FALHOU'}")
    sys.exit(0 if success else 1)
