"""add logs_sistema table and routes.distance_source

Revision ID: b2a4f5c6d7e8
Revises: 3f7c0d9a1b2e
Create Date: 2026-08-31 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b2a4f5c6d7e8'
down_revision: Union[str, None] = '3f7c0d9a1b2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tabla de logs de auditoría (quién hizo qué).
    op.create_table(
        'logs_sistema',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('accion', sa.String(length=100), nullable=False),
        sa.Column('entidad', sa.String(length=50), nullable=True),
        sa.Column('entidad_id', sa.Integer(), nullable=True),
        sa.Column('detalle', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index(op.f('ix_logs_sistema_created_at'), 'logs_sistema', ['created_at'], unique=False)
    op.create_index(op.f('ix_logs_sistema_id'), 'logs_sistema', ['id'], unique=False)

    # Fuente de las distancias de cada ruta: "ors" (reales) o "haversine".
    op.add_column(
        'routes',
        sa.Column('distance_source', sa.String(length=20), nullable=True,
                  server_default='haversine'),
    )


def downgrade() -> None:
    op.drop_column('routes', 'distance_source')
    op.drop_index(op.f('ix_logs_sistema_id'), table_name='logs_sistema')
    op.drop_index(op.f('ix_logs_sistema_created_at'), table_name='logs_sistema')
    op.drop_table('logs_sistema')
