"""merge ors geometry and logs audits

Revision ID: 09882de0f542
Revises: b2a4f5c6d7e8, a1b2c3d4e5f6
Create Date: 2026-09-01 18:30:01.296686
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '09882de0f542'
down_revision: Union[str, None] = ('b2a4f5c6d7e8', 'a1b2c3d4e5f6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
