"""Dobles de los puertos (Principio IV; T066).

Implementan la semántica de los contratos sobre datos en memoria: orden y posición *keyset* de los conductores,
modo evaluador, saldos sin costo y políticas activas. Cada llamada queda registrada con su operación y sus
argumentos normalizados para verificar que no hay llamadas repetidas ni proporcionales al número de productos.
Un doble puede configurarse para fallar (`fail`) o para no admitir ciertas operaciones (`forbidden`).
"""

from __future__ import annotations

import asyncio
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from product_inventory_query_service.application.call_registry import normalize
from product_inventory_query_service.application.exceptions import DependencyUnavailableError
from product_inventory_query_service.application.ports import (
    Balance,
    BelowMinimumPair,
    BranchInfo,
    CatalogFilters,
    Category,
    CompanyPresentation,
    CompanyProduct,
    Identifier,
    InventorySummary,
    Policy,
    PresentationInfo,
    PriceLine,
    PriceResult,
    ProductCriteria,
    ProductSummary,
    Reference,
    SummaryCounts,
)


@dataclass
class CallLog:
    """Registro de llamadas: (operación, argumentos normalizados) → veces."""

    calls: Counter = field(default_factory=Counter)
    order: list[str] = field(default_factory=list)

    def record(self, operation: str, arguments: object = ()) -> None:
        self.calls[(operation, normalize(arguments))] += 1
        self.order.append(operation)

    def count(self, operation: str) -> int:
        return sum(times for (name, _), times in self.calls.items() if name == operation)

    def total(self) -> int:
        return sum(self.calls.values())

    def repeated(self) -> list:
        return [key for key, times in self.calls.items() if times > 1]


class _Fake:
    provider = "fake"

    def __init__(self, log: CallLog) -> None:
        self.log = log
        self.fail: set[str] = set()
        self.forbidden: set[str] = set()

    async def _enter(self, operation: str, arguments: object = ()) -> None:
        if operation in self.forbidden:
            raise AssertionError(f"Llamada no permitida en esta prueba: {operation}")
        self.log.record(operation, arguments)
        await asyncio.sleep(0)
        if operation in self.fail or "*" in self.fail:
            raise DependencyUnavailableError(self.provider, operation, "falla_simulada")


# --------------------------------------------------------------------------- Operational Context


class FakeOperationalContext(_Fake):
    provider = "operational-context"

    def __init__(self, log: CallLog) -> None:
        super().__init__(log)
        self.members: set[UUID] = set()
        self.branch_rows: dict[UUID, list[BranchInfo]] = {}

    def add_company(self, *, member: bool = True, branches: int = 2, inactive: int = 0) -> tuple[UUID, list[UUID]]:
        company = uuid4()
        if member:
            self.members.add(company)
        rows = [BranchInfo(uuid4(), company, "ACTIVE") for _ in range(branches)]
        rows += [BranchInfo(uuid4(), company, "INACTIVE") for _ in range(inactive)]
        self.branch_rows[company] = rows
        return company, [row.id for row in rows]

    async def has_company_access(self, company_id: UUID) -> bool:
        await self._enter("operational_access", company_id)
        return company_id in self.members

    async def branches(self, company_id: UUID, *, status: str) -> list[BranchInfo]:
        await self._enter("branches", (company_id, status))
        if company_id not in self.members:
            return []
        return [row for row in self.branch_rows.get(company_id, []) if row.status == status]


# --------------------------------------------------------------------------- Commercial Relationship


SORT_VALUE = {
    "display_name": lambda p: p.display_name,
    "internal_code": lambda p: p.internal_code,
    "created_at": lambda p: p.created_at.isoformat(),
}


class FakeCommercialRelationship(_Fake):
    provider = "commercial-relationship"

    def __init__(self, log: CallLog) -> None:
        super().__init__(log)
        self.products: list[CompanyProduct] = []
        self.presentations: list[CompanyPresentation] = []
        self.skus: dict[UUID, set[str]] = {}
        self.prices: dict[UUID, PriceResult] = {}
        self.price_lists_requested: set[UUID | None] = set()
        self._clock = datetime(2026, 10, 1, tzinfo=UTC)

    def add_product(self, company_id: UUID, display_name: str, *, global_product_id: UUID | None = None, **kwargs) -> CompanyProduct:
        self._clock += timedelta(seconds=1)
        product = CompanyProduct(
            id=kwargs.pop("id", uuid4()),
            company_id=company_id,
            global_product_id=global_product_id or uuid4(),
            internal_code=kwargs.pop("internal_code", f"C{len(self.products):05d}"),
            reference_code=kwargs.pop("reference_code", None),
            display_name=display_name,
            status=kwargs.pop("status", "ACTIVE"),
            is_sellable=kwargs.pop("is_sellable", True),
            is_purchasable=kwargs.pop("is_purchasable", True),
            inventory_control_enabled=kwargs.pop("inventory_control_enabled", True),
            created_at=kwargs.pop("created_at", self._clock),
        )
        assert not kwargs, kwargs
        self.products.append(product)
        return product

    def add_presentation(self, product: CompanyProduct, global_presentation_id: UUID, *, sku: str | None = None,
                         internal_code: str | None = None, status: str = "ACTIVE", is_sellable: bool = True,
                         company_id: UUID | None = None, id: UUID | None = None) -> CompanyPresentation:
        presentation = CompanyPresentation(
            id=id or uuid4(), company_id=company_id or product.company_id, company_product_id=product.id,
            global_product_presentation_id=global_presentation_id, internal_code=internal_code, sku=sku,
            reference_code=None, is_sellable=is_sellable, status=status,
        )
        self.presentations.append(presentation)
        if sku:
            self.skus.setdefault(product.id, set()).add(sku)
        return presentation

    def set_price(self, presentation: CompanyPresentation, unit_price: str, *, price_list_id: UUID | None = None,
                  resolution: str = "PRICE_LIST_ITEM", currency_code: str = "COP",
                  price_list_item_id: UUID | None = None) -> PriceResult:
        price = PriceResult(presentation.id, resolution, unit_price, currency_code, price_list_id or uuid4(),
                            price_list_item_id or uuid4())
        self.prices[presentation.id] = price
        return price

    def _matches(self, product: CompanyProduct, criteria: ProductCriteria) -> bool:
        if criteria.status != "ALL" and product.status != criteria.status:
            return False
        if criteria.inventory_control_enabled is not None and product.inventory_control_enabled != criteria.inventory_control_enabled:
            return False
        if criteria.search:
            term = criteria.search.lower()
            fields = [product.display_name, product.internal_code, product.reference_code or ""]
            fields += list(self.skus.get(product.id, ()))
            if not any(term in value.lower() for value in fields):
                return False
        if criteria.internal_code and product.internal_code.lower() != criteria.internal_code.lower():
            return False
        if criteria.sku and criteria.sku.lower() not in {s.lower() for s in self.skus.get(product.id, ())}:
            return False
        return True

    async def search_products(self, company_id, criteria, *, sort_key, descending, limit, after=None,
                              company_product_ids=None, global_product_ids=None):
        await self._enter("search_products", (company_id, criteria, sort_key, descending, limit, after,
                                              company_product_ids, global_product_ids))
        value = SORT_VALUE[sort_key]
        rows = [p for p in self.products if p.company_id == company_id and self._matches(p, criteria)]
        if company_product_ids is not None:
            rows = [p for p in rows if p.id in set(company_product_ids)]
        if global_product_ids is not None:
            rows = [p for p in rows if p.global_product_id in set(global_product_ids)]
        rows.sort(key=lambda p: (value(p), str(p.id)), reverse=descending)
        if after is not None:
            bound = (after["k"][0], str(after["id"]))
            rows = [p for p in rows if ((value(p), str(p.id)) < bound if descending else (value(p), str(p.id)) > bound)]
        page = rows[: limit + 1]
        result = [_with_position(p, {"k": [value(p)], "id": str(p.id)}) for p in page[:limit]]
        return result, len(page) > limit

    async def presentations_by_products(self, company_id, company_product_ids):
        await self._enter("presentations_by_products", (company_id, list(company_product_ids)))
        wanted = set(company_product_ids)
        rows = [p for p in self.presentations if p.company_id == company_id and p.company_product_id in wanted]
        return sorted(rows, key=lambda p: (str(p.company_product_id), str(p.id)))

    async def resolve_prices(self, company_id, lines: list[PriceLine]):
        await self._enter("resolve_prices", (company_id, [(line.company_product_presentation_id, line.price_list_id)
                                                          for line in lines]))
        self.price_lists_requested.update(line.price_list_id for line in lines)
        results = []
        for line in lines:
            price = self.prices.get(line.company_product_presentation_id)
            if price is not None and line.price_list_id is not None and price.price_list_id != line.price_list_id:
                price = None  # una sola lista: el precio de otra lista nunca se usa (FR-022-33)
            results.append(price or PriceResult(line.company_product_presentation_id, "NO_PRICE_IN_LIST", None, None,
                                                line.price_list_id, None))
        return results

    async def count_adopted(self, company_id):
        await self._enter("count_adopted", company_id)
        return sum(1 for p in self.products if p.company_id == company_id and p.status == "ACTIVE" and p.inventory_control_enabled)


def _with_position(product: CompanyProduct, position: dict) -> CompanyProduct:
    from dataclasses import replace

    return replace(product, position=position)


# --------------------------------------------------------------------------- Product Catalog


class FakeProductCatalog(_Fake):
    provider = "product-catalog"

    def __init__(self, log: CallLog) -> None:
        super().__init__(log)
        self.products: dict[UUID, ProductSummary] = {}
        self.brand_of: dict[UUID, UUID | None] = {}
        self.categories_of: dict[UUID, set[UUID]] = {}
        self.identifiers_of: dict[UUID, set[str]] = {}
        self.units_by_id: dict[UUID, Reference] = {}
        self.presentation_rows: dict[UUID, PresentationInfo] = {}

    def add_product(self, product_id: UUID, name: str, *, brand_id: UUID | None = None, has_image: bool = False,
                    categories: set[UUID] | None = None, identifiers: set[str] | None = None, status: str = "ACTIVE",
                    base_unit: Reference | None = None, product_type: str = "GOOD") -> ProductSummary:
        summary = ProductSummary(
            id=product_id, canonical_name=name, product_type=product_type, status=status,
            brand=Reference(brand_id, "MARCA", "Marca") if brand_id else None, base_unit=base_unit,
            categories=tuple(Category(c, f"CAT-{str(c)[:4]}", "Categoría", index == 0)
                             for index, c in enumerate(sorted(categories or set(), key=str))),
            identifiers=tuple(Identifier("GTIN", value, index == 0, None)
                              for index, value in enumerate(sorted(identifiers or set()))),
            has_image=has_image,
            image_url=f"https://catalogo.sio.test/api/v1/public/product-images?ref=r{product_id.hex[:8]}" if has_image else None,
        )
        self.products[product_id] = summary
        self.brand_of[product_id] = brand_id
        self.categories_of[product_id] = categories or set()
        self.identifiers_of[product_id] = identifiers or set()
        return summary

    def _matches(self, product_id: UUID, filters: CatalogFilters) -> bool:
        summary = self.products.get(product_id)
        if summary is None:
            return False
        if filters.status != "ALL" and summary.status != filters.status:
            return False
        if filters.brand_ids and self.brand_of.get(product_id) not in set(filters.brand_ids):
            return False
        if filters.category_ids and not (self.categories_of.get(product_id, set()) & set(filters.category_ids)):
            return False
        if filters.identifier and filters.identifier not in self.identifiers_of.get(product_id, set()):
            return False
        if filters.product_type and summary.product_type != filters.product_type:
            return False
        if filters.has_image is not None and summary.has_image != filters.has_image:
            return False
        return True

    async def summaries(self, ids):
        await self._enter("summaries", list(ids))
        return {i: self.products[i] for i in ids if i in self.products}

    async def match_candidates(self, filters, candidate_ids):
        await self._enter("match_candidates", (filters, list(candidate_ids)))
        return [i for i in dict.fromkeys(candidate_ids) if self._matches(i, filters)]

    async def match_page(self, filters, *, limit, after=None):
        await self._enter("match_page", (filters, limit, after))
        rows = sorted((p for p in self.products if self._matches(p, filters)),
                      key=lambda i: (self.products[i].canonical_name.lower(), str(i)))
        if after is not None:
            bound = (after["k"][0], str(after["id"]))
            rows = [i for i in rows if (self.products[i].canonical_name.lower(), str(i)) > bound]
        page = rows[: limit + 1]
        return [(i, {"k": [self.products[i].canonical_name.lower()], "id": str(i)}) for i in page[:limit]], len(page) > limit

    async def units(self, ids):
        await self._enter("units", list(ids))
        return {i: self.units_by_id[i] for i in ids if i in self.units_by_id}

    def add_presentation(self, product_id: UUID, code: str, name: str, factor: str | None,
                         status: str = "ACTIVE", id: UUID | None = None) -> PresentationInfo:
        info = PresentationInfo(id or uuid4(), product_id, code, name, status, None if factor is None else Decimal(factor))
        self.presentation_rows[info.id] = info
        return info

    async def presentations(self, ids):
        await self._enter("presentations", list(ids))
        return {i: self.presentation_rows[i] for i in dict.fromkeys(ids) if i in self.presentation_rows}


# --------------------------------------------------------------------------- Inventory


class FakeInventory(_Fake):
    provider = "inventory"

    def __init__(self, log: CallLog) -> None:
        super().__init__(log)
        self.quantities: dict[tuple[UUID, UUID, UUID], Decimal] = {}
        self.minimums: dict[tuple[UUID, UUID, UUID], Decimal] = {}

    def set_balance(self, company: UUID, branch: UUID, product: UUID, quantity: str) -> None:
        self.quantities[(company, branch, product)] = Decimal(quantity)

    def set_policy(self, company: UUID, branch: UUID, product: UUID, minimum: str) -> None:
        self.minimums[(company, branch, product)] = Decimal(minimum)

    async def balances(self, company_id, branch_id, ids):
        await self._enter("balances", (company_id, branch_id, list(ids)))
        result = {}
        for product in dict.fromkeys(ids):
            key = (company_id, branch_id, product)
            result[product] = Balance(product, branch_id, self.quantities.get(key, Decimal("0")), key in self.quantities)
        return result

    async def policies(self, company_id, branch_id, ids):
        await self._enter("policies", (company_id, branch_id, list(ids)))
        return {
            product: Policy(product, branch_id, self.minimums[(company_id, branch_id, product)])
            for product in dict.fromkeys(ids)
            if (company_id, branch_id, product) in self.minimums
        }

    def _products(self, company_id, branch_ids, stock_state, minimum_state) -> list[UUID]:
        products = {p for (c, b, p) in list(self.quantities) + list(self.minimums) if c == company_id and b in branch_ids}
        result = []
        for product in products:
            total = sum(self.quantities.get((company_id, b, product), Decimal("0")) for b in branch_ids)
            if stock_state == "IN_STOCK" and not total > 0:
                continue
            if minimum_state is not None:
                states = []
                for branch in branch_ids:
                    if (company_id, branch, product) not in self.minimums:
                        continue
                    quantity = self.quantities.get((company_id, branch, product), Decimal("0"))
                    minimum = self.minimums[(company_id, branch, product)]
                    states.append("BELOW_MINIMUM" if quantity < minimum else "AT_MINIMUM" if quantity == minimum else "ABOVE_MINIMUM")
                if minimum_state == "WITH_POLICY" and not states:
                    continue
                if minimum_state != "WITH_POLICY" and minimum_state not in states:
                    continue
            result.append(product)
        return sorted(result, key=str)

    async def product_set(self, company_id, branch_ids, *, stock_state, minimum_state, limit, after=None):
        await self._enter("product_set", (company_id, list(branch_ids), stock_state, minimum_state, limit, after))
        rows = self._products(company_id, list(branch_ids), stock_state, minimum_state)
        if after is not None:
            rows = [p for p in rows if str(p) > str(after["id"])]
        page = rows[: limit + 1]
        return [(p, {"k": [], "id": str(p)}) for p in page[:limit]], len(page) > limit

    async def below_minimum_pairs(self, company_id, branch_ids, *, limit, after=None):
        await self._enter("below_minimum_pairs", (company_id, list(branch_ids), limit, after))
        pairs = []
        for (c, b, p), minimum in self.minimums.items():
            if c != company_id or b not in branch_ids:
                continue
            quantity = self.quantities.get((c, b, p), Decimal("0"))
            if quantity < minimum:
                pairs.append(BelowMinimumPair(p, b, quantity, minimum, minimum - quantity))
        pairs.sort(key=lambda x: (-x.shortfall, str(x.company_product_id), str(x.branch_id)))
        if after is not None:
            bound = (-Decimal(after["k"][0]), str(after["id"]), str(after["branch_id"]))
            pairs = [x for x in pairs if (-x.shortfall, str(x.company_product_id), str(x.branch_id)) > bound]
        page = pairs[: limit + 1]
        return [
            _with_pair_position(x) for x in page[:limit]
        ], len(page) > limit

    async def summary(self, company_id, branch_ids):
        """Las definiciones de INV-3 (FR-022-55) sobre los datos en memoria."""
        await self._enter("summary", (company_id, list(branch_ids)))

        def counts(branches) -> SummaryCounts:
            balances = {(b, p): q for (c, b, p), q in self.quantities.items() if c == company_id and b in branches}
            policies = {(b, p): m for (c, b, p), m in self.minimums.items() if c == company_id and b in branches}
            products = {p for (_, p) in balances}
            totals = {p: sum(q for (_, p2), q in balances.items() if p2 == p) for p in products}
            below = {p for (b, p), m in policies.items() if balances.get((b, p), Decimal("0")) < m}
            return SummaryCounts(
                products_with_positive_balance=sum(1 for t in totals.values() if t > 0),
                products_with_zero_balance=sum(1 for t in totals.values() if t == 0),
                products_with_policy=len({p for (_, p) in policies}),
                products_below_minimum=len(below),
            )

        return InventorySummary(branches={b: counts({b}) for b in branch_ids}, consolidated=counts(set(branch_ids)))


def _with_pair_position(pair: BelowMinimumPair) -> BelowMinimumPair:
    from dataclasses import replace

    return replace(pair, position={"k": [format(pair.shortfall, "f")], "id": str(pair.company_product_id),
                                   "branch_id": str(pair.branch_id)})


@dataclass
class Fakes:
    log: CallLog
    oc: FakeOperationalContext
    cr: FakeCommercialRelationship
    pc: FakeProductCatalog
    inventory: FakeInventory


def build_fakes() -> Fakes:
    log = CallLog()
    return Fakes(log, FakeOperationalContext(log), FakeCommercialRelationship(log), FakeProductCatalog(log), FakeInventory(log))
