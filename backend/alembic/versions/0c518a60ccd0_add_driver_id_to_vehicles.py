"""add driver_id to vehicles

Revision ID: 0c518a60ccd0
Revises: e813abcd9b5a
Create Date: 2026-08-27 19:02:23.908578
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0c518a60ccd0'
down_revision: Union[str, None] = 'e813abcd9b5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('vehicles', sa.Column('driver_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'vehicles_driver_id_fkey', 'vehicles', 'users', ['driver_id'], ['id']
    )


def downgrade() -> None:
    op.drop_constraint('vehicles_driver_id_fkey', 'vehicles', type_='foreignkey')
    op.drop_column('vehicles', 'driver_id')
