"""
Seed command for populating database with demo data.

Usage:
    python -m cli.seed --all
    python -m cli.seed --tenant --crm
    python -m cli.seed --cases --ai
    python -m cli.seed --all --reset
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

import click
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import AsyncSessionLocal
from db.seeds.tenant import run_tenant_seed, DEMO_TENANT_ID
from db.seeds.crm import run_crm_seed
from db.seeds.legal_cases import run_legal_cases_seed
from db.seeds.ai_config import run_ai_config_seed


async def reset_database(session: AsyncSession) -> None:
    """
    Clear all data from the database.
    
    WARNING: This will delete ALL data!
    
    Args:
        session: Database session
    """
    click.echo("\n⚠️  WARNING: This will delete ALL data from the database!")
    if not click.confirm("Are you sure you want to continue?"):
        click.echo("Aborted.")
        sys.exit(0)
    
    click.echo("\n🗑️  Clearing database...")
    
    # Tables to clear (in order to respect foreign keys)
    tables = [
        "case_movements",
        "legal_cases",
        "client_notes",
        "timeline_embeddings",
        "timeline_events",
        "clients",
        "leads",
        "ai_providers",
        "ai_conversations",
        "briefings",
        "notifications",
        "events",
        "automations",
        "client_automations",
        "user_preferences",
        "audit_logs",
        "users",
        "tenants",
    ]
    
    for table in tables:
        try:
            await session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
            click.echo(f"  ✓ Cleared {table}")
        except Exception as e:
            click.echo(f"  ⚠ Could not clear {table}: {e}")
    
    await session.commit()
    click.echo("✓ Database cleared\n")


async def run_seeds(
    session: AsyncSession,
    tenant: bool,
    crm: bool,
    cases: bool,
    ai: bool,
    all_seeds: bool,
    reset: bool
) -> None:
    """
    Run selected seed operations.
    
    Args:
        session: Database session
        tenant: Seed tenant and users
        crm: Seed CRM data (leads and clients)
        cases: Seed legal cases and movements
        ai: Seed AI provider configurations
        all_seeds: Seed everything
        reset: Clear database before seeding
    """
    if reset:
        await reset_database(session)
    
    # If --all is specified, enable all seeds
    if all_seeds:
        tenant = crm = cases = ai = True
    
    # If nothing specified, show help
    if not any([tenant, crm, cases, ai]):
        click.echo("❌ No seed options specified. Use --all or specify individual seeds.")
        click.echo("   Run 'python -m cli.seed --help' for usage information.")
        sys.exit(1)
    
    click.echo("🌱 Starting seed process...\n")
    
    # Track created data
    tenant_data = None
    crm_data = None
    
    # 1. Tenant and users (required for other seeds)
    if tenant:
        # Create super admin and platform tenant first
        from scripts.create_super_admin import create_platform_tenant, create_super_admin, create_default_schedules
        click.echo("\n🔒 Setting up Super Admin...")
        platform_tenant = await create_platform_tenant(session)
        super_admin = await create_super_admin(session, platform_tenant)
        await create_default_schedules(session)
        click.echo("✓ Super Admin setup complete")
        
        tenant_data = await run_tenant_seed(session)
        user_ids = [u.id for u in tenant_data["users"]]
    else:
        # If not seeding tenant but need it for other seeds, check if exists
        if crm or cases or ai:
            click.echo("⚠️  Tenant seed not requested, but required for other seeds.")
            click.echo("   Checking if demo tenant exists...")
            
            from app.db.models.tenant import Tenant
            from app.db.models.user import User
            from sqlalchemy import select
            
            result = await session.execute(
                select(Tenant).where(Tenant.id == DEMO_TENANT_ID)
            )
            existing_tenant = result.scalar_one_or_none()
            
            if not existing_tenant:
                click.echo("❌ Demo tenant not found. Please run with --tenant first.")
                sys.exit(1)
            
            # Get users
            result = await session.execute(
                select(User).where(User.tenant_id == DEMO_TENANT_ID)
            )
            users = result.scalars().all()
            
            if not users:
                click.echo("❌ No users found for demo tenant. Please run with --tenant first.")
                sys.exit(1)
            
            user_ids = [u.id for u in users]
            click.echo(f"✓ Found existing tenant with {len(users)} users\n")
    
    # 2. CRM data (leads and clients)
    if crm:
        crm_data = await run_crm_seed(session, DEMO_TENANT_ID, user_ids)
    else:
        # If cases seed needs clients, fetch them
        if cases:
            from app.db.models.client import Client
            from sqlalchemy import select
            
            result = await session.execute(
                select(Client).where(Client.tenant_id == DEMO_TENANT_ID)
            )
            clients = result.scalars().all()
            
            if not clients:
                click.echo("❌ No clients found. Please run with --crm first.")
                sys.exit(1)
            
            crm_data = {"clients": clients}
    
    # 3. Legal cases and movements
    if cases:
        if not crm_data:
            click.echo("❌ CRM data required for cases seed. Please run with --crm first.")
            sys.exit(1)
        
        await run_legal_cases_seed(session, DEMO_TENANT_ID, crm_data["clients"])
    
    # 4. AI provider configurations
    if ai:
        await run_ai_config_seed(session, DEMO_TENANT_ID)
    
    click.echo("\n" + "="*60)
    click.echo("✅ Seed process completed successfully!")
    click.echo("="*60)
    
    # Show summary
    click.echo("\n📊 Summary:")
    if tenant:
        click.echo("  • Tenant: Demo Law Firm")
        click.echo("  • Users: admin, advogado, assistente")
    if crm:
        click.echo("  • Leads: 20 leads across different stages")
        click.echo("  • Clients: 10 clients with notes and interactions")
    if cases:
        click.echo("  • Legal Cases: 15 cases with CNJ numbers")
        click.echo("  • Movements: 100+ case movements")
    if ai:
        click.echo("  • AI Providers: OpenAI, Anthropic, Groq configured")
    
    click.echo("\n🔐 Demo Credentials:")
    click.echo("  • Admin: admin@demolawfirm.com / admin123")
    click.echo("  • Advogado: advogado@demolawfirm.com / advogado123")
    click.echo("  • Assistente: assistente@demolawfirm.com / assistente123")
    
    click.echo("\n💡 Next Steps:")
    click.echo("  1. Start the backend: python main.py")
    click.echo("  2. Access API docs: http://localhost:8000/docs")
    click.echo("  3. Login with demo credentials")
    click.echo("")


@click.command()
@click.option(
    "--all",
    "all_seeds",
    is_flag=True,
    help="Seed all data (tenant, CRM, cases, AI)"
)
@click.option(
    "--tenant",
    is_flag=True,
    help="Seed tenant and users only"
)
@click.option(
    "--crm",
    is_flag=True,
    help="Seed CRM data (leads and clients)"
)
@click.option(
    "--cases",
    is_flag=True,
    help="Seed legal cases and movements"
)
@click.option(
    "--ai",
    is_flag=True,
    help="Seed AI provider configurations"
)
@click.option(
    "--reset",
    is_flag=True,
    help="Clear all data before seeding (WARNING: destructive!)"
)
def seed(all_seeds: bool, tenant: bool, crm: bool, cases: bool, ai: bool, reset: bool):
    """
    Seed database with demo data for development and testing.
    
    Examples:
    
        # Seed everything
        python -m cli.seed --all
        
        # Seed only tenant and users
        python -m cli.seed --tenant
        
        # Seed CRM and cases
        python -m cli.seed --crm --cases
        
        # Reset database and seed everything
        python -m cli.seed --all --reset
    """
    async def main():
        async with AsyncSessionLocal() as session:
            await run_seeds(session, tenant, crm, cases, ai, all_seeds, reset)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        click.echo("\n\n⚠️  Seed process interrupted by user.")
        sys.exit(1)
    except Exception as e:
        click.echo(f"\n\n❌ Error during seed process: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    seed()
