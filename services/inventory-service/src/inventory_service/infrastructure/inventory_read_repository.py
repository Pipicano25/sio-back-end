"""Lecturas de la spec 022 sobre `inventory_balances` e `inventory_policies` (INV-1, INV-2, INV-3).

Solo lectura: no hay migraciones, columnas nuevas ni cambios en las operaciones de escritura (D-022-10).
Toda consulta filtra por la empresa de la ruta. Las agregaciones y la comparación *keyset* las hace
PostgreSQL; la aplicación no recorre saldos.

Definiciones (spec 022, FR-022-55):
- Saldo positivo: fila de saldo con cantidad `> 0`; consolidado: suma en las sucursales pedidas `> 0`.
- Saldo registrado en cero: fila con cantidad `= 0`; consolidado: al menos una fila y suma `= 0`. Un
  producto sin fila de saldo nunca cuenta aquí.
- Política: política de producto activa. Un par con política y sin fila de saldo cuenta con cantidad 0.
- Bajo mínimo: par con política activa y cantidad `<` mínimo; consolidado: productos con al menos un par.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, and_, cast, distinct, func, literal, null, or_, select, tuple_, union_all
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Session

from inventory_service.infrastructure.models import InventoryBalance, InventoryPolicy

ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class PolicyRow:
    id: UUID
    company_product_id: UUID
    minimum_stock: Decimal


@dataclass(frozen=True, slots=True)
class PairRow:
    company_product_id: UUID
    branch_id: UUID
    base_quantity: Decimal
    minimum_stock: Decimal
    shortfall: Decimal


@dataclass(frozen=True, slots=True)
class SummaryRow:
    branch_id: UUID | None
    positive: int
    zero: int
    with_policy: int
    below_minimum: int
    inventory_value: Decimal


class InventoryReadRepository:
    """Consultas de solo lectura de INV-1, INV-2 e INV-3."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------------- comunes

    def _balances(self, company_id: UUID, branch_ids: list[UUID]):
        balance = InventoryBalance
        return (
            select(balance.branch_id, balance.company_product_id, balance.quantity, balance.inventory_value)
            .where(balance.company_id == company_id, balance.branch_id.in_(branch_ids))
            .cte("bal")
        )

    def _pairs(self, company_id: UUID, branch_ids: list[UUID]):
        policy, balance = InventoryPolicy, InventoryBalance
        return (
            select(
                policy.branch_id,
                policy.company_product_id,
                policy.minimum_stock,
                func.coalesce(balance.quantity, ZERO).label("quantity"),
            )
            .select_from(
                policy.__table__.outerjoin(
                    balance.__table__,
                    and_(
                        balance.company_id == policy.company_id,
                        balance.branch_id == policy.branch_id,
                        balance.company_product_id == policy.company_product_id,
                    ),
                )
            )
            .where(policy.company_id == company_id, policy.branch_id.in_(branch_ids), policy.is_active.is_(True))
            .cte("pol")
        )

    # ------------------------------------------------------------------------- INV-1

    def active_policies(self, company_id: UUID, branch_id: UUID, product_ids: list[UUID]) -> dict[UUID, PolicyRow]:
        policy = InventoryPolicy
        try:
            rows = self._session.execute(
                select(policy.id, policy.company_product_id, policy.minimum_stock).where(
                    policy.company_id == company_id,
                    policy.branch_id == branch_id,
                    policy.company_product_id.in_(product_ids),
                    policy.is_active.is_(True),
                )
            ).all()
            return {row.company_product_id: PolicyRow(row.id, row.company_product_id, row.minimum_stock) for row in rows}
        finally:
            self._session.rollback()

    # ------------------------------------------------------------------------- INV-2

    def product_set(
        self,
        company_id: UUID,
        branch_ids: list[UUID],
        *,
        stock_state: str | None,
        minimum_state: str | None,
        after: UUID | None,
        limit: int,
    ) -> tuple[list[UUID], bool]:
        bal = self._balances(company_id, branch_ids)
        pol = self._pairs(company_id, branch_ids)
        totals = (
            select(bal.c.company_product_id, func.sum(bal.c.quantity).label("total"))
            .group_by(bal.c.company_product_id)
            .cte("totals")
        )
        in_stock = select(totals.c.company_product_id).where(totals.c.total > 0)
        minimum = _minimum_products(pol, minimum_state)

        statement: Select
        if stock_state is not None:
            statement = in_stock
            product = totals.c.company_product_id
            if minimum is not None:
                statement = statement.where(product.in_(minimum))
        else:
            statement = minimum.distinct()
            product = pol.c.company_product_id

        if after is not None:
            statement = statement.where(product > after)

        try:
            rows = list(self._session.execute(statement.order_by(product).limit(limit + 1)).scalars())
            return rows[:limit], len(rows) > limit
        finally:
            self._session.rollback()

    def below_minimum_pairs(
        self,
        company_id: UUID,
        branch_ids: list[UUID],
        *,
        after: tuple[Decimal, UUID, UUID] | None,
        limit: int,
    ) -> tuple[list[PairRow], bool]:
        pol = self._pairs(company_id, branch_ids)
        shortfall = (pol.c.minimum_stock - pol.c.quantity).label("shortfall")
        statement = select(
            pol.c.company_product_id, pol.c.branch_id, pol.c.quantity, pol.c.minimum_stock, shortfall
        ).where(pol.c.quantity < pol.c.minimum_stock)

        if after is not None:
            value, product_id, branch_id = after
            gap = pol.c.minimum_stock - pol.c.quantity
            statement = statement.where(
                or_(
                    gap < value,
                    and_(gap == value, tuple_(pol.c.company_product_id, pol.c.branch_id) > tuple_(product_id, branch_id)),
                )
            )

        statement = statement.order_by(shortfall.desc(), pol.c.company_product_id, pol.c.branch_id).limit(limit + 1)
        try:
            rows = [
                PairRow(row.company_product_id, row.branch_id, row.quantity, row.minimum_stock, row.shortfall)
                for row in self._session.execute(statement)
            ]
            return rows[:limit], len(rows) > limit
        finally:
            self._session.rollback()

    # ------------------------------------------------------------------------- INV-3

    def summary(self, company_id: UUID, branch_ids: list[UUID]) -> list[SummaryRow]:
        """Indicadores por sucursal y consolidados en **una** consulta agregada (FR-022-57)."""
        bal = self._balances(company_id, branch_ids)
        pol = self._pairs(company_id, branch_ids)
        totals = (
            select(bal.c.company_product_id, func.sum(bal.c.quantity).label("total"))
            .group_by(bal.c.company_product_id)
            .cte("totals")
        )
        by_branch_balance = (
            select(
                bal.c.branch_id,
                func.count().filter(bal.c.quantity > 0).label("positive"),
                func.count().filter(bal.c.quantity == 0).label("zero"),
                func.coalesce(func.sum(bal.c.inventory_value), ZERO).label("value"),
            )
            .group_by(bal.c.branch_id)
            .subquery("bb")
        )
        by_branch_policy = (
            select(
                pol.c.branch_id,
                func.count().label("with_policy"),
                func.count().filter(pol.c.quantity < pol.c.minimum_stock).label("below"),
            )
            .group_by(pol.c.branch_id)
            .subquery("bp")
        )
        branch = func.coalesce(by_branch_balance.c.branch_id, by_branch_policy.c.branch_id)
        per_branch = select(
            literal("B").label("kind"),
            branch.label("branch_id"),
            func.coalesce(by_branch_balance.c.positive, 0).label("positive"),
            func.coalesce(by_branch_balance.c.zero, 0).label("zero"),
            func.coalesce(by_branch_policy.c.with_policy, 0).label("with_policy"),
            func.coalesce(by_branch_policy.c.below, 0).label("below"),
            func.coalesce(by_branch_balance.c.value, ZERO).label("value"),
        ).select_from(
            by_branch_balance.join(
                by_branch_policy, by_branch_balance.c.branch_id == by_branch_policy.c.branch_id, full=True
            )
        )
        consolidated = select(
            literal("C").label("kind"),
            cast(null(), PG_UUID(as_uuid=True)).label("branch_id"),
            select(func.count()).select_from(totals).where(totals.c.total > 0).scalar_subquery(),
            select(func.count()).select_from(totals).where(totals.c.total == 0).scalar_subquery(),
            select(func.count(distinct(pol.c.company_product_id))).scalar_subquery(),
            select(func.count(distinct(pol.c.company_product_id)))
            .where(pol.c.quantity < pol.c.minimum_stock)
            .scalar_subquery(),
            select(func.coalesce(func.sum(bal.c.inventory_value), ZERO)).scalar_subquery(),
        )
        statement = union_all(per_branch, consolidated)
        try:
            return [
                SummaryRow(
                    branch_id=row.branch_id,
                    positive=int(row.positive),
                    zero=int(row.zero),
                    with_policy=int(row.with_policy),
                    below_minimum=int(row.below),
                    inventory_value=Decimal(row.value),
                )
                for row in self._session.execute(statement)
            ]
        finally:
            self._session.rollback()


def _minimum_products(pol, state: str | None) -> Select | None:
    """Productos con al menos un par del alcance en el estado pedido."""
    if state is None:
        return None
    product = select(pol.c.company_product_id)
    if state == "WITH_POLICY":
        return product
    condition = {
        "BELOW_MINIMUM": pol.c.quantity < pol.c.minimum_stock,
        "AT_MINIMUM": pol.c.quantity == pol.c.minimum_stock,
        "ABOVE_MINIMUM": pol.c.quantity > pol.c.minimum_stock,
    }[state]
    return product.where(condition)
