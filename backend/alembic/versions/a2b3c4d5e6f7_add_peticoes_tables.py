"""add_peticoes_tables

Revision ID: a2b3c4d5e6f7
Revises: 451eb7fb5987
Create Date: 2026-03-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = '451eb7fb5987'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === peticoes ===
    op.create_table('peticoes',
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('criado_por', sa.UUID(), nullable=True),
        sa.Column('certificado_id', sa.UUID(), nullable=True),
        sa.Column('processo_numero', sa.String(length=50), nullable=False, comment='Número CNJ (20 dígitos) ou formatado com pontos'),
        sa.Column('tribunal_id', sa.String(length=20), nullable=False, comment='ID do tribunal (e.g. TRF5-JFCE)'),
        sa.Column('tipo_peticao', sa.String(length=30), nullable=False),
        sa.Column('assunto', sa.String(length=500), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('numero_protocolo', sa.String(length=100), nullable=True),
        sa.Column('protocolado_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('protocolo_recibo', sa.Text(), nullable=True, comment='Recibo base64 retornado pelo tribunal'),
        sa.Column('motivo_rejeicao', sa.Text(), nullable=True),
        sa.Column('analise_ia', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['criado_por'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['certificado_id'], ['certificados_digitais.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_peticoes_tenant_id', 'peticoes', ['tenant_id'])
    op.create_index('ix_peticoes_processo_numero', 'peticoes', ['processo_numero'])
    op.create_index('ix_peticoes_tribunal_id', 'peticoes', ['tribunal_id'])
    op.create_index('ix_peticoes_status', 'peticoes', ['status'])
    op.create_index('ix_peticoes_criado_por', 'peticoes', ['criado_por'])

    # === peticao_documentos ===
    op.create_table('peticao_documentos',
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('peticao_id', sa.UUID(), nullable=False),
        sa.Column('nome_original', sa.String(length=500), nullable=False),
        sa.Column('tamanho_bytes', sa.Integer(), nullable=False),
        sa.Column('tipo_documento', sa.String(length=30), nullable=False),
        sa.Column('ordem', sa.Integer(), nullable=False),
        sa.Column('conteudo_encrypted', sa.LargeBinary(), nullable=False, comment='Fernet-encrypted PDF bytes'),
        sa.Column('hash_sha256', sa.String(length=64), nullable=False, comment='SHA-256 hash of original PDF bytes'),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('erro_validacao', sa.Text(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['peticao_id'], ['peticoes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_peticao_documentos_tenant_id', 'peticao_documentos', ['tenant_id'])
    op.create_index('ix_peticao_documentos_peticao_id', 'peticao_documentos', ['peticao_id'])

    # === peticao_eventos ===
    op.create_table('peticao_eventos',
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('peticao_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('descricao', sa.String(length=500), nullable=False),
        sa.Column('detalhes', sa.Text(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['peticao_id'], ['peticoes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_peticao_eventos_tenant_id', 'peticao_eventos', ['tenant_id'])
    op.create_index('ix_peticao_eventos_peticao_id', 'peticao_eventos', ['peticao_id'])


def downgrade() -> None:
    op.drop_table('peticao_eventos')
    op.drop_table('peticao_documentos')
    op.drop_table('peticoes')
