"""Crea la outbox de auditoría (`audit_outbox`; feature 016, D26).

Revision ID: 0019_audit_outbox
Revises: 0018_widen_sector_name
Create Date: 2026-10-07

Estructura definida por `libs/sio-audit` (`sio_audit.outbox`), igual que en Inventory, Purchase y
Sales. Categoría Outbox (Principio VI): sin `version`; el worker solo marca `SENT`, nunca borra.
Ver specs/016-existing-services-audit/data-model.md.
"""

from collections.abc import Sequence

from sio_audit.outbox import create_audit_outbox_table, drop_audit_outbox_table

revision: str = "0019_audit_outbox"
down_revision: str | None = "0018_widen_sector_name"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    from alembic import op

    create_audit_outbox_table(op)


def downgrade() -> None:
    from alembic import op

    drop_audit_outbox_table(op)
