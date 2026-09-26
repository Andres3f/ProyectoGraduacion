"""add fallido value to orderstatus enum

`OrderStatus.fallido` existe en el modelo desde el sprint de entregas, pero
nunca se añadió al enum de PostgreSQL, así que marcar una parada como fallida
fallaba con:

    invalid input value for enum orderstatus: "fallido"

Los tests no lo detectaban porque recrean el esquema con `create_all()`, que
reconstruye el enum desde los modelos; solo las bases migradas con Alembic
tenían el valor ausente.

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-09-26 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, None] = 'c4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # `ALTER TYPE ... ADD VALUE` no se puede ejecutar dentro de la transacción
    # de la migración en versiones antiguas de PostgreSQL, así que Alembic lo
    # envuelve en un bloque de autocommit. `IF NOT EXISTS` la hace idempotente.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'fallido'")


def downgrade() -> None:
    # PostgreSQL no permite quitar un valor de un enum. Para revertirlo hay que
    # recrear el tipo, lo que exige migrar los datos de la columna `status`.
    raise NotImplementedError(
        "PostgreSQL no permite eliminar valores de un enum. Para revertir, "
        "hay que recrear el tipo orderstatus sin 'fallido' y castear la columna."
    )
