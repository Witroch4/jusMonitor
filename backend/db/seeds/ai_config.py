"""Seed data for AI provider configurations."""

import asyncio
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from cryptography.fernet import Fernet
import os

from app.db.models.ai_provider import AIProvider
from .tenant import DEMO_TENANT_ID


def encrypt_api_key(api_key: str) -> str:
    """
    Encrypt API key for storage.
    
    In production, use proper key management (AWS KMS, HashiCorp Vault, etc.)
    For demo purposes, we'll use a simple encryption.
    
    Args:
        api_key: Plain text API key
        
    Returns:
        Encrypted API key
    """
    # Get encryption key from environment or generate one
    encryption_key = os.getenv("ENCRYPTION_KEY")
    
    if not encryption_key:
        # For demo purposes, use a fixed key
        # In production, this should be stored securely
        encryption_key = Fernet.generate_key()
    
    if isinstance(encryption_key, str):
        encryption_key = encryption_key.encode()
    
    fernet = Fernet(encryption_key)
    encrypted = fernet.encrypt(api_key.encode())
    
    return encrypted.decode()


async def seed_ai_providers(
    session: AsyncSession,
    tenant_id: UUID
) -> list[AIProvider]:
    """
    Create AI provider configurations.
    
    Configures multiple providers with priorities and rate limits:
    - OpenAI (highest priority)
    - Anthropic (fallback)
    - Groq (fast inference, lower priority)
    
    Args:
        session: Database session
        tenant_id: Tenant ID
        
    Returns:
        List of created AI providers
    """
    
    # Note: These are placeholder API keys for demo purposes
    # In production, real API keys should be provided via environment variables
    providers_config = [
        {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key": os.getenv("OPENAI_API_KEY", "sk-demo-openai-key-placeholder"),
            "priority": 100,  # Highest priority
            "is_active": True,
            "max_tokens": 4096,
            "temperature": 0.7,
            "description": "Primary provider for general tasks",
        },
        {
            "provider": "openai",
            "model": "gpt-4o",
            "api_key": os.getenv("OPENAI_API_KEY", "sk-demo-openai-key-placeholder"),
            "priority": 90,
            "is_active": True,
            "max_tokens": 8192,
            "temperature": 0.7,
            "description": "For complex reasoning tasks",
        },
        {
            "provider": "anthropic",
            "model": "claude-3-5-sonnet-20241022",
            "api_key": os.getenv("ANTHROPIC_API_KEY", "sk-ant-demo-key-placeholder"),
            "priority": 80,
            "is_active": True,
            "max_tokens": 8192,
            "temperature": 0.7,
            "description": "Fallback provider with strong reasoning",
        },
        {
            "provider": "anthropic",
            "model": "claude-3-5-haiku-20241022",
            "api_key": os.getenv("ANTHROPIC_API_KEY", "sk-ant-demo-key-placeholder"),
            "priority": 70,
            "is_active": True,
            "max_tokens": 4096,
            "temperature": 0.7,
            "description": "Fast and cost-effective for simple tasks",
        },
        {
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "api_key": os.getenv("GROQ_API_KEY", "gsk-demo-groq-key-placeholder"),
            "priority": 60,
            "is_active": True,
            "max_tokens": 8192,
            "temperature": 0.7,
            "description": "Fast inference for real-time responses",
        },
        {
            "provider": "groq",
            "model": "llama-3.1-8b-instant",
            "api_key": os.getenv("GROQ_API_KEY", "gsk-demo-groq-key-placeholder"),
            "priority": 50,
            "is_active": True,
            "max_tokens": 4096,
            "temperature": 0.7,
            "description": "Ultra-fast for simple queries",
        },
    ]
    
    ai_providers = []
    
    for config in providers_config:
        description = config.pop("description")
        api_key = config.pop("api_key")
        
        # Encrypt API key
        encrypted_key = encrypt_api_key(api_key)
        
        provider = AIProvider(
            tenant_id=tenant_id,
            api_key_encrypted=encrypted_key,
            usage_count=0,
            last_used_at=None,
            **config
        )
        
        session.add(provider)
        ai_providers.append(provider)
        
        print(f"✓ Configured AI provider: {provider.provider}/{provider.model} (priority: {provider.priority}) - {description}")
    
    await session.flush()
    
    return ai_providers


async def run_ai_config_seed(
    session: AsyncSession,
    tenant_id: UUID
) -> dict:
    """
    Run complete AI configuration seed.
    
    Args:
        session: Database session
        tenant_id: Tenant ID
        
    Returns:
        Dictionary with created AI providers
    """
    print("\n=== Seeding AI Provider Configurations ===")
    
    ai_providers = await seed_ai_providers(session, tenant_id)
    
    await session.commit()
    
    print(f"\n✓ AI config seed completed: {len(ai_providers)} providers configured")
    print("\n⚠ Note: Demo API keys are placeholders.")
    print("  Set real API keys via environment variables:")
    print("  - OPENAI_API_KEY")
    print("  - ANTHROPIC_API_KEY")
    print("  - GROQ_API_KEY")
    
    return {
        "ai_providers": ai_providers,
    }


if __name__ == "__main__":
    # For standalone testing
    from app.db.engine import AsyncSessionLocal
    
    async def main():
        async with AsyncSessionLocal() as session:
            await run_ai_config_seed(session, DEMO_TENANT_ID)
    
    asyncio.run(main())
