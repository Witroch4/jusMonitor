"""
Pytest configuration and fixtures for tests.
"""

import os
from unittest.mock import Mock

import pytest


# Set test environment variables before importing app modules
@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Setup test environment variables."""
    os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test_db"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key"
    os.environ["JWT_ALGORITHM"] = "HS256"
    os.environ["JWT_EXPIRATION_MINUTES"] = "30"
    os.environ["CHATWIT_API_URL"] = "https://api.chatwit.test"
    os.environ["CHATWIT_API_KEY"] = "test_chatwit_key"
    os.environ["CHATWIT_RATE_LIMIT_PER_MINUTE"] = "100"
    os.environ["DATAJUD_API_URL"] = "https://api.datajud.test"
    os.environ["DATAJUD_CERT_PATH"] = ""
    os.environ["DATAJUD_KEY_PATH"] = ""
    
    yield
    
    # Cleanup
    for key in [
        "SECRET_KEY",
        "DATABASE_URL",
        "REDIS_URL",
        "JWT_SECRET_KEY",
        "CHATWIT_API_URL",
        "CHATWIT_API_KEY",
        "DATAJUD_API_URL",
    ]:
        os.environ.pop(key, None)


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    from unittest.mock import AsyncMock
    
    redis = AsyncMock()
    redis.get.return_value = None
    redis.set.return_value = True
    redis.delete.return_value = True
    redis.incr.return_value = 1
    redis.expire.return_value = True
    redis.zadd.return_value = 1
    redis.zrange.return_value = []
    redis.zrevrange.return_value = []
    redis.zrem.return_value = 1
    redis.keys.return_value = []
    redis.close.return_value = None
    
    return redis


@pytest.fixture
def mock_settings():
    """Mock application settings."""
    from unittest.mock import Mock
    
    settings = Mock()
    settings.secret_key = "test-secret-key"
    settings.database_url = "postgresql+asyncpg://test:test@localhost:5432/test_db"
    settings.redis_url = "redis://localhost:6379/0"
    settings.jwt_secret_key = "test-jwt-secret"
    settings.jwt_algorithm = "HS256"
    settings.jwt_expiration_minutes = 30
    settings.chatwit_api_url = "https://api.chatwit.test"
    settings.chatwit_api_key = "test_chatwit_key"
    settings.chatwit_rate_limit_per_minute = 100
    settings.datajud_api_url = "https://api.datajud.test"
    settings.DATAJUD_API_URL = "https://api.datajud.test"
    settings.DATAJUD_CERT_PATH = None
    settings.DATAJUD_KEY_PATH = None
    
    return settings
