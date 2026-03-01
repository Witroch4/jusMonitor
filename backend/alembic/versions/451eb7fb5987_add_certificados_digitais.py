"""add_certificados_digitais

Revision ID: 451eb7fb5987
Revises: b1c2d3e4f5a6
Create Date: 2026-02-28 23:14:32.173591

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '451eb7fb5987'
down_revision: Union[str, None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('certificados_digitais',
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('nome', sa.String(length=255), nullable=False, comment='Friendly name (e.g. Certificado Dra. Maria)'),
    sa.Column('titular_nome', sa.String(length=255), nullable=False, comment='Certificate subject CN'),
    sa.Column('titular_cpf_cnpj', sa.String(length=18), nullable=False, comment='CPF or CNPJ extracted from certificate'),
    sa.Column('emissora', sa.String(length=255), nullable=False, comment='Certificate issuer CN (e.g. AC SERASA RFB v5)'),
    sa.Column('serial_number', sa.String(length=100), nullable=False, comment='Certificate serial number (hex)'),
    sa.Column('valido_de', sa.DateTime(timezone=True), nullable=False),
    sa.Column('valido_ate', sa.DateTime(timezone=True), nullable=False),
    sa.Column('pfx_encrypted', sa.LargeBinary(), nullable=False, comment='Fernet-encrypted PFX/P12 binary'),
    sa.Column('pfx_password_encrypted', sa.LargeBinary(), nullable=False, comment='Fernet-encrypted PFX password'),
    sa.Column('ultimo_teste_em', sa.DateTime(timezone=True), nullable=True),
    sa.Column('ultimo_teste_resultado', sa.String(length=20), nullable=True, comment='sucesso | falha'),
    sa.Column('ultimo_teste_mensagem', sa.Text(), nullable=True),
    sa.Column('revogado', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'serial_number', name='uq_cert_tenant_serial')
    )
    op.create_index(op.f('ix_certificados_digitais_tenant_id'), 'certificados_digitais', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_certificados_digitais_tenant_id'), table_name='certificados_digitais')
    op.drop_table('certificados_digitais')
