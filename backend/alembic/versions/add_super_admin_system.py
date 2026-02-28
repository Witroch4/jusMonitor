"""Add super admin system: new role, agent_execution_logs, worker_schedules tables.

Revision ID: a1b2c3d4e5f6
Revises: 07aa6fd2ba78
Create Date: 2026-02-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "07aa6fd2ba78"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Expand role column from VARCHAR(9) to VARCHAR(11) to fit 'SUPER_ADMIN'
    op.alter_column('users', 'role', type_=sa.String(11), existing_type=sa.String(9))

    # 2. Update the CHECK constraint to include SUPER_ADMIN
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS user_role")
    op.execute("""
        ALTER TABLE users ADD CONSTRAINT user_role
        CHECK (role IN ('SUPER_ADMIN', 'ADMIN', 'LAWYER', 'ASSISTANT', 'VIEWER'))
    """)

    # 2. Create agent_execution_logs table
    op.create_table(
        "agent_execution_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("agent_name", sa.String(100), nullable=False, index=True),
        sa.Column("status", sa.String(20), nullable=False, index=True),
        sa.Column("input_tokens", sa.Integer, nullable=False, default=0),
        sa.Column("output_tokens", sa.Integer, nullable=False, default=0),
        sa.Column("total_tokens", sa.Integer, nullable=False, default=0),
        sa.Column("provider_used", sa.String(50), nullable=False, default="unknown", index=True),
        sa.Column("model_used", sa.String(100), nullable=False, default="unknown"),
        sa.Column("duration_ms", sa.Integer, nullable=False, default=0),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("context", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # 3. Create worker_schedules table
    op.create_table(
        "worker_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("task_name", sa.String(100), unique=True, nullable=False),
        sa.Column("cron_expression", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True, index=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("worker_schedules")
    op.drop_table("agent_execution_logs")
    # Note: Cannot remove enum values in PostgreSQL easily.
    # The 'super_admin' value will remain but be unused.
