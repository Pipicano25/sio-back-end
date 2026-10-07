"""Datos de la Fase A sembrados en la revisión `0001` (antes de la valoración; T007, T019, T022).

Inserta operaciones, movimientos y saldos coherentes con el esquema de la `0001`
(sin columnas de valoración), como los habría dejado el motor de la Fase A.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import text

from tests.contract.db_rows import insert_movement, insert_operation


class FaseASeeder:
    """Siembra entradas, salidas y reversos de una sucursal, con saldos y correlativos."""

    def __init__(self, connection, company: UUID, branch: UUID, *, application_user_id: UUID | None = None) -> None:
        self._connection = connection
        self.company = company
        self.branch = branch
        self.application_user_id = application_user_id or uuid4()
        self.balances: dict[UUID, tuple[Decimal, int]] = {}

    def _apply(
        self,
        product: UUID,
        operation_type: str,
        movement_type: str,
        quantity: Decimal,
        *,
        unit_cost: Decimal | None = None,
        reverses: UUID | None = None,
        reversed_movement: UUID | None = None,
        operation_id: UUID | None = None,
        movement_id: UUID | None = None,
    ) -> tuple[UUID, UUID]:
        origin_type = "PURCHASE" if operation_type in ("ENTRY", "ENTRY_REVERSAL") else "SALE"
        sign = 1 if movement_type in ("PURCHASE_ENTRY", "OUTPUT_REVERSAL") else -1
        previous, version = self.balances.get(product, (Decimal(0), 0))
        new = previous + sign * quantity
        assert new >= 0, "la Fase A nunca deja saldos negativos"
        operation = insert_operation(
            self._connection,
            id=operation_id or uuid4(),
            operation_type=operation_type,
            company_id=self.company,
            branch_id=self.branch,
            origin_type=origin_type,
            reverses_operation_id=reverses,
            reason="Anulación ficticia" if reverses else None,
            application_user_id=self.application_user_id,
        )
        movement = insert_movement(
            self._connection,
            operation,
            valued=False,
            id=movement_id or uuid4(),
            company_id=self.company,
            branch_id=self.branch,
            company_product_id=product,
            movement_type=movement_type,
            quantity=quantity,
            previous_balance=previous,
            new_balance=new,
            balance_sequence=version + 1,
            unit_cost=unit_cost,
            origin_type=origin_type,
            reversed_movement_id=reversed_movement,
            reason="Anulación ficticia" if reverses else None,
            application_user_id=self.application_user_id,
        )
        self.balances[product] = (new, version + 1)
        return operation, movement

    def entry(self, product: UUID, quantity, unit_cost=None, **ids) -> tuple[UUID, UUID]:
        cost = Decimal(str(unit_cost)) if unit_cost is not None else None
        return self._apply(product, "ENTRY", "PURCHASE_ENTRY", Decimal(str(quantity)), unit_cost=cost, **ids)

    def output(self, product: UUID, quantity, **ids) -> tuple[UUID, UUID]:
        return self._apply(product, "OUTPUT", "SALE_OUTPUT", Decimal(str(quantity)), **ids)

    def reverse_entry(self, product: UUID, entry: tuple[UUID, UUID], quantity, unit_cost=None) -> tuple[UUID, UUID]:
        cost = Decimal(str(unit_cost)) if unit_cost is not None else None
        return self._apply(
            product,
            "ENTRY_REVERSAL",
            "ENTRY_REVERSAL",
            Decimal(str(quantity)),
            unit_cost=cost,
            reverses=entry[0],
            reversed_movement=entry[1],
        )

    def flush_balances(self) -> None:
        """Escribe los saldos acumulados (`quantity`, `version`)."""
        for product, (quantity, version) in self.balances.items():
            self._connection.execute(
                text(
                    "INSERT INTO inventory_balances (company_id, branch_id, company_product_id, quantity, version, "
                    "created_by, updated_by) VALUES (:c, :b, :p, :q, :v, 'sub-fase-a', 'sub-fase-a') "
                    "ON CONFLICT (company_id, branch_id, company_product_id) DO UPDATE "
                    "SET quantity = EXCLUDED.quantity, version = EXCLUDED.version"
                ),
                {"c": self.company, "b": self.branch, "p": product, "q": quantity, "v": version},
            )
