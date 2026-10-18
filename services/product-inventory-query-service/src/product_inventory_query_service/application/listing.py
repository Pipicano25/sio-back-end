"""Ejecución común de los listados paginados (FR-022-130 a FR-022-140, FR-022-149 a FR-022-151; research R-05 a R-10).

Orden de cada solicitud:

1. Los parámetros ya validados (`QuerySpec`) y los bloques visibles llegan de la capa API; un filtro de un bloque
   no visible ya respondió `403`.
2. **Tanda 0**: membresía `ACTIVE` y sucursales en OC con el token del usuario (`authorize`). Ninguna llamada a
   CR, PC o Inventory sale antes.
3. Plan determinista en memoria (`planner.plan`).
4. Cursor: primera página, continuación o reinicio (`CursorCodec.evaluate`); un cursor inválido es `422`.
5. Búsqueda progresiva: el conductor del plan entrega lotes y los evaluadores los filtran.
6. Página (`derive_page`) y cursor nuevo `PAGE` o `SCAN`.

Los evaluadores se ejecutan en paralelo cuando conduce CR. Si conduce PC o Inventory, CR evalúa **primero** cada
lote (traducción entre `global_product_id` y `company_product_id`, adopción y filtros comerciales) y los demás
evaluadores trabajan solo sobre los candidatos que CR aceptó (FR-022-132, FR-022-139).

`RequestFacts` guarda, solo durante la solicitud, lo que ya respondieron las dependencias (productos de CR,
saldos, políticas y pares) para que el enriquecimiento no lo pida de nuevo (FR-022-137). No es una caché entre
solicitudes (FR-022-02).
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from product_inventory_query_service.application.authorization import AuthorizedScope, authorize
from product_inventory_query_service.application.call_registry import CallRegistry
from product_inventory_query_service.application.ports import (
    Balance,
    CatalogFilters,
    CommercialRelationshipPort,
    CompanyProduct,
    InventoryPort,
    OperationalContextPort,
    Policy,
    ProductCatalogPort,
    ProductCriteria,
)
from product_inventory_query_service.application.progressive_search import Evaluate, Fetch, progressive_search
from product_inventory_query_service.application.request_context import RequestBudget, request_budget
from product_inventory_query_service.domain.cursor import CursorCodec, Decision, Expected
from product_inventory_query_service.domain.fingerprint import fingerprint
from product_inventory_query_service.domain.pagination import Candidate, Page, SearchOutcome, derive_page
from product_inventory_query_service.domain.planner import BatchPolicy, Evaluator, QueryPlan, plan
from product_inventory_query_service.domain.query_spec import Endpoint, QuerySpec
from product_inventory_query_service.domain.routes import INVENTORY_DRIVING_MINIMUMS, Conductor
from product_inventory_query_service.domain.stock import ZERO, minimum_state
from product_inventory_query_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)

EVALUATOR_SORT_KEY = "display_name"
"""Orden de CR-1 en modo evaluador: no importa (solo se usa el conjunto aceptado), pero debe ser válido."""


@dataclass(frozen=True, slots=True)
class Ports:
    """Puertos de una solicitud. OC lleva el token del usuario; CR, PC e Inventory, la identidad técnica."""

    oc: OperationalContextPort
    cr: CommercialRelationshipPort
    pc: ProductCatalogPort
    inventory: InventoryPort


@dataclass(frozen=True, slots=True)
class Runtime:
    """Configuración de la ejecución (de `Settings`)."""

    codec: CursorCodec
    policy: BatchPolicy
    request_budget_seconds: float
    max_parallel_calls: int
    monotonic: Callable[[], float] = time.monotonic
    now: Callable[[], datetime] = lambda: datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class PairFacts:
    """Datos de un par (producto, sucursal) bajo mínimo, de INV-2 o calculados con `balances/lookup` e INV-1."""

    company_product_id: UUID
    branch_id: UUID
    base_quantity: Decimal
    minimum_stock: Decimal
    shortfall: Decimal


@dataclass
class RequestFacts:
    products: dict[UUID, CompanyProduct] = field(default_factory=dict)
    by_global: dict[UUID, CompanyProduct] = field(default_factory=dict)
    balances: dict[UUID, dict[UUID, Balance]] = field(default_factory=dict)
    policies: dict[UUID, dict[UUID, Policy | None]] = field(default_factory=dict)
    pairs: dict[tuple[UUID, UUID], PairFacts] = field(default_factory=dict)

    def remember(self, products: list[CompanyProduct]) -> None:
        for product in products:
            self.products[product.id] = product
            self.by_global[product.global_product_id] = product


class Gateway:
    """Acceso a las dependencias de una solicitud: sin llamadas repetidas y con lo ya obtenido reutilizado."""

    def __init__(self, ports: Ports, company_id: UUID, registry: CallRegistry) -> None:
        self.ports = ports
        self.company_id = company_id
        self.registry = registry
        self.facts = RequestFacts()

    async def balances(self, branch_id: UUID, ids: list[UUID]) -> dict[UUID, Balance]:
        known = self.facts.balances.setdefault(branch_id, {})
        missing = [i for i in dict.fromkeys(ids) if i not in known]
        if missing:
            found = await self.registry.once(
                "balances", (branch_id, missing),
                lambda: self.ports.inventory.balances(self.company_id, branch_id, missing),
            )
            for product_id in missing:
                # Un id sin elemento en la respuesta es un producto sin saldo registrado en la sucursal.
                known[product_id] = found.get(product_id) or Balance(product_id, branch_id, ZERO, False)
        return {i: known[i] for i in ids}

    async def policies(self, branch_id: UUID, ids: list[UUID]) -> dict[UUID, Policy | None]:
        known = self.facts.policies.setdefault(branch_id, {})
        missing = [i for i in dict.fromkeys(ids) if i not in known]
        if missing:
            found = await self.registry.once(
                "policies", (branch_id, missing),
                lambda: self.ports.inventory.policies(self.company_id, branch_id, missing),
            )
            for product_id in missing:
                known[product_id] = found.get(product_id)
        return {i: known[i] for i in ids}

    async def products(self, criteria: ProductCriteria, *, company_ids: list[UUID] | None = None,
                       global_ids: list[UUID] | None = None) -> list[CompanyProduct]:
        """CR-1 en modo evaluador (hasta 100 ids, un lote nunca pasa de 40 productos)."""
        size = len(company_ids or global_ids or [])
        if size == 0:
            return []
        found, _ = await self.registry.once(
            "search_products_evaluator", (criteria, company_ids, global_ids),
            lambda: self.ports.cr.search_products(
                self.company_id, criteria, sort_key=EVALUATOR_SORT_KEY, descending=False, limit=size,
                company_product_ids=company_ids, global_product_ids=global_ids,
            ),
        )
        self.facts.remember(found)
        return found


# --------------------------------------------------------------------------- filtros por propietario


def product_criteria(spec: QuerySpec) -> ProductCriteria:
    """Filtros comerciales (CR). En `inventory-overviews` CR exige siempre el control de inventario (FR-022-40)."""
    return ProductCriteria(
        status=spec.status,
        search=spec.search,
        internal_code=spec.internal_code,
        sku=spec.sku,
        inventory_control_enabled=True if spec.endpoint is Endpoint.INVENTORY_OVERVIEWS else None,
    )


def catalog_filters(spec: QuerySpec) -> CatalogFilters | None:
    """Filtros de catálogo (PC). `status = ALL`: un producto global inactivo sigue apareciendo con su estado global.

    `barcode` e `identifier` se comparan con el mismo campo de PC; si los dos llegan con valores distintos ningún
    producto puede cumplirlos y se devuelve `None` (resultado vacío, sin llamadas).
    """
    barcode = spec.barcode.strip() if spec.barcode else None
    identifier = spec.identifier.strip() if spec.identifier else None
    if barcode and identifier and barcode != identifier:
        return None
    return CatalogFilters(
        brand_ids=spec.brand_ids,
        category_ids=spec.category_ids,
        include_descendants=spec.include_descendants,
        identifier=barcode or identifier,
        product_type=spec.product_type,
        has_image=spec.has_image,
        status="ALL",
    )


# --------------------------------------------------------------------------- conductores


class Listing:
    """Una solicitud de listado: conductor, evaluadores y página."""

    def __init__(self, spec: QuerySpec, scope: AuthorizedScope, query_plan: QueryPlan, gateway: Gateway) -> None:
        self.spec = spec
        self.scope = scope
        self.plan = query_plan
        self.gateway = gateway
        self.criteria = product_criteria(spec)
        self.filters = catalog_filters(spec)
        self.branch_ids = scope.branch_ids

    # Identificadores de un candidato según el conductor.

    def company_id_of(self, candidate: Candidate) -> UUID | None:
        if self.plan.pairs:
            return candidate.key[0]
        if self.plan.conductor is Conductor.PC:
            product = self.gateway.facts.by_global.get(candidate.key)
            return product.id if product is not None else None
        return candidate.key

    def global_id_of(self, candidate: Candidate) -> UUID | None:
        if self.plan.conductor is Conductor.PC:
            return candidate.key
        product = self.gateway.facts.products.get(self.company_id_of(candidate))
        return product.global_product_id if product is not None else None

    def product_of(self, candidate: Candidate) -> CompanyProduct:
        return self.gateway.facts.products[self.company_id_of(candidate)]

    def fetch(self) -> Fetch:
        if self.filters is None:
            async def empty(after, limit):
                return [], False
            return empty
        if self.plan.conductor is Conductor.CR:
            return self._fetch_cr_pairs if self.plan.pairs else self._fetch_cr
        if self.plan.conductor is Conductor.PC:
            return self._fetch_pc
        return self._fetch_inventory_pairs if self.plan.pairs else self._fetch_inventory

    async def _cr_page(self, after: dict | None, limit: int) -> tuple[list[CompanyProduct], bool]:
        sort = self.plan.sort_effective
        products, has_more = await self.gateway.registry.once(
            "search_products", (self.criteria, sort.key, sort.descending, limit, after),
            lambda: self.gateway.ports.cr.search_products(
                self.gateway.company_id, self.criteria, sort_key=sort.key, descending=sort.descending, limit=limit,
                after=after,
            ),
        )
        self.gateway.facts.remember(products)
        return products, has_more

    async def _fetch_cr(self, after, limit):
        products, has_more = await self._cr_page(after, limit)
        return [Candidate(product.id, product.position, product) for product in products], has_more

    async def _fetch_cr_pairs(self, after, limit):
        """Bajo stock con `sort` explícito (R-F): CR conduce productos y cada uno se expande en sus pares.

        Cada par lleva la posición de CR de su producto (`p`), la del producto anterior (`prev`) y su sucursal
        (`b`). Para continuar se vuelve a pedir a CR desde `prev`: así reaparece el producto del último par y solo
        se toman sus sucursales posteriores a `b`. Las posiciones de CR se reenvían sin interpretarlas (R-06).
        """
        cr_after, resume = None, None
        if after is not None:
            cr_after, resume = after.get("prev"), (after.get("p"), after.get("b"))
        products, has_more = await self._cr_page(cr_after, limit)
        branches = sorted(self.branch_ids, key=str)
        candidates, previous = [], cr_after
        for product in products:
            for branch_id in branches:
                if resume is not None and product.position == resume[0] and str(branch_id) <= str(resume[1]):
                    continue
                position = {"p": product.position, "prev": previous, "b": str(branch_id)}
                candidates.append(Candidate((product.id, branch_id), position, product))
            previous = product.position
        return candidates, has_more

    async def _fetch_pc(self, after, limit):
        page, has_more = await self.gateway.registry.once(
            "match_page", (self.filters, limit, after),
            lambda: self.gateway.ports.pc.match_page(self.filters, limit=limit, after=after),
        )
        return [Candidate(global_id, position) for global_id, position in page], has_more

    async def _fetch_inventory(self, after, limit):
        if not self.branch_ids:
            return [], False
        stock = "IN_STOCK" if self.spec.stock_state == "IN_STOCK" else None
        minimum = self.spec.minimum_state if self.spec.minimum_state in INVENTORY_DRIVING_MINIMUMS else None
        page, has_more = await self.gateway.registry.once(
            "product_set", (self.branch_ids, stock, minimum, limit, after),
            lambda: self.gateway.ports.inventory.product_set(
                self.gateway.company_id, self.branch_ids, stock_state=stock, minimum_state=minimum, limit=limit,
                after=after,
            ),
        )
        return [Candidate(product_id, position) for product_id, position in page], has_more

    async def _fetch_inventory_pairs(self, after, limit):
        if not self.branch_ids:
            return [], False
        pairs, has_more = await self.gateway.registry.once(
            "below_minimum_pairs", (self.branch_ids, limit, after),
            lambda: self.gateway.ports.inventory.below_minimum_pairs(
                self.gateway.company_id, self.branch_ids, limit=limit, after=after,
            ),
        )
        candidates = []
        for pair in pairs:
            key = (pair.company_product_id, pair.branch_id)
            self.gateway.facts.pairs[key] = PairFacts(pair.company_product_id, pair.branch_id, pair.base_quantity,
                                                      pair.minimum_stock, pair.shortfall)
            candidates.append(Candidate(key, pair.position))
        return candidates, has_more

    # ----------------------------------------------------------------------- evaluadores

    def evaluators(self) -> list[Evaluate]:
        others = [self._evaluator(kind) for kind in self.plan.evaluators if kind is not Evaluator.CR]
        if Evaluator.CR not in self.plan.evaluators:
            return others  # conduce CR: todos en paralelo sobre el lote

        async def staged(candidates: list[Candidate]) -> set:
            accepted = await self._evaluate_cr(candidates)
            remaining = [c for c in candidates if c.key in accepted]
            if not remaining or not others:
                return accepted
            results = await asyncio.gather(*(evaluate(remaining) for evaluate in others))
            return set.intersection(accepted, *(set(result) for result in results))

        return [staged]

    def _evaluator(self, kind: Evaluator) -> Evaluate:
        return {
            Evaluator.PC: self._evaluate_pc,
            Evaluator.INVENTORY_STOCK: self._evaluate_stock,
            Evaluator.INVENTORY_MINIMUM: self._evaluate_minimum,
        }[kind]

    async def _evaluate_cr(self, candidates: list[Candidate]) -> set:
        if self.plan.conductor is Conductor.PC:
            ids = list(dict.fromkeys(c.key for c in candidates))
            accepted = {p.global_product_id for p in await self.gateway.products(self.criteria, global_ids=ids)}
            return {c.key for c in candidates if c.key in accepted}
        ids = list(dict.fromkeys(self.company_id_of(c) for c in candidates))
        accepted = {p.id for p in await self.gateway.products(self.criteria, company_ids=ids)}
        return {c.key for c in candidates if self.company_id_of(c) in accepted}

    async def _evaluate_pc(self, candidates: list[Candidate]) -> set:
        global_ids = {c.key: self.global_id_of(c) for c in candidates}
        ids = list(dict.fromkeys(g for g in global_ids.values() if g is not None))
        if not ids:
            return set()
        accepted = set(await self.gateway.registry.once(
            "match_candidates", (self.filters, ids),
            lambda: self.gateway.ports.pc.match_candidates(self.filters, ids),
        ))
        return {key for key, global_id in global_ids.items() if global_id in accepted}

    async def _evaluate_stock(self, candidates: list[Candidate]) -> set:
        ids = list(dict.fromkeys(self.company_id_of(c) for c in candidates))
        per_branch = await asyncio.gather(*(self.gateway.balances(b, ids) for b in self.branch_ids))
        totals = {i: sum((balances[i].quantity for balances in per_branch), ZERO) for i in ids}
        wanted_positive = self.spec.stock_state == "IN_STOCK"
        return {c.key for c in candidates if (totals[self.company_id_of(c)] > 0) == wanted_positive}

    async def _evaluate_minimum(self, candidates: list[Candidate]) -> set:
        """Estado frente al mínimo con `balances/lookup` e INV-1 (FR-022-50).

        - Listados: el producto cumple si al menos una sucursal del alcance tiene el estado pedido (como INV-2).
        - Bajo stock con CR conduciendo (R-F): el candidato es el par y cumple si está `BELOW_MINIMUM`.
        """
        ids = list(dict.fromkeys(self.company_id_of(c) for c in candidates))
        branches = self.branch_ids
        balances, policies = await asyncio.gather(
            asyncio.gather(*(self.gateway.balances(b, ids) for b in branches)),
            asyncio.gather(*(self.gateway.policies(b, ids) for b in branches)),
        )
        states: dict[tuple[UUID, UUID], str] = {}
        for index, branch_id in enumerate(branches):
            for product_id in ids:
                quantity = balances[index][product_id].quantity
                policy = policies[index][product_id]
                minimum = policy.minimum_stock if policy is not None else None
                states[(product_id, branch_id)] = minimum_state(quantity, minimum)
                if self.plan.pairs and minimum is not None and quantity < minimum:
                    self.gateway.facts.pairs[(product_id, branch_id)] = PairFacts(
                        product_id, branch_id, quantity, minimum, minimum - quantity)

        if self.plan.pairs:
            return {c.key for c in candidates if states.get(c.key) == "BELOW_MINIMUM"}
        wanted = self.spec.minimum_state
        return {
            c.key for c in candidates
            if any(states[(self.company_id_of(c), b)] == wanted for b in branches)
        }


# --------------------------------------------------------------------------- ejecución


@dataclass(frozen=True, slots=True)
class ListingResult:
    listing: Listing
    page: Page
    next_cursor: str | None
    reset_reason: str | None
    sort_applied: str
    resolved_at: datetime


async def run_listing(spec: QuerySpec, ports: Ports, runtime: Runtime, *,
                      enrich: Callable[[Listing, Page], Awaitable[Any]]) -> tuple[ListingResult, Any]:
    """Autoriza, planifica, valida el cursor, busca, pagina y enriquece; registra el plan (FR-022-140)."""
    budget = RequestBudget(runtime.request_budget_seconds, runtime.max_parallel_calls, clock=runtime.monotonic)
    resolved_at = runtime.now()
    registry = CallRegistry()
    try:
        with request_budget(budget):
            scope = await authorize(ports.oc, spec.company_id, list(spec.branch_ids) if spec.branch_ids else None)
            query_plan = plan(spec, runtime.policy)
            expected = Expected(spec.endpoint.value, str(spec.company_id), fingerprint(spec), query_plan.sort_applied,
                                spec.page_size, query_plan.route.value)
            decision = runtime.codec.evaluate(spec.cursor, expected)
            after = decision.payload.pos if decision.decision is Decision.CONTINUE else None
            reset = decision.reason.value if decision.decision is Decision.RESET else None

            listing = Listing(spec, scope, query_plan, Gateway(ports, spec.company_id, registry))
            outcome: SearchOutcome = await progressive_search(
                listing.fetch(), listing.evaluators(), need=query_plan.need, batch_size=query_plan.batch_size,
                max_batches=query_plan.max_batches, work_time_seconds=query_plan.work_time_seconds, after=after,
                started_at=budget.started_at, clock=runtime.monotonic,
            )
            page = derive_page(outcome, spec.page_size)
            next_cursor = None
            if page.has_next:
                next_cursor = runtime.codec.issue(expected, kind=page.cursor_kind, position=page.cursor_position)
            result = ListingResult(listing, page, next_cursor, reset, query_plan.sort_applied, resolved_at)
            enriched = await enrich(listing, page)
    finally:
        registry.close()

    logger.info(
        "Plan ejecutado endpoint=%s ruta=%s lotes=%d examinados=%d validos=%d entregados=%d llamadas=%d "
        "duracion_ms=%d parcial=%s tipo_continuacion=%s reinicio=%s",
        spec.endpoint.value, query_plan.route.value, outcome.batches, outcome.examined, len(outcome.valid),
        len(page.items), sum(registry.executed.values()), int(budget.elapsed() * 1000), page.partial,
        page.cursor_kind or "-", reset or "-",
    )
    return result, enriched
