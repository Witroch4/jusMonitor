"""Seed data for demo tenant and users."""

import asyncio
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
import bcrypt
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = type("about", (), {"__version__": getattr(bcrypt, "__version__", "4.0.1")})
from passlib.context import CryptContext

from app.db.models.tenant import Tenant
from app.db.models.user import User, UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Demo tenant ID (fixed for consistency across seeds)
DEMO_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


async def seed_tenant(session: AsyncSession) -> Tenant:
    """
    Create demo tenant "Demo Law Firm".
    
    Returns:
        Created tenant instance
    """
    tenant = Tenant(
        id=DEMO_TENANT_ID,
        name="Demo Law Firm",
        slug="demo-law-firm",
        plan="professional",
        is_active=True,
        settings={
            "sync_frequency_hours": 6,
            "notification_channels": ["email", "whatsapp"],
            "ai_features_enabled": True,
            "max_users": 10,
            "max_cases": 1000,
        }
    )
    
    session.add(tenant)
    await session.flush()
    
    print(f"✓ Created tenant: {tenant.name} (ID: {tenant.id})")
    return tenant


async def seed_users(session: AsyncSession, tenant_id: UUID) -> list[User]:
    """
    Create demo users: admin, advogado (lawyer), assistente (assistant).
    
    Args:
        session: Database session
        tenant_id: Tenant ID to associate users with
        
    Returns:
        List of created users
    """
    users_data = [
        {
            "email": "amandasousa22.adv@gmail.com",
            "password": "amandaesquecida@123ABC",
            "full_name": "Amanda Sousa",
            "role": UserRole.ADMIN,
        },
        {
            "email": "carlos@demolawfirm.com",
            "password": "lawyer123",
            "full_name": "Carlos Advogado",
            "role": UserRole.LAWYER,
        },
        {
            "email": "marcos@demolawfirm.com",
            "password": "assistant123",
            "full_name": "Marcos Assistente",
            "role": UserRole.ASSISTANT,
        },
    ]
    
    users = []
    for user_data in users_data:
        password = user_data.pop("password")
        user = User(
            tenant_id=tenant_id,
            password_hash=pwd_context.hash(password),
            is_active=True,
            **user_data
        )
        session.add(user)
        users.append(user)
    
    await session.flush()
    
    for user in users:
        print(f"✓ Created user: {user.full_name} ({user.email}) - Role: {user.role}")
    
    return users


async def run_tenant_seed(session: AsyncSession) -> dict:
    """
    Run complete tenant seed.
    
    Args:
        session: Database session
        
    Returns:
        Dictionary with created tenant and users
    """
    print("\n=== Seeding Tenant and Users ===")
    
    tenant = await seed_tenant(session)
    users = await seed_users(session, tenant.id)
    
    await session.commit()
    
    print(f"\n✓ Tenant seed completed: {len(users)} users created")
    
    return {
        "tenant": tenant,
        "users": users,
        "admin": users[0],
        "advogado": users[1],
        "assistente": users[2],
    }


if __name__ == "__main__":
    # For standalone testing
    from app.db.engine import AsyncSessionLocal
    
    async def main():
        async with AsyncSessionLocal() as session:
            await run_tenant_seed(session)
    
    asyncio.run(main())
