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
TOTP_SECRET = "MNFTCT2WKBJFKU3NGN2GYNKUJVDVKM3X"


def _make_test_pdf() -> bytes:
    """Create a proper test PDF with real content that PJe will accept."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        import io
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        c.setFont("Helvetica", 12)
        c.drawString(72, 750, "TESTE AUTOMATIZADO DE PETICIONAMENTO")
        c.drawString(72, 730, "Este documento e um teste do sistema JusMonitorIA.")
        c.drawString(72, 710, "NAO PROTOCOLAR - Apenas verificacao do fluxo.")
        c.save()
        return buf.getvalue()
    except ImportError:
        # Fallback: build a more complete PDF manually
        content = (
            "BT\n"
            "/F1 12 Tf\n"
            "72 750 Td\n"
            "(TESTE AUTOMATIZADO DE PETICIONAMENTO) Tj\n"
            "0 -20 Td\n"
            "(Este documento e um teste do sistema JusMonitorIA.) Tj\n"
            "0 -20 Td\n"
            "(NAO PROTOCOLAR - Apenas verificacao do fluxo.) Tj\n"
            "ET\n"
        )
        stream_len = len(content)
        pdf = (
            "%PDF-1.4\n"
            "1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            "2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            f"3 0 obj<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R"
            f"/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj\n"
            "4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
            f"5 0 obj<</Length {stream_len}>>stream\n"
            f"{content}"
            "endstream\nendobj\n"
        )
        # Build xref
        lines = pdf.encode('latin-1')
        xref_offset = len(lines)
        xref = (
            "xref\n0 6\n"
            "0000000000 65535 f \n"
        )
        # Just use approximate offsets
        offsets = []
        pos = 0
        for i in range(1, 6):
            idx = pdf.find(f"{i} 0 obj")
            offsets.append(idx)
            xref += f"{idx:010d} 00000 n \n"

        xref += (
            f"trailer<</Size 6/Root 1 0 R>>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        )
        return (pdf + xref).encode('latin-1')


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
    pdf_bytes = _make_test_pdf()
    pdf_b64 = base64.b64encode(pdf_bytes).decode()

    logger.info("PFX: %d bytes → b64: %d chars | PDF: %d bytes", len(pfx_bytes), len(pfx_b64), len(pdf_bytes))

    # Importar a função alvo
    from app.scrapers.pje_peticionamento import protocolar_peticao_pje

    logger.info("Iniciando protocolar_peticao_pje()...")
    result = await protocolar_peticao_pje(
        tribunal_code=TRIBUNAL,
        numero_processo=PROCESSO,
        pfx_base64=pfx_b64,
        pfx_password=PFX_PASSWORD,
        pdf_base64=pdf_b64,
        tipo_documento="Petição intercorrente",
        descricao="TESTE AUTOMATIZADO — NÃO PROTOCOLAR",
        totp_secret=TOTP_SECRET,
        totp_algorithm="SHA1",
        totp_digits=6,
        totp_period=30,
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
