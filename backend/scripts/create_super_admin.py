#!/usr/bin/env python3
"""
Create the platform tenant and super admin user.

Usage:
    python -m scripts.create_super_admin

    # Or with custom credentials:
    SUPER_ADMIN_EMAIL=admin@jusmonitor.com SUPER_ADMIN_PASSWORD=secret123 python -m scripts.create_super_admin

Also seeds default worker schedules.
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.config import settings
from app.core.auth.password import hash_password
from app.db.engine import AsyncSessionLocal, close_db
from app.db.models.tenant import Tenant
from app.db.models.user import User, UserRole
from app.db.models.worker_schedule import WorkerSchedule


PLATFORM_TENANT_SLUG = "_platform"
PLATFORM_TENANT_NAME = "JusMonitor Platform"

DEFAULT_SCHEDULES = [
    {
        "task_name": "datajud_poller",
        "cron_expression": "0 */6 * * *",
        "description": "Sincronizar processos com DataJud a cada 6 horas",
        "config": {"batch_size": 100, "timeout_minutes": 5},
    },
    {
        "task_name": "lead_scoring",
        "cron_expression": "0 */1 * * *",
        "description": "Recalcular score de leads ativos a cada hora",
        "config": {},
    },
    {
        "task_name": "embeddings_batch",
        "cron_expression": "30 3 * * *",
        "description": "Gerar embeddings pendentes diariamente as 03:30",
        "config": {"batch_size": 50},
    },
]


async def create_platform_tenant(session) -> Tenant:
    """Create or get the _platform tenant."""
    result = await session.execute(
        select(Tenant).where(Tenant.slug == PLATFORM_TENANT_SLUG)
    )
    tenant = result.scalar_one_or_none()

    if tenant:
        print(f"  Platform tenant already exists: {tenant.id}")
        return tenant

    tenant = Tenant(
        name=PLATFORM_TENANT_NAME,
        slug=PLATFORM_TENANT_SLUG,
        plan="enterprise",
        is_active=True,
        settings={"type": "platform", "description": "Internal platform management tenant"},
    )
    session.add(tenant)
    await session.flush()
    print(f"  Created platform tenant: {tenant.id}")
    return tenant


async def create_super_admin(session, tenant: Tenant) -> User:
    """Create or update the super admin user."""
    email = settings.super_admin_email or "witalo_rocha@hotmail.com"
    password = settings.super_admin_password or "W#@@%¨&!B!!!UN<L="

    result = await session.execute(
        select(User).where(User.email == email, User.tenant_id == tenant.id)
    )
    user = result.scalar_one_or_none()

    if user:
        if user.role != UserRole.SUPER_ADMIN:
            user.role = UserRole.SUPER_ADMIN
            print(f"  Updated user role to super_admin: {user.id}")
        else:
            print(f"  Super admin already exists: {user.id} ({email})")
        return user

    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name="Super Admin",
        role=UserRole.SUPER_ADMIN,
        tenant_id=tenant.id,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    print(f"  Created super admin: {user.id} ({email})")
    print(f"  Password: {password}")
    return user


async def create_default_schedules(session) -> None:
    """Create default worker schedules."""
    for sched_data in DEFAULT_SCHEDULES:
        result = await session.execute(
            select(WorkerSchedule).where(
                WorkerSchedule.task_name == sched_data["task_name"]
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"  Schedule '{sched_data['task_name']}' already exists")
            continue

        schedule = WorkerSchedule(
            task_name=sched_data["task_name"],
            cron_expression=sched_data["cron_expression"],
            is_active=True,
            config=sched_data.get("config", {}),
            description=sched_data["description"],
        )
        session.add(schedule)
        print(f"  Created schedule: {sched_data['task_name']} ({sched_data['cron_expression']})")


async def main():
    print("\n=== JusMonitor Super Admin Setup ===\n")

    async with AsyncSessionLocal() as session:
        print("1. Platform Tenant")
        tenant = await create_platform_tenant(session)

        print("\n2. Super Admin User")
        user = await create_super_admin(session, tenant)

        print("\n3. Worker Schedules")
        await create_default_schedules(session)

        await session.commit()

    await close_db()
    print("\n=== Setup Complete ===\n")


if __name__ == "__main__":
    asyncio.run(main())
