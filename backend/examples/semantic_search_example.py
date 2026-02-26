"""
Example demonstrating the complete embeddings and semantic search workflow.

This example shows:
1. Creating case movements
2. Generating embeddings asynchronously
3. Performing semantic searches
4. Finding similar cases
"""

import asyncio
from datetime import date
from uuid import uuid4

from app.config import settings
from app.core.services.search.semantic import SemanticSearchService
from app.db.engine import get_session
from app.db.models.case_movement import CaseMovement
from app.db.models.legal_case import LegalCase
from app.db.models.tenant import Tenant
from app.workers.tasks.embeddings import (
    generate_case_movement_embeddings,
    batch_generate_embeddings_for_tenant,
)


async def create_sample_data():
    """Create sample tenant, case, and movements."""
    
    async with get_session() as session:
        # Create tenant
        tenant = Tenant(
            name="Example Law Firm",
            slug="example-firm",
            settings={},
        )
        session.add(tenant)
        await session.flush()
        
        # Create legal case
        legal_case = LegalCase(
            tenant_id=tenant.id,
            cnj_number="0000001-00.2024.8.00.0001",
            court="Tribunal de Justiça de São Paulo",
            case_type="Ação de Indenização",
            subject="Danos Morais",
            status="active",
            plaintiff="João da Silva",
            defendant="Empresa XYZ Ltda",
            monitoring_enabled=True,
        )
        session.add(legal_case)
        await session.flush()
        
        # Create sample movements
        movements_data = [
            {
                "date": date(2024, 1, 15),
                "type": "Sentença",
                "description": "Sentença de procedência. Julgo procedente o pedido para condenar a ré ao pagamento de indenização por danos morais no valor de R$ 10.000,00.",
            },
            {
                "date": date(2024, 1, 10),
                "type": "Audiência",
                "description": "Realizada audiência de instrução e julgamento. Ouvidas as testemunhas arroladas pelas partes.",
            },
            {
                "date": date(2024, 1, 5),
                "type": "Contestação",
                "description": "Apresentada contestação pela parte ré, alegando ausência de responsabilidade pelos danos alegados.",
            },
            {
                "date": date(2024, 1, 1),
                "type": "Petição Inicial",
                "description": "Distribuída ação de indenização por danos morais. Autor alega ter sofrido constrangimento em estabelecimento comercial.",
            },
        ]
        
        movements = []
        for i, data in enumerate(movements_data):
            movement = CaseMovement(
                tenant_id=tenant.id,
                legal_case_id=legal_case.id,
                movement_date=data["date"],
                movement_type=data["type"],
                description=data["description"],
                content_hash=f"hash_{i}",
            )
            session.add(movement)
            movements.append(movement)
        
        await session.commit()
        
        print(f"✓ Created tenant: {tenant.name}")
        print(f"✓ Created case: {legal_case.cnj_number}")
        print(f"✓ Created {len(movements)} movements")
        
        return tenant, legal_case, movements


async def generate_embeddings_example(tenant, movements):
    """Generate embeddings for movements."""
    
    print("\n--- Generating Embeddings ---")
    
    movement_ids = [str(m.id) for m in movements]
    
    # Option 1: Generate embeddings for specific movements
    print(f"Generating embeddings for {len(movement_ids)} movements...")
    
    result = await generate_case_movement_embeddings.kiq(
        tenant_id=str(tenant.id),
        movement_ids=movement_ids,
    )
    
    # Wait for task to complete
    task_result = await result.wait_result(timeout=30.0)
    
    if task_result.is_ok:
        data = task_result.return_value
        print(f"✓ Generated {data['processed']} embeddings")
        print(f"  Skipped: {data['skipped']}")
    else:
        print(f"✗ Error: {task_result.error}")
    
    # Option 2: Batch generate for entire tenant
    # Uncomment to use:
    # result = await batch_generate_embeddings_for_tenant.kiq(
    #     tenant_id=str(tenant.id),
    #     entity_type="movement",
    # )


async def search_movements_example(tenant):
    """Perform semantic searches on movements."""
    
    print("\n--- Semantic Search Examples ---")
    
    async with get_session() as session:
        search_service = SemanticSearchService(session)
        
        # Example 1: Search for favorable decisions
        print("\n1. Searching for 'sentença favorável'...")
        results = await search_service.search_case_movements(
            tenant_id=tenant.id,
            query="sentença favorável ao autor",
            limit=3,
            min_score=0.5,
        )
        
        for i, result in enumerate(results, 1):
            print(f"\n   Result {i} (score: {result.score:.3f}):")
            print(f"   Date: {result.entity.movement_date}")
            print(f"   Type: {result.entity.movement_type}")
            print(f"   Description: {result.entity.description[:100]}...")
        
        # Example 2: Search for hearings
        print("\n2. Searching for 'audiência'...")
        results = await search_service.search_case_movements(
            tenant_id=tenant.id,
            query="audiência de instrução",
            limit=3,
            min_score=0.5,
        )
        
        for i, result in enumerate(results, 1):
            print(f"\n   Result {i} (score: {result.score:.3f}):")
            print(f"   Date: {result.entity.movement_date}")
            print(f"   Type: {result.entity.movement_type}")
        
        # Example 3: Search with date filter
        print("\n3. Searching with date filter (January 2024)...")
        results = await search_service.search_case_movements(
            tenant_id=tenant.id,
            query="decisão judicial",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31),
            limit=5,
        )
        
        print(f"   Found {len(results)} results in January 2024")


async def find_similar_cases_example(tenant, legal_case):
    """Find cases similar to a reference case."""
    
    print("\n--- Finding Similar Cases ---")
    
    async with get_session() as session:
        search_service = SemanticSearchService(session)
        
        # Create another case for comparison
        similar_case = LegalCase(
            tenant_id=tenant.id,
            cnj_number="0000002-00.2024.8.00.0001",
            court="Tribunal de Justiça de São Paulo",
            case_type="Ação de Indenização",
            subject="Danos Morais",
            status="active",
            monitoring_enabled=True,
        )
        session.add(similar_case)
        
        # Add similar movement
        similar_movement = CaseMovement(
            tenant_id=tenant.id,
            legal_case_id=similar_case.id,
            movement_date=date(2024, 2, 1),
            movement_type="Sentença",
            description="Sentença de procedência parcial. Condenada a ré ao pagamento de indenização por danos morais.",
            content_hash="hash_similar",
        )
        session.add(similar_movement)
        await session.commit()
        
        # Generate embedding for the new movement
        await generate_case_movement_embeddings.kiq(
            tenant_id=str(tenant.id),
            movement_ids=[str(similar_movement.id)],
        )
        
        # Wait a bit for embedding generation
        await asyncio.sleep(2)
        
        # Find similar cases
        print(f"\nFinding cases similar to: {legal_case.cnj_number}")
        similar_cases = await search_service.find_similar_cases(
            tenant_id=tenant.id,
            reference_case_id=legal_case.id,
            limit=5,
            min_score=0.3,
        )
        
        if similar_cases:
            for case, score in similar_cases:
                print(f"\n   Similar case: {case.cnj_number}")
                print(f"   Similarity score: {score:.3f}")
                print(f"   Type: {case.case_type}")
        else:
            print("   No similar cases found (may need more data)")


async def main():
    """Run the complete example."""
    
    print("=" * 60)
    print("Semantic Search Example")
    print("=" * 60)
    
    # Step 1: Create sample data
    tenant, legal_case, movements = await create_sample_data()
    
    # Step 2: Generate embeddings
    await generate_embeddings_example(tenant, movements)
    
    # Wait for embeddings to be generated
    print("\nWaiting for embeddings to be processed...")
    await asyncio.sleep(3)
    
    # Step 3: Perform searches
    await search_movements_example(tenant)
    
    # Step 4: Find similar cases
    await find_similar_cases_example(tenant, legal_case)
    
    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    """
    Run this example:
    
    1. Ensure the database is running and migrations are applied
    2. Ensure Redis is running for Taskiq
    3. Start the Taskiq worker:
       taskiq worker app.workers.broker:broker
    4. Run this script:
       python examples/semantic_search_example.py
    """
    asyncio.run(main())
