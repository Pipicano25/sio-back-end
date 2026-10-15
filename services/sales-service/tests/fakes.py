"""Dobles de las dependencias, inyectados por DI en `create_app` (Principio IV, R-19).

`World` reúne datos ficticios coherentes de las cinco dependencias. Cada doble registra
sus llamadas y admite modos "no disponible" (lanza `DependencyUnavailableError` como el
adaptador real) y "falla si se llama".

- `FakeCommercial` resuelve el precio aplicable como el contrato 010 §6 con la spec 019: solo el
  precio explícito de la presentación en la lista indicada o en la predeterminada (base
  `PRESENTATION`); `NO_PRICE_IN_LIST`, `NO_APPLICABLE_PRICE_LIST`, `PRICE_LIST_NOT_APPLICABLE`,
  `NOT_FOUND`. Sin `sale_price` ni precios generales por producto.
- `FakeInventory` reproduce el contrato de Inventory (012 + 013) para salidas: capas FIFO
  por sucursal y producto con costo conocido o desconocido, `409 INSUFFICIENT_STOCK` con
  `shortages`, idempotencia por `operation_key` (`409 OPERATION_KEY_CONFLICT` con otra
  solicitud), costo informado por movimiento (`unit_cost` por unidad base, `movement_value`,
  `cost_known`), reverso exacto por `id` que restituye las capas, consulta por clave y saldos.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID, uuid4

import jwt

from sales_service.application.exceptions import (
    COMMERCIAL_RELATIONSHIP,
    INVENTORY,
    OPERATIONAL_CONTEXT,
    PARTY_IDENTITY,
    PAYMENT_REFERENCE,
    PRODUCT_CATALOG,
    DependencyUnavailableError,
)
from sales_service.application.ports import (
    AccessResult,
    ApplicationUserInfo,
    BalanceInfo,
    BranchInfo,
    CompanyInfo,
    CompanyPresentationInfo,
    CompanyProductInfo,
    CustomerInfo,
    Directories,
    GlobalPresentationInfo,
    GlobalProductInfo,
    IdentityInfo,
    InventoryOperationRef,
    InventoryRejection,
    MovementCost,
    PaymentMethodInfo,
    PriceListInfo,
    ResolvedPrice,
    UnitInfo,
)

Q4 = Decimal("0.0001")


class Unavailable:
    """Control de disponibilidad compartido por un doble."""

    def __init__(self, provider: str) -> None:
        self.provider = provider
        self.down = False
        self.fail_if_called = False
        self.latency = 0.0
        self.calls: list[tuple[str, Any]] = []
        self.lock = threading.Lock()

    def hit(self, operation: str, argument: Any = None) -> None:
        with self.lock:
            self.calls.append((operation, argument))
        if self.fail_if_called:
            raise AssertionError(f"{self.provider}.{operation} no debía llamarse")
        if self.latency:
            time.sleep(self.latency)
        if self.down:
            raise DependencyUnavailableError(self.provider, operation=operation, cause="doble_no_disponible")


def subject_of(authorization: str | None) -> str | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    claims = jwt.decode(authorization.split(" ", 1)[1], options={"verify_signature": False})
    return claims.get("sub")


@dataclass
class World:
    """Datos ficticios coherentes (empresa COP, sucursales A y B, clientes, productos, listas)."""

    company: UUID = field(default_factory=uuid4)
    other_company: UUID = field(default_factory=uuid4)
    branch: UUID = field(default_factory=uuid4)
    branch_b: UUID = field(default_factory=uuid4)
    customer: UUID = field(default_factory=uuid4)
    customer_org: UUID = field(default_factory=uuid4)
    person: UUID = field(default_factory=uuid4)
    organization: UUID = field(default_factory=uuid4)
    product: UUID = field(default_factory=uuid4)
    product_2: UUID = field(default_factory=uuid4)
    product_no_inventory: UUID = field(default_factory=uuid4)
    global_product: UUID = field(default_factory=uuid4)
    global_product_2: UUID = field(default_factory=uuid4)
    presentation: UUID = field(default_factory=uuid4)
    global_presentation: UUID = field(default_factory=uuid4)
    unit: UUID = field(default_factory=uuid4)
    price_list: UUID = field(default_factory=uuid4)
    price_list_2: UUID = field(default_factory=uuid4)
    item_box: UUID = field(default_factory=uuid4)
    item_product_2: UUID = field(default_factory=uuid4)
    # Spec 019: cada producto se vende por presentación; la unidad base, con su presentación de factor 1.
    unit_presentation: UUID = field(default_factory=uuid4)
    unit_presentation_2: UUID = field(default_factory=uuid4)
    unit_presentation_ni: UUID = field(default_factory=uuid4)
    global_unit: UUID = field(default_factory=uuid4)
    global_unit_2: UUID = field(default_factory=uuid4)
    default_list: UUID = field(default_factory=uuid4)
    item_unit: UUID = field(default_factory=uuid4)
    item_unit_2: UUID = field(default_factory=uuid4)
    item_unit_ni: UUID = field(default_factory=uuid4)
    item_box_default: UUID = field(default_factory=uuid4)
    # Spec 020: medio de pago declarado (activo e inactivo) de Payment Reference.
    payment_method: UUID = field(default_factory=uuid4)
    inactive_payment_method: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        UNIT_PRESENTATION_OF.update({
            self.product: self.unit_presentation,
            self.product_2: self.unit_presentation_2,
            self.product_no_inventory: self.unit_presentation_ni,
        })


# Producto → su presentación de factor 1 (la usa `line()` de conftest cuando una prueba no indica presentación).
UNIT_PRESENTATION_OF: dict[UUID, UUID] = {}


class FakeOperationalContext:
    def __init__(self, world: World) -> None:
        self.world = world
        self.availability = Unavailable(OPERATIONAL_CONTEXT)
        self.companies: dict[UUID, CompanyInfo] = {
            world.company: CompanyInfo(world.company, "ACTIVE", "COP"),
            world.other_company: CompanyInfo(world.other_company, "ACTIVE", "COP"),
        }
        self.branches: dict[UUID, BranchInfo] = {
            world.branch: BranchInfo(world.branch, world.company, "ACTIVE", "America/Bogota"),
            world.branch_b: BranchInfo(world.branch_b, world.company, "ACTIVE", "America/Bogota"),
        }
        self.users: dict[UUID, ApplicationUserInfo] = {}
        self.members: dict[tuple[str, UUID], UUID] = {}
        self.assignments: set[tuple[str, UUID]] = set()
        self.access_down = False
        self.access_forbidden: set[str] = set()
        self.access_calls: list[tuple[str | None, str, UUID]] = []

    def add_member(
        self, sub: str, company: UUID, *, branches: tuple[UUID, ...] = (), status: str = "ACTIVE", user_id: UUID | None = None
    ) -> UUID:
        user_id = self.members.get((sub, company)) or user_id or uuid4()
        self.members[(sub, company)] = user_id
        self.users[user_id] = ApplicationUserInfo(user_id, company, status)
        for branch in branches:
            self.assignments.add((sub, branch))
        return user_id

    # Directorio técnico
    def get_company(self, company_id: UUID) -> CompanyInfo | None:
        self.availability.hit("company", company_id)
        return self.companies.get(company_id)

    def get_branch(self, branch_id: UUID) -> BranchInfo | None:
        self.availability.hit("branch", branch_id)
        return self.branches.get(branch_id)

    def get_application_user(self, application_user_id: UUID) -> ApplicationUserInfo | None:
        self.availability.hit("application_user", application_user_id)
        return self.users.get(application_user_id)

    def access_for(self, request) -> FakeAccess:
        return FakeAccess(self, request.headers.get("authorization"))


class FakeAccess:
    def __init__(self, oc: FakeOperationalContext, authorization: str | None) -> None:
        self.oc = oc
        self.authorization = authorization
        self.sub = subject_of(authorization)

    def _guard(self, kind: str, target: UUID) -> None:
        self.oc.access_calls.append((self.authorization, kind, target))
        if self.oc.access_down:
            raise DependencyUnavailableError(OPERATIONAL_CONTEXT, operation="operational_access", cause="doble")
        if self.sub in self.oc.access_forbidden:
            from sales_service.application.exceptions import OperationalAccessDeniedError

            raise OperationalAccessDeniedError()

    def check_branch(self, branch_id: UUID) -> AccessResult:
        self._guard("branch", branch_id)
        branch = self.oc.branches.get(branch_id)
        company = branch.company_id if branch else None
        user = self.oc.members.get((self.sub, company)) if company else None
        if branch is None or user is None:
            return AccessResult(False, "USER_NOT_MEMBER", company, None)
        if (self.sub, branch_id) not in self.oc.assignments:
            return AccessResult(False, "BRANCH_NOT_ASSIGNED", company, user)
        if branch.status != "ACTIVE":
            return AccessResult(False, "BRANCH_INACTIVE", company, user)
        return AccessResult(True, None, company, user)

    def check_company(self, company_id: UUID) -> AccessResult:
        self._guard("company", company_id)
        user = self.oc.members.get((self.sub, company_id))
        if user is None:
            return AccessResult(False, "USER_NOT_MEMBER", company_id, None)
        return AccessResult(True, None, company_id, user)


@dataclass
class ListItem:
    id: UUID
    unit_price: Decimal
    currency_code: str = "COP"


class FakeCommercial:
    def __init__(self, world: World) -> None:
        self.world = world
        self.availability = Unavailable(COMMERCIAL_RELATIONSHIP)
        self.customers = {
            world.customer: CustomerInfo(
                world.customer, world.company, "PERSON", world.person, None, "Ana Ficticia Pérez", "ACTIVE"
            ),
            world.customer_org: CustomerInfo(
                world.customer_org, world.company, "ORGANIZATION", None, world.organization,
                "Tiendas Ficticias S.A.S.", "ACTIVE",
            ),
        }
        self.products = {
            world.product: CompanyProductInfo(
                world.product, world.company, world.global_product, "000045", "Arroz ficticio 500 g", True, True, "ACTIVE"
            ),
            world.product_2: CompanyProductInfo(
                world.product_2, world.company, world.global_product_2, "000046", "Aceite ficticio 1 L", True, True, "ACTIVE"
            ),
            world.product_no_inventory: CompanyProductInfo(
                world.product_no_inventory, world.company, world.global_product_2, "000099", "Servicio ficticio", True, False, "ACTIVE"
            ),
        }
        self.presentations = {
            world.presentation: CompanyPresentationInfo(
                world.presentation, world.company, world.product, world.global_presentation, True, "ACTIVE"
            ),
            world.unit_presentation: CompanyPresentationInfo(
                world.unit_presentation, world.company, world.product, world.global_unit, True, "ACTIVE"
            ),
            world.unit_presentation_2: CompanyPresentationInfo(
                world.unit_presentation_2, world.company, world.product_2, world.global_unit_2, True, "ACTIVE"
            ),
            world.unit_presentation_ni: CompanyPresentationInfo(
                world.unit_presentation_ni, world.company, world.product_no_inventory, world.global_unit_2, True, "ACTIVE"
            ),
        }
        self.price_lists: dict[UUID, PriceListInfo] = {
            world.default_list: PriceListInfo(world.default_list, world.company, "ACTIVE"),
            world.price_list: PriceListInfo(world.price_list, world.company, "ACTIVE"),
            world.price_list_2: PriceListInfo(world.price_list_2, world.company, "ACTIVE"),
        }
        self.list_applicable: dict[UUID, bool] = {world.default_list: True, world.price_list: True, world.price_list_2: True}
        # (lista, producto, presentación) → ítem: siempre el precio explícito de una presentación (spec 019).
        self.items: dict[tuple[UUID, UUID, UUID], ListItem] = {
            (world.default_list, world.product, world.unit_presentation): ListItem(world.item_unit, Decimal("1500.00")),
            (world.default_list, world.product_2, world.unit_presentation_2): ListItem(world.item_unit_2, Decimal("9000.00")),
            (world.default_list, world.product_no_inventory, world.unit_presentation_ni): ListItem(world.item_unit_ni, Decimal("50000.00")),
            # La caja también tiene su precio explícito en GENERAL (antes salía de 1500 × 12; spec 019: sin conversión).
            (world.default_list, world.product, world.presentation): ListItem(world.item_box_default, Decimal("18000.00")),
            (world.price_list, world.product, world.presentation): ListItem(world.item_box, Decimal("16000.00")),
            (world.price_list, world.product_2, world.unit_presentation_2): ListItem(world.item_product_2, Decimal("8500.00")),
        }
        # Lista predeterminada vigente en la moneda del producto (`None`: no hay → NO_APPLICABLE_PRICE_LIST).
        self.default_list: UUID | None = world.default_list

    def get_customer(self, customer_id: UUID) -> CustomerInfo | None:
        self.availability.hit("customer", customer_id)
        return self.customers.get(customer_id)

    def lookup_products(self, ids) -> dict[UUID, CompanyProductInfo]:
        self.availability.hit("products", tuple(ids))
        return {value: self.products[value] for value in ids if value in self.products}

    def lookup_presentations(self, ids) -> dict[UUID, CompanyPresentationInfo]:
        self.availability.hit("presentations", tuple(ids))
        return {value: self.presentations[value] for value in ids if value in self.presentations}

    def get_price_list(self, price_list_id: UUID) -> PriceListInfo | None:
        self.availability.hit("price_list", price_list_id)
        return self.price_lists.get(price_list_id)

    def set_price(self, price_list: UUID, product: UUID, presentation: UUID, price: str, item: UUID | None = None,
                  currency_code: str = "COP") -> UUID:
        item_id = item or uuid4()
        self.items[(price_list, product, presentation)] = ListItem(item_id, Decimal(price), currency_code)
        return item_id

    def set_unit_price(self, product: UUID, price: str | None, currency_code: str = "COP") -> UUID | None:
        """Precio de la presentación de factor 1 del producto en la lista predeterminada (`None` lo retira)."""
        key = (self.world.default_list, product, UNIT_PRESENTATION_OF[product])
        if price is None:
            self.items.pop(key, None)
            return None
        return self.set_price(*key, price, currency_code=currency_code)

    def _item(self, price_list: UUID, product: UUID, presentation: UUID | None) -> ListItem | None:
        return self.items.get((price_list, product, presentation)) if presentation is not None else None

    def resolve_prices(self, company_id: UUID, lines, at) -> dict[str, ResolvedPrice]:
        self.availability.hit("applicable_prices", tuple(lines))
        result: dict[str, ResolvedPrice] = {}
        for line in lines:
            empty = dict(basis=None, unit_price=None, currency_code=None, price_list_id=None, price_list_item_id=None)
            product = self.products.get(line.company_product_id)
            presentation = (
                self.presentations.get(line.company_product_presentation_id)
                if line.company_product_presentation_id
                else None
            )
            if (
                product is None
                or product.company_id != company_id
                or (line.company_product_presentation_id and (presentation is None or presentation.company_product_id != product.id))
            ):
                result[line.line_id] = ResolvedPrice(line.line_id, False, "NOT_FOUND", **empty)
                continue
            if line.price_list_id is not None:
                price_list = self.price_lists.get(line.price_list_id)
                if (
                    price_list is None
                    or price_list.company_id != company_id
                    or price_list.status != "ACTIVE"
                    or not self.list_applicable.get(line.price_list_id, True)
                ):
                    result[line.line_id] = ResolvedPrice(line.line_id, True, "PRICE_LIST_NOT_APPLICABLE", **empty)
                    continue
                item = self._item(line.price_list_id, product.id, line.company_product_presentation_id)
                if item is None:
                    result[line.line_id] = ResolvedPrice(line.line_id, True, "NO_PRICE_IN_LIST", **empty)
                    continue
                result[line.line_id] = ResolvedPrice(
                    line.line_id, True, "PRICE_LIST_ITEM", "PRESENTATION", item.unit_price, item.currency_code, line.price_list_id, item.id
                )
                continue
            if self.default_list is None or not self.list_applicable.get(self.default_list, True):
                result[line.line_id] = ResolvedPrice(line.line_id, True, "NO_APPLICABLE_PRICE_LIST", **empty)
                continue
            item = self._item(self.default_list, product.id, line.company_product_presentation_id)
            if item is None:
                result[line.line_id] = ResolvedPrice(line.line_id, True, "NO_PRICE_IN_LIST", **empty)
                continue
            result[line.line_id] = ResolvedPrice(
                line.line_id, True, "PRICE_LIST_ITEM", "PRESENTATION", item.unit_price, item.currency_code, self.default_list, item.id
            )
        return result


class FakeCatalog:
    def __init__(self, world: World) -> None:
        self.availability = Unavailable(PRODUCT_CATALOG)
        self.presentations = {
            world.global_presentation: GlobalPresentationInfo(world.global_presentation, "CAJA12", "Caja x12", Decimal("12")),
            world.global_unit: GlobalPresentationInfo(world.global_unit, "UND", "Unidad", Decimal("1")),
            world.global_unit_2: GlobalPresentationInfo(world.global_unit_2, "UND", "Unidad", Decimal("1")),
        }
        self.products = {
            world.global_product: GlobalProductInfo(world.global_product, world.unit),
            world.global_product_2: GlobalProductInfo(world.global_product_2, world.unit),
        }
        self.units = {world.unit: UnitInfo(world.unit, "UND")}

    def get_presentation(self, presentation_id: UUID):
        self.availability.hit("presentation", presentation_id)
        return self.presentations.get(presentation_id)

    def get_product(self, product_id: UUID):
        self.availability.hit("product", product_id)
        return self.products.get(product_id)

    def get_unit(self, unit_id: UUID):
        self.availability.hit("unit", unit_id)
        return self.units.get(unit_id)


class FakeParty:
    def __init__(self, world: World) -> None:
        self.availability = Unavailable(PARTY_IDENTITY)
        self.persons = {world.person: IdentityInfo(world.person, "CC", "1020304050")}
        self.organizations = {world.organization: IdentityInfo(world.organization, "NIT", "900123456")}

    def get_person(self, person_id: UUID):
        self.availability.hit("person", person_id)
        return self.persons.get(person_id)

    def get_organization(self, organization_id: UUID):
        self.availability.hit("organization", organization_id)
        return self.organizations.get(organization_id)


class FakePaymentReference:
    def __init__(self, world: World) -> None:
        self.availability = Unavailable(PAYMENT_REFERENCE)
        self.methods = build_methods(world)

    def get_payment_method(self, method_id: UUID):
        self.availability.hit("payment_method", method_id)
        return self.methods.get(method_id)


def build_methods(world: World) -> dict[UUID, PaymentMethodInfo]:
    return {
        world.payment_method: PaymentMethodInfo(world.payment_method, "CASH", "Efectivo", "ACTIVE"),
        world.inactive_payment_method: PaymentMethodInfo(world.inactive_payment_method, "CHECK", "Cheque", "INACTIVE"),
    }


def _canonical(payload: dict[str, Any]) -> Any:
    def norm(value):
        if isinstance(value, dict):
            return {key: norm(item) for key, item in sorted(value.items())}
        if isinstance(value, list):
            return [norm(item) for item in value]
        if isinstance(value, str):
            try:
                return str(Decimal(value).normalize()) if any(ch.isdigit() for ch in value) and "-" not in value else value
            except Exception:  # noqa: BLE001
                return value
        return value

    return norm(payload)


@dataclass
class Layer:
    quantity: Decimal
    unit_cost: Decimal
    known: bool = True


@dataclass
class StoredOperation:
    ref: InventoryOperationRef
    key: str
    payload: dict[str, Any]
    kind: str
    company_id: str
    consumed: list[list[tuple[Decimal, Decimal, bool]]] = field(default_factory=list)
    reversed_by: UUID | None = None


class FakeInventory:
    """Contrato de Inventory (012 + 013) para salidas, con capas FIFO en memoria."""

    def __init__(self) -> None:
        self.availability = Unavailable(INVENTORY)
        self.by_key: dict[str, StoredOperation] = {}
        self.by_id: dict[UUID, StoredOperation] = {}
        self.layers: dict[tuple[str, str], list[Layer]] = {}
        self.reject_output: tuple[int, str] | None = None
        self.lose_response = 0  # aplica y responde como no disponible (respuesta perdida)
        self.output_calls = 0
        self.lock = threading.Lock()

    # ------------------------------------------------------------- datos

    def stock(self, branch: UUID, product: UUID, quantity: str, unit_cost: str = "1000", *, known: bool = True) -> None:
        """Agrega una capa FIFO (equivale a una entrada previa)."""
        self.layers.setdefault((str(branch), str(product)), []).append(Layer(Decimal(quantity), Decimal(unit_cost), known))

    def balance(self, branch: UUID, product: UUID) -> Decimal:
        return sum((layer.quantity for layer in self.layers.get((str(branch), str(product)), [])), Decimal("0"))

    def value(self, branch: UUID, product: UUID) -> Decimal:
        return sum(
            (layer.quantity * layer.unit_cost for layer in self.layers.get((str(branch), str(product)), [])), Decimal("0")
        )

    def outputs(self) -> list[StoredOperation]:
        return [item for item in self.by_key.values() if item.kind == "OUTPUT"]

    def _maybe_lose(self, operation: str) -> None:
        if self.lose_response > 0:
            self.lose_response -= 1
            raise DependencyUnavailableError(INVENTORY, operation=operation, cause="respuesta_perdida")

    # ------------------------------------------------------------ puerto

    def lookup_balances(self, company_id: UUID, branch_id: UUID, product_ids) -> dict[UUID, BalanceInfo]:
        self.availability.hit("balances", tuple(product_ids))
        return {product: BalanceInfo(product, self.balance(branch_id, product)) for product in product_ids}

    def apply_output(self, payload: dict[str, Any]) -> InventoryOperationRef:
        self.availability.hit("output", payload)
        with self.lock:
            self.output_calls += 1
            key = payload["operation_key"]
            existing = self.by_key.get(key)
            if existing is not None:
                if _canonical(existing.payload) != _canonical(payload):
                    raise InventoryRejection(409, "OPERATION_KEY_CONFLICT")
                result = existing.ref
            else:
                if self.reject_output is not None:
                    status, code = self.reject_output
                    raise InventoryRejection(status, code)
                for line in payload["lines"]:
                    assert "unit_cost" not in line, "unit_cost no se admite en salidas (contrato 012)"
                branch = payload["branch_id"]
                requested: dict[str, tuple[int, Decimal]] = {}
                for index, line in enumerate(payload["lines"]):
                    first, total = requested.get(line["company_product_id"], (index, Decimal("0")))
                    requested[line["company_product_id"]] = (first, total + Decimal(line["quantity"]))
                shortages = [
                    {
                        "index": first,
                        "company_product_id": product,
                        "available": format(self.balance(branch, product).quantize(Q4), "f"),
                        "requested": format(total.quantize(Q4), "f"),
                    }
                    for product, (first, total) in requested.items()
                    if self.balance(branch, product) < total
                ]
                if shortages:
                    raise InventoryRejection(409, "INSUFFICIENT_STOCK", {"code": "INVENTORY.INSUFFICIENT_STOCK", "shortages": shortages})
                movements: list[MovementCost] = []
                consumed_all = []
                for line in payload["lines"]:
                    quantity = Decimal(line["quantity"])
                    consumed = self._consume(branch, line["company_product_id"], quantity)
                    consumed_all.append(consumed)
                    value = sum((qty * cost for qty, cost, _ in consumed), Decimal("0")).quantize(Q4, rounding=ROUND_HALF_UP)
                    known = all(flag for _, _, flag in consumed)
                    movements.append(
                        MovementCost(
                            UUID(line["origin_detail_id"]),
                            (value / quantity).quantize(Q4, rounding=ROUND_HALF_UP),
                            value,
                            known,
                        )
                    )
                stored = StoredOperation(
                    InventoryOperationRef(uuid4(), "OUTPUT", None, tuple(movements)),
                    key,
                    payload,
                    "OUTPUT",
                    payload["company_id"],
                    consumed_all,
                )
                self.by_key[key] = stored
                self.by_id[stored.ref.id] = stored
                result = stored.ref
        self._maybe_lose("inventory_output")
        return result

    def _consume(self, branch: str, product: str, quantity: Decimal) -> list[tuple[Decimal, Decimal, bool]]:
        layers = self.layers.get((branch, product), [])
        pending = quantity
        consumed = []
        while pending > 0:
            layer = layers[0]
            take = min(layer.quantity, pending)
            consumed.append((take, layer.unit_cost, layer.known))
            layer.quantity -= take
            pending -= take
            if layer.quantity == 0:
                layers.pop(0)
        return consumed

    def reverse_output(self, operation_id: UUID, payload: dict[str, Any]) -> InventoryOperationRef:
        self.availability.hit("reversal", (operation_id, payload))
        with self.lock:
            key = payload["operation_key"]
            existing = self.by_key.get(key)
            if existing is not None:
                if _canonical(existing.payload) != _canonical({**payload, "target": str(operation_id)}):
                    raise InventoryRejection(409, "OPERATION_KEY_CONFLICT")
                result = existing.ref
            else:
                output = self.by_id.get(operation_id)
                if output is None or output.kind != "OUTPUT" or output.company_id != payload["company_id"]:
                    raise InventoryRejection(404, "NOT_FOUND")
                if output.reversed_by is not None:
                    raise InventoryRejection(409, "ALREADY_REVERSED")
                branch = output.payload["branch_id"]
                for line, consumed in zip(output.payload["lines"], output.consumed, strict=True):
                    layers = self.layers.setdefault((branch, line["company_product_id"]), [])
                    for qty, cost, known in reversed(consumed):
                        layers.insert(0, Layer(qty, cost, known))
                stored = StoredOperation(
                    InventoryOperationRef(uuid4(), "OUTPUT_REVERSAL", operation_id),
                    key,
                    {**payload, "target": str(operation_id)},
                    "OUTPUT_REVERSAL",
                    payload["company_id"],
                )
                output.reversed_by = stored.ref.id
                self.by_key[key] = stored
                self.by_id[stored.ref.id] = stored
                result = stored.ref
        self._maybe_lose("inventory_output_reversal")
        return result

    def find_by_key(self, company_id: UUID, operation_key: UUID) -> InventoryOperationRef | None:
        self.availability.hit("by_key", operation_key)
        stored = self.by_key.get(str(operation_key))
        if stored is None or stored.company_id != str(company_id):
            return None
        return stored.ref


@dataclass
class Fakes:
    world: World
    oc: FakeOperationalContext
    cr: FakeCommercial
    catalog: FakeCatalog
    party: FakeParty
    inventory: FakeInventory
    pr: FakePaymentReference

    def directories(self) -> Directories:
        return Directories(self.oc, self.cr, self.catalog, self.party, self.pr)

    def all_availability(self) -> list[Unavailable]:
        return [
            self.oc.availability,
            self.cr.availability,
            self.catalog.availability,
            self.party.availability,
            self.inventory.availability,
            self.pr.availability,
        ]


def build_fakes(world: World | None = None) -> Fakes:
    world = world or World()
    inventory = FakeInventory()
    # Existencias de partida en la sucursal A (costo conocido).
    inventory.stock(world.branch, world.product, "1000", "1000")
    inventory.stock(world.branch, world.product_2, "1000", "6000")
    return Fakes(
        world=world,
        oc=FakeOperationalContext(world),
        cr=FakeCommercial(world),
        catalog=FakeCatalog(world),
        party=FakeParty(world),
        inventory=inventory,
        pr=FakePaymentReference(world),
    )


def today() -> date:
    return date.today()
