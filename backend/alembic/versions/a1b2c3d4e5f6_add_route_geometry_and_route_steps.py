"""add route_geometry and route_steps to routes

Revision ID: a1b2c3d4e5f6
Revises: 3f7c0d9a1b2e
Create Date: 2026-09-01 18:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '3f7c0d9a1b2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('routes', sa.Column('route_geometry', sa.JSON(), nullable=True))
    op.add_column('routes', sa.Column('steps', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('routes', 'steps')
    op.drop_column('routes', 'route_geometry')