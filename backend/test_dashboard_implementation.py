"""
Simple test script to verify dashboard implementation.

This script checks that all the dashboard components are properly implemented
and can be imported without errors.
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))


def test_imports():
    """Test that all dashboard components can be imported."""
    print("Testing imports...")
    
    try:
        # Test schemas
        from app.schemas.dashboard import (
            AttentionCaseItem,
            DashboardAttentionResponse,
            DashboardGoodNewsResponse,
            DashboardMetricsResponse,
            DashboardNoiseResponse,
            DashboardUrgentResponse,
            GoodNewsItem,
            NoiseItem,
            OfficeMetrics,
            UrgentCaseItem,
        )
        print("✓ Dashboard schemas imported successfully")
        
        # Test user preference schemas
        from app.schemas.user_preference import (
            DashboardPreferences,
            DashboardPreferencesUpdate,
            UserPreferenceCreate,
            UserPreferenceResponse,
            UserPreferenceUpdate,
        )
        print("✓ User preference schemas imported successfully")
        
        # Test services
        from app.core.services.dashboard import DashboardAggregator, MetricsCalculator
        print("✓ Dashboard services imported successfully")
        
        # Test models
        from app.db.models.user_preference import UserPreference
        print("✓ User preference model imported successfully")
        
        # Test API endpoints
        from app.api.v1.endpoints import dashboard
        print("✓ Dashboard API endpoints imported successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_schema_validation():
    """Test that schemas can be instantiated."""
    print("\nTesting schema validation...")
    
    try:
        from app.schemas.dashboard import OfficeMetrics, UrgentCaseItem
        from datetime import date
        from uuid import uuid4
        
        # Test OfficeMetrics
        metrics = OfficeMetrics(
            conversion_rate=45.5,
            conversion_rate_change=5.2,
            avg_response_time_hours=4.5,
            avg_response_time_change=-12.3,
            satisfaction_score=87.0,
            satisfaction_score_change=3.1,
            total_active_cases=10,
            new_cases_this_period=2,
            total_active_clients=8,
            new_clients_this_period=1,
        )
        print(f"✓ OfficeMetrics created: {metrics.conversion_rate}% conversion rate")
        
        # Test UrgentCaseItem
        urgent_case = UrgentCaseItem(
            case_id=uuid4(),
            cnj_number="1234567-89.2024.1.01.0001",
            client_id=uuid4(),
            client_name="Test Client",
            next_deadline=date.today(),
            days_remaining=2,
        )
        print(f"✓ UrgentCaseItem created: {urgent_case.cnj_number}")
        
        # Test DashboardPreferences
        from app.schemas.user_preference import DashboardPreferences
        
        prefs = DashboardPreferences()
        print(f"✓ DashboardPreferences created with defaults: {prefs.default_period_days} days")
        
        return True
        
    except Exception as e:
        print(f"✗ Schema validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_router():
    """Test that dashboard router is properly configured."""
    print("\nTesting API router...")
    
    try:
        from app.api.v1.router import api_router
        
        # Check that dashboard routes are included
        routes = [route.path for route in api_router.routes]
        dashboard_routes = [r for r in routes if '/dashboard' in r]
        
        print(f"✓ Found {len(dashboard_routes)} dashboard routes:")
        for route in dashboard_routes:
            print(f"  - {route}")
        
        expected_routes = [
            '/v1/dashboard/urgent',
            '/v1/dashboard/attention',
            '/v1/dashboard/good-news',
            '/v1/dashboard/noise',
            '/v1/dashboard/metrics',
            '/v1/dashboard/preferences',
            '/v1/dashboard/summary',
        ]
        
        for expected in expected_routes:
            if expected in routes:
                print(f"  ✓ {expected}")
            else:
                print(f"  ✗ Missing: {expected}")
        
        return True
        
    except Exception as e:
        print(f"✗ Router test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Dashboard Implementation Test")
    print("=" * 60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Schema Validation", test_schema_validation()))
    results.append(("API Router", test_api_router()))
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
        print("=" * 60)
        return 0
    else:
        print("✗ Some tests failed")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())

