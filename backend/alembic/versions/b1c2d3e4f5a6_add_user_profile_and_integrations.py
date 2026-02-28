"""add_user_profile_fields_and_user_integrations_table

Revision ID: b1c2d3e4f5a6
Revises: a084d486203a
Create Date: 2026-02-28

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: str = "a084d486203a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add profile columns to users table
    op.add_column("users", sa.Column("phone", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(500), nullable=True))
    op.add_column("users", sa.Column("oab_number", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("oab_state", sa.String(2), nullable=True))

    # Add Instagram fields to leads table
    op.add_column(
        "leads", sa.Column("instagram_username", sa.String(100), nullable=True)
    )
    op.add_column(
        "leads",
        sa.Column("instagram_profile_picture_url", sa.String(500), nullable=True),
    )

    # Create user_integrations table
    op.create_table(
        "user_integrations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("integration_type", sa.String(50), nullable=False),
        sa.Column("access_token_encrypted", sa.Text(), nullable=True),
        sa.Column(
            "token_expires_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("external_user_id", sa.String(100), nullable=True),
        sa.Column("external_username", sa.String(100), nullable=True),
        sa.Column(
            "external_profile_picture_url", sa.String(500), nullable=True
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "extra_data",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "user_id",
            "integration_type",
            name="uq_user_integrations_tenant_user_type",
        ),
    )
    op.create_index(
        "ix_user_integrations_user_id", "user_integrations", ["user_id"]
    )
    op.create_index(
        "ix_user_integrations_tenant_id", "user_integrations", ["tenant_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_user_integrations_tenant_id", table_name="user_integrations")
    op.drop_index("ix_user_integrations_user_id", table_name="user_integrations")
    op.drop_table("user_integrations")

    op.drop_column("leads", "instagram_profile_picture_url")
    op.drop_column("leads", "instagram_username")

    op.drop_column("users", "oab_state")
    op.drop_column("users", "oab_number")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "phone")
