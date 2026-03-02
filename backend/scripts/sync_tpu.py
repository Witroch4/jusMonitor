#!/usr/bin/env python3
"""
Sync TPU data from CNJ.

Usage:
    python -m scripts.sync_tpu
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.core.services.tpu.cnj_client import CnjTpuClient
from app.db.engine import AsyncSessionLocal, close_db
from app.db.models.tpu import TpuClasse, TpuAssunto

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def upsert_classes(session, classes_data: list[dict]):
    """Upsert classes data."""
    if not classes_data:
        return 0

    logger.info(f"Upserting {len(classes_data)} classes in two passes to handle hierarchies...")
    
    existing_result = await session.execute(select(TpuClasse.codigo))
    valid_ids = {row[0] for row in existing_result}
    for item in classes_data:
        valid_ids.add(item.get("cod_item"))

    batch_size = 1000
    
    # PASS 1: Insert all without relationships
    inserted_count = 0
    for i in range(0, len(classes_data), batch_size):
        batch = classes_data[i:i + batch_size]
        
        values = []
        for item in batch:
            values.append({
                "codigo": item.get("cod_item"),
                "nome": item.get("nome"),
                "cod_item_pai": None,
                "glossario": item.get("descricao_glossario"),
                "sigla": item.get("sigla"),
                "natureza": item.get("natureza"),
                "polo_ativo": item.get("polo_ativo"),
                "polo_passivo": item.get("polo_passivo"),
            })
            
        stmt = insert(TpuClasse).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["codigo"],
            set_={
                "nome": stmt.excluded.nome,
                "glossario": stmt.excluded.glossario,
                "sigla": stmt.excluded.sigla,
                "natureza": stmt.excluded.natureza,
                "polo_ativo": stmt.excluded.polo_ativo,
                "polo_passivo": stmt.excluded.polo_passivo,
                "updated_at": func.now(),
            }
        )
        await session.execute(stmt)
        inserted_count += len(batch)
        logger.info(f"  Pass 1 (Base): Processed {inserted_count}/{len(classes_data)} classes")

    # PASS 2: Establish relationships
    inserted_count = 0
    for i in range(0, len(classes_data), batch_size):
        batch = classes_data[i:i + batch_size]
        
        values = []
        for item in batch:
            cod_pai = item.get("cod_item_pai")
            valid_cod_pai = cod_pai if cod_pai and cod_pai > 0 and cod_pai in valid_ids else None
            
            values.append({
                "codigo": item.get("cod_item"),
                "nome": item.get("nome"), 
                "cod_item_pai": valid_cod_pai,
            })
            
        stmt = insert(TpuClasse).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["codigo"],
            set_={
                "cod_item_pai": stmt.excluded.cod_item_pai,
            }
        )
        await session.execute(stmt)
        inserted_count += len(batch)
        logger.info(f"  Pass 2 (Hierarchy): Linked {inserted_count}/{len(classes_data)} classes")
        
    await session.commit()
    logger.info("Successfully upserted all classes.")
    return len(classes_data)


async def upsert_assuntos(session, assuntos_data: list[dict]):
    """Upsert assuntos data."""
    if not assuntos_data:
        return 0

    logger.info(f"Upserting {len(assuntos_data)} assuntos in two passes to handle hierarchies...")
    
    existing_result = await session.execute(select(TpuAssunto.codigo))
    valid_ids = {row[0] for row in existing_result}
    for item in assuntos_data:
        valid_ids.add(item.get("cod_item"))

    batch_size = 1000
    
    # PASS 1: Insert all without relationships
    inserted_count = 0
    for i in range(0, len(assuntos_data), batch_size):
        batch = assuntos_data[i:i + batch_size]
        
        values = []
        for item in batch:
            values.append({
                "codigo": item.get("cod_item"),
                "nome": item.get("nome"),
                "cod_item_pai": None,
                "glossario": item.get("descricao_glossario"),
                "artigo": item.get("artigo"),
            })
            
        stmt = insert(TpuAssunto).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["codigo"],
            set_={
                "nome": stmt.excluded.nome,
                "glossario": stmt.excluded.glossario,
                "artigo": stmt.excluded.artigo,
                "updated_at": func.now(),
            }
        )
        await session.execute(stmt)
        inserted_count += len(batch)
        logger.info(f"  Pass 1 (Base): Processed {inserted_count}/{len(assuntos_data)} assuntos")
        
    # PASS 2: Establish relationships
    inserted_count = 0
    for i in range(0, len(assuntos_data), batch_size):
        batch = assuntos_data[i:i + batch_size]
        
        values = []
        for item in batch:
            cod_pai = item.get("cod_item_pai")
            valid_cod_pai = cod_pai if cod_pai and cod_pai > 0 and cod_pai in valid_ids else None
            
            values.append({
                "codigo": item.get("cod_item"),
                "nome": item.get("nome"),
                "cod_item_pai": valid_cod_pai,
            })
            
        stmt = insert(TpuAssunto).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["codigo"],
            set_={
                "cod_item_pai": stmt.excluded.cod_item_pai,
            }
        )
        await session.execute(stmt)
        inserted_count += len(batch)
        logger.info(f"  Pass 2 (Hierarchy): Linked {inserted_count}/{len(assuntos_data)} assuntos")
        
    await session.commit()
    logger.info("Successfully upserted all assuntos.")
    return len(assuntos_data)


async def main():
    logger.info("=== Starting TPU Sync from CNJ ===")
    
    client = CnjTpuClient(timeout=120)  # 2 minutes timeout for large payloads
    
    try:
        # Download data
        logger.info("Downloading classes from CNJ...")
        classes_data = await client.get_classes()
        
        logger.info("Downloading assuntos from CNJ...")
        assuntos_data = await client.get_assuntos()
        
        logger.info("Connecting to database...")
        async with AsyncSessionLocal() as session:
            # Disable constraint checking temporarily during bulk import if needed
            # But PostgreSQL handles upserts reasonably if ordered, so we try ordered
            
            # 1. Upsert Classes
            await upsert_classes(session, classes_data)
            
            # 2. Upsert Assuntos
            await upsert_assuntos(session, assuntos_data)
            
        logger.info("=== TPU Sync Complete ===")
            
    except Exception as e:
        logger.error(f"Failed to sync TPU data: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
