"""add depots table, vehicle.depot_id, route.depot_id

Revision ID: 7a9c1b2d3e4f
Revises: 09882de0f542
Create Date: 2026-09-24 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import geoalchemy2

# revision identifiers, used by Alembic.
revision: str = '7a9c1b2d3e4f'
down_revision: Union[str, None] = '09882de0f542'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Tabla de depósitos (punto de partida de los camiones).
    op.create_table(
        'depots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('address', sa.String(length=500), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column(
            'geom',
            geoalchemy2.types.Geography(
                geometry_type='POINT', srid=4326,
                from_text='ST_GeogFromText', name='geography',
            ),
            nullable=True,
        ),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column(
            'created_at', sa.DateTime(timezone=True),
            server_default=sa.text('now()'), nullable=True,
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True),
            server_default=sa.text('now()'), nullable=True,
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    # El índice espacial 'idx_depots_geom' lo genera GeoAlchemy2 automáticamente.
    op.create_index(op.f('ix_depots_id'), 'depots', ['id'], unique=False)

    # 2. vehicle.depot_id (nullable: NULL → usa el depósito is_default).
    op.add_column(
        'vehicles', sa.Column('depot_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'vehicles_depot_id_fkey', 'vehicles', 'depots', ['depot_id'], ['id']
    )

    # 3. route.depot_id: depósito real desde el que salió cada ruta.
    op.add_column(
        'routes', sa.Column('depot_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'routes_depot_id_fkey', 'routes', 'depots', ['depot_id'], ['id']
    )

    # 4. Migración de datos: crea el depósito inicial a partir de los valores
    #    previos de settings.DEPOT_LAT/DEPOT_LNG y lo marca is_default, para
    #    que el sistema nunca quede sin punto de partida tras la migración.
    op.execute("""
        INSERT INTO depots
            (name, address, latitude, longitude, geom, is_default,
             created_at, updated_at)
        SELECT 'Patio Principal Jalapa', 'Centro, Jalapa',
               14.6347, -89.9889,
               ST_SetSRID(ST_MakePoint(-89.9889, 14.6347), 4326)::geography,
               TRUE, now(), now()
        WHERE NOT EXISTS (SELECT 1 FROM depots)
    """)


def downgrade() -> None:
    op.drop_constraint('routes_depot_id_fkey', 'routes', type_='foreignkey')
    op.drop_column('routes', 'depot_id')
    op.drop_constraint('vehicles_depot_id_fkey', 'vehicles', type_='foreignkey')
    op.drop_column('vehicles', 'depot_id')
    op.drop_index(op.f('ix_depots_id'), table_name='depots')
    op.drop_table('depots')