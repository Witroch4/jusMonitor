"""SQLAlchemy async engine and session configuration."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool

from app.config import settings


def create_engine() -> AsyncEngine:
    """Create async SQLAlchemy engine with connection pooling."""
    
    # Use NullPool for testing, AsyncAdaptedQueuePool for production
    poolclass = NullPool if settings.environment == "test" else AsyncAdaptedQueuePool
    
    # Build engine kwargs based on pool class
    engine_kwargs = {
        "echo": settings.debug,
        "pool_pre_ping": True,  # Verify connections before using
        "poolclass": poolclass,
    }
    
    # Only add pool settings for AsyncAdaptedQueuePool
    if poolclass == AsyncAdaptedQueuePool:
        engine_kwargs["pool_size"] = settings.database_pool_size
        engine_kwargs["max_overflow"] = settings.database_max_overflow
    
    engine = create_async_engine(
        str(settings.database_url),
        **engine_kwargs,
    )
    
    return engine


# Global engine instance
engine = create_engine()

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_session() -> AsyncSession:
    """
    Get a database session (non-dependency version).
    
    Usage:
        async with get_session() as session:
            ...
    
    Returns:
        AsyncSession instance
    """
    return AsyncSessionLocal()


async def close_db() -> None:
    """Close database engine. Call on application shutdown."""
    await engine.dispose()
