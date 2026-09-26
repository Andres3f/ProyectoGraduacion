"""add route_geometry_return to routes

Separa la geometría del trayecto de regreso (última parada -> depósito) de la
de ida, para que el mapa pueda dibujarlas con colores distintos.

Revision ID: c4d5e6f7a8b9
Revises: 7a9c1b2d3e4f
Create Date: 2026-09-26 10:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, None] = '7a9c1b2d3e4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Geometría del tramo de regreso. NULL en las rutas ya guardadas: se
    # regenera con `python -m scripts.backfill_routes_geometry`.
    op.add_column(
        'routes', sa.Column('route_geometry_return', sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('routes', 'route_geometry_return')
