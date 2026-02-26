"""
Test script to verify database optimizations.

This script tests:
1. Migration can be applied
2. Indexes are created correctly
3. Optimized repositories work
4. Cache service works
"""

import asyncio
import sys
from uuid import uuid4

# Add backend to path
sys.path.insert(0, '/home/wital/jusMonitor/backend')

from sqlalchemy import text
from app.db.engine import engine, AsyncSessionLocal
from app.services.cache_service import cache_service


async def test_indexes():
    """Test that indexes were created."""
    print("\n=== Testing Indexes ===")
    
    async with engine.begin() as conn:
        # Check if key indexes exist
        result = await conn.execute(text("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename IN ('clients', 'leads', 'legal_cases', 'case_movements')
            AND indexname LIKE 'idx_%'
            ORDER BY indexname;
        """))
        
        indexes = [row[0] for row in result.fetchall()]
        
        print(f"Found {len(indexes)} indexes:")
        for idx in indexes[:10]:  # Show first 10
            print(f"  - {idx}")
        
        if len(indexes) > 10:
            print(f"  ... and {len(indexes) - 10} more")
        
        # Check for specific critical indexes
        critical_indexes = [
            'idx_clients_tenant_status_created',
            'idx_leads_tenant_status_stage_score',
            'idx_legal_cases_tenant_client_movement',
            'idx_case_movements_tenant_case_date',
        ]
        
        missing = [idx for idx in critical_indexes if idx not in indexes]
        
        if missing:
            print(f"\n⚠️  Missing critical indexes: {missing}")
            print("Run: alembic upgrade head")
            return False
        else:
            print("\n✅ All critical indexes present")
            return True


async def test_cache_service():
    """Test cache service."""
    print("\n=== Testing Cache Service ===")
    
    try:
        await cache_service.connect()
        
        # Test basic operations
        tenant_id = uuid4()
        test_key = "test:key"
        test_value = {"data": "test", "number": 42}
        
        # Set
        success = await cache_service.set(test_key, test_value, ttl=60, tenant_id=tenant_id)
        if not success:
            print("❌ Cache set failed")
            return False
        
        # Get
        cached = await cache_service.get(test_key, tenant_id=tenant_id)
        if cached != test_value:
            print(f"❌ Cache get failed: expected {test_value}, got {cached}")
            return False
        
        # Delete
        deleted = await cache_service.delete(test_key, tenant_id=tenant_id)
        if not deleted:
            print("❌ Cache delete failed")
            return False
        
        # Verify deleted
        cached = await cache_service.get(test_key, tenant_id=tenant_id)
        if cached is not None:
            print("❌ Cache still exists after delete")
            return False
        
        print("✅ Cache service working correctly")
        
        await cache_service.disconnect()
        return True
        
    except Exception as e:
        print(f"❌ Cache service error: {e}")
        return False


async def test_optimized_repository():
    """Test optimized repository."""
    print("\n=== Testing Optimized Repository ===")
    
    try:
        from app.db.repositories.optimized_base import OptimizedBaseRepository
        from app.db.models.client import Client
        
        tenant_id = uuid4()
        
        async with AsyncSessionLocal() as session:
            repo = OptimizedBaseRepository(
                Client,
                session,
                tenant_id,
                eager_load=['tenant', 'assigned_user'],
            )
            
            # Test that repository can be instantiated
            print("✅ OptimizedBaseRepository instantiated successfully")
            
            # Test count (should work even with no data)
            count = await repo.count()
            print(f"✅ Count query works: {count} clients")
            
            return True
            
    except Exception as e:
        print(f"❌ Optimized repository error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Database Optimization Tests")
    print("=" * 60)
    
    results = []
    
    # Test indexes
    results.append(("Indexes", await test_indexes()))
    
    # Test cache service
    results.append(("Cache Service", await test_cache_service()))
    
    # Test optimized repository
    results.append(("Optimized Repository", await test_optimized_repository()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:.<40} {status}")
    
    all_passed = all(passed for _, passed in results)
    
    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
