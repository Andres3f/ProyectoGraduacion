"""add delivered_at to route_stops

Revision ID: 3f7c0d9a1b2e
Revises: 10a95ef0b258
Create Date: 2026-08-28 22:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3f7c0d9a1b2e'
down_revision: Union[str, None] = '10a95ef0b258'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Sello de tiempo de entrega real de una parada (OPT-18). Se setea cuando
    # el conductor marca la parada como "entregado".
    op.add_column(
        'route_stops', sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('route_stops', 'delivered_at')
