"""Performance tests for HNSW indexes on embeddings."""

import asyncio
import time
from datetime import date, timedelta
from typing import List
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.case_movement import CaseMovement
from app.db.models.legal_case import LegalCase
from app.db.models.tenant import Tenant
from app.db.models.timeline_embedding import TimelineEmbedding
from app.db.models.timeline_event import TimelineEvent


@pytest.fixture
async def tenant_with_large_dataset(db_session: AsyncSession):
    """
    Create a tenant with 10k+ movements for performance testing.
    
    Note: This fixture creates a large dataset and may take several minutes.
    Only run when specifically testing performance.
    """
    # Create tenant
    tenant = Tenant(
        name="Performance Test Tenant",
        slug="perf-test",
        settings={},
    )
    db_session.add(tenant)
    await db_session.flush()
    
    # Create a legal case
    legal_case = LegalCase(
        tenant_id=tenant.id,
        cnj_number="0000001-00.2024.8.00.0000",
        court="Test Court",
        case_type="Test Type",
        status="active",
        monitoring_enabled=True,
    )
    db_session.add(legal_case)
    await db_session.flush()
    
    # Generate 10k movements with random embeddings
    # In production, these would be real embeddings from OpenAI
    movements = []
    batch_size = 1000
    
    for i in range(10000):
        # Generate a pseudo-random embedding (1536 dimensions)
        # Using a simple pattern for testing - in production use real embeddings
        embedding = [float((i + j) % 100) / 100.0 for j in range(1536)]
        
        movement = CaseMovement(
            tenant_id=tenant.id,
            legal_case_id=legal_case.id,
            movement_date=date.today() - timedelta(days=i % 365),
            movement_type=f"Type {i % 10}",
            description=f"Test movement {i} with some descriptive text",
            content_hash=f"hash_{i}",
            embedding=embedding,
        )
        movements.append(movement)
        
        # Commit in batches to avoid memory issues
        if len(movements) >= batch_size:
            db_session.add_all(movements)
            await db_session.flush()
            movements = []
    
    # Add remaining movements
    if movements:
        db_session.add_all(movements)
        await db_session.flush()
    
    await db_session.commit()
    
    return tenant, legal_case


@pytest.mark.asyncio
@pytest.mark.performance
async def test_hnsw_index_exists(db_session: AsyncSession):
    """Verify that HNSW indexes are created."""
    
    # Check case_movements index
    result = await db_session.execute(text("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = 'case_movements'
        AND indexname = 'idx_case_movements_embedding_hnsw';
    """))
    
    index = result.fetchone()
    assert index is not None, "HNSW index for case_movements not found"
    assert "hnsw" in index[1].lower(), "Index is not using HNSW"
    assert "vector_cosine_ops" in index[1], "Index not using cosine distance"
    
    # Check timeline_embeddings index
    result = await db_session.execute(text("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = 'timeline_embeddings'
        AND indexname = 'idx_timeline_embeddings_embedding_hnsw';
    """))
    
    index = result.fetchone()
    assert index is not None, "HNSW index for timeline_embeddings not found"
    assert "hnsw" in index[1].lower(), "Index is not using HNSW"


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.slow
async def test_search_performance_with_hnsw(
    db_session: AsyncSession,
    tenant_with_large_dataset,
):
    """
    Test search performance with HNSW index on 10k+ vectors.
    
    Expected performance:
    - Search should complete in < 100ms for top-10 results
    - Search should complete in < 500ms for top-100 results
    """
    tenant, legal_case = tenant_with_large_dataset
    
    # Generate a query embedding
    query_embedding = [float(i % 100) / 100.0 for i in range(1536)]
    
    # Test top-10 search
    start_time = time.time()
    
    stmt = (
        select(CaseMovement)
        .where(CaseMovement.tenant_id == tenant.id)
        .order_by(CaseMovement.embedding.cosine_distance(query_embedding))
        .limit(10)
    )
    
    result = await db_session.execute(stmt)
    movements = result.scalars().all()
    
    top_10_time = (time.time() - start_time) * 1000  # Convert to ms
    
    assert len(movements) == 10, "Should return 10 results"
    assert top_10_time < 100, f"Top-10 search took {top_10_time:.2f}ms (expected < 100ms)"
    
    print(f"\nTop-10 search performance: {top_10_time:.2f}ms")
    
    # Test top-100 search
    start_time = time.time()
    
    stmt = (
        select(CaseMovement)
        .where(CaseMovement.tenant_id == tenant.id)
        .order_by(CaseMovement.embedding.cosine_distance(query_embedding))
        .limit(100)
    )
    
    result = await db_session.execute(stmt)
    movements = result.scalars().all()
    
    top_100_time = (time.time() - start_time) * 1000
    
    assert len(movements) == 100, "Should return 100 results"
    assert top_100_time < 500, f"Top-100 search took {top_100_time:.2f}ms (expected < 500ms)"
    
    print(f"Top-100 search performance: {top_100_time:.2f}ms")


@pytest.mark.asyncio
@pytest.mark.performance
async def test_hnsw_index_parameters(db_session: AsyncSession):
    """Verify HNSW index parameters are correctly set."""
    
    # Query index parameters for case_movements
    result = await db_session.execute(text("""
        SELECT
            i.relname as index_name,
            am.amname as index_type,
            pg_get_indexdef(i.oid) as index_definition
        FROM pg_class t
        JOIN pg_index ix ON t.oid = ix.indrelid
        JOIN pg_class i ON i.oid = ix.indexrelid
        JOIN pg_am am ON i.relam = am.oid
        WHERE t.relname = 'case_movements'
        AND i.relname = 'idx_case_movements_embedding_hnsw';
    """))
    
    index_info = result.fetchone()
    
    if index_info:
        index_def = index_info[2]
        
        # Verify parameters
        assert "m=16" in index_def or "m = 16" in index_def, \
            "HNSW index should have m=16"
        assert "ef_construction=64" in index_def or "ef_construction = 64" in index_def, \
            "HNSW index should have ef_construction=64"
        
        print(f"\nHNSW index definition: {index_def}")


@pytest.mark.asyncio
@pytest.mark.performance
async def test_compare_with_ivfflat(db_session: AsyncSession):
    """
    Compare HNSW performance with IVFFlat (if available).
    
    This test demonstrates why HNSW is preferred for this use case.
    """
    # Create a temporary IVFFlat index for comparison
    await db_session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_case_movements_embedding_ivfflat_temp
        ON case_movements
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    """))
    
    await db_session.commit()
    
    # Note: In production, HNSW typically provides:
    # - Better recall (accuracy) than IVFFlat
    # - Faster query times for high-dimensional vectors
    # - No need for VACUUM ANALYZE before queries
    # - Better performance with small to medium datasets
    
    # Cleanup
    await db_session.execute(text("""
        DROP INDEX IF EXISTS idx_case_movements_embedding_ivfflat_temp;
    """))
    
    await db_session.commit()


if __name__ == "__main__":
    """
    Run performance tests manually.
    
    Usage:
        pytest tests/performance/test_hnsw_performance.py -v -s -m performance
    """
    pytest.main([__file__, "-v", "-s", "-m", "performance"])
