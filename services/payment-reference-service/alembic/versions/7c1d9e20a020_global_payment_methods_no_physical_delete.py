"""global payment methods: sin borrado físico

Revision ID: 7c1d9e20a020
Revises: 4a30e958088d
Create Date: 2026-10-14 00:00:00.000000

Spec 020 (FR-020-10, RC-MVP-4; GAP-PR-18 parcial; D7): Purchase y Sales guardan
`payment_method_id`, así que un método usado no puede desaparecer. La API ya no expone
`DELETE` y este trigger rechaza `DELETE` y `TRUNCATE` en la base. La inactivación sigue
disponible con `PUT` (`status = INACTIVE`). No modifica datos.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '7c1d9e20a020'
down_revision: Union[str, Sequence[str], None] = '4a30e958088d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


REJECT_FUNCTION = """
CREATE FUNCTION global_payment_methods_reject_delete() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Los métodos de pago no se eliminan físicamente (%): inactívelos.', TG_OP
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$;
"""


def upgrade() -> None:
    """Crea los triggers que impiden el borrado físico."""
    op.execute(REJECT_FUNCTION)
    op.execute(
        "CREATE TRIGGER tr_global_payment_methods_no_delete BEFORE DELETE ON global_payment_methods "
        "FOR EACH ROW EXECUTE FUNCTION global_payment_methods_reject_delete()"
    )
    op.execute(
        "CREATE TRIGGER tr_global_payment_methods_no_truncate BEFORE TRUNCATE ON global_payment_methods "
        "FOR EACH STATEMENT EXECUTE FUNCTION global_payment_methods_reject_delete()"
    )


def downgrade() -> None:
    """Elimina los triggers (vuelve a permitir el borrado en la base)."""
    op.execute("DROP TRIGGER IF EXISTS tr_global_payment_methods_no_truncate ON global_payment_methods")
    op.execute("DROP TRIGGER IF EXISTS tr_global_payment_methods_no_delete ON global_payment_methods")
    op.execute("DROP FUNCTION IF EXISTS global_payment_methods_reject_delete()")
