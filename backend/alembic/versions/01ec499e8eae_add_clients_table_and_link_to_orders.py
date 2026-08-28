"""add clients table and link to orders

Revision ID: 01ec499e8eae
Revises: 0c518a60ccd0
Create Date: 2026-08-27 19:08:10.615276
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import geoalchemy2

# revision identifiers, used by Alembic.
revision: str = '01ec499e8eae'
down_revision: Union[str, None] = '0c518a60ccd0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Tabla de clientes
    op.create_table('clients',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('address', sa.String(length=500), nullable=False),
        sa.Column('zone', sa.String(length=100), nullable=True),
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
    # El índice espacial 'idx_clients_geom' lo genera GeoAlchemy2
    # automáticamente al crear la columna Geography (spatial_index=True).
    op.create_index(op.f('ix_clients_id'), 'clients', ['id'], unique=False)

    # 2. orders.client_id (nullable para poder rellenarlo con datos previos)
    op.add_column(
        'orders', sa.Column('client_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'orders_client_id_fkey', 'orders', 'clients', ['client_id'], ['id']
    )

    # 3. Migración de datos: crea clientes a partir de los datos sueltos de
    #    los pedidos existentes y enlaza cada pedido con su cliente.
    op.execute("""
        INSERT INTO clients
            (name, address, zone, latitude, longitude, geom, created_at, updated_at)
        SELECT DISTINCT ON (client_name, address)
            client_name, address, NULL, latitude, longitude,
            ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography,
            now(), now()
        FROM orders
        WHERE orders.client_id IS NULL
        ORDER BY client_name, address
    """)
    op.execute("""
        UPDATE orders o
        SET client_id = c.id
        FROM clients c
        WHERE o.client_id IS NULL
          AND o.client_name = c.name
          AND o.address = c.address
    """)

    # 4. A partir de ahora todo pedido DEBE tener cliente
    op.alter_column('orders', 'client_id', nullable=False)


def downgrade() -> None:
    op.drop_constraint('orders_client_id_fkey', 'orders', type_='foreignkey')
    op.drop_column('orders', 'client_id')
    op.drop_index(op.f('ix_clients_id'), table_name='clients')
    op.drop_table('clients')