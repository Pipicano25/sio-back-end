"""Dobles de las dependencias, inyectados por DI en `create_app` (Principio IV, R-17).

`World` reúne datos ficticios coherentes de las seis dependencias. Cada doble registra
sus llamadas y admite modos "no disponible" (lanza `DependencyUnavailableError` como el
adaptador real) y "falla si se llama". `FakeInventory` reproduce el contrato de
Inventory: idempotencia por `operation_key` con la misma solicitud, `409
OPERATION_KEY_CONFLICT` con otra, reverso exacto por `id`, `ENTRY_LAYER_CONSUMED`,
consulta por clave y saldos por sucursal y producto.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import jwt

from purchase_service.application.exceptions import (
    COMMERCIAL_RELATIONSHIP,
    INVENTORY,
    OPERATIONAL_CONTEXT,
    PARTY_IDENTITY,
    PAYMENT_REFERENCE,
    PRODUCT_CATALOG,
    DependencyUnavailableError,
)
from purchase_service.application.ports import (
    AccessResult,
    ApplicationUserInfo,
    BranchInfo,
    CompanyInfo,
    CompanyPresentationInfo,
    CompanyProductInfo,
    Directories,
    GlobalPresentationInfo,
    GlobalProductInfo,
    InventoryOperationRef,
    InventoryRejection,
    OrganizationInfo,
    PaymentConditionInfo,
    PaymentConditionTypeInfo,
    PaymentMethodInfo,
    SupplierInfo,
    SupplierProductInfo,
    UnitInfo,
)


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


UNIT_NAMESPACE = uuid5(NAMESPACE_URL, "sio:purchase-tests:unit-presentation")


def unit_presentation_of(product: UUID | str) -> UUID:
    """Presentación de empresa de factor 1 de un producto ficticio (spec 020: toda línea con presentación)."""
    return uuid5(UNIT_NAMESPACE, f"company:{product}")


def global_unit_presentation_of(product: UUID | str) -> UUID:
    return uuid5(UNIT_NAMESPACE, f"global:{product}")


@dataclass
class World:
    """Datos ficticios coherentes (empresa COP, sucursales A y B, proveedor, productos).

    Spec 020: `condition` es de contado (la única admitida); `credit_condition` y
    `financing_condition` existen para comprobar su rechazo. Cada producto tiene su presentación
    de factor 1 (`unit_presentation_of`) y hay un medio de pago activo y otro inactivo.
    """

    company: UUID = field(default_factory=uuid4)
    other_company: UUID = field(default_factory=uuid4)
    branch: UUID = field(default_factory=uuid4)
    branch_b: UUID = field(default_factory=uuid4)
    supplier: UUID = field(default_factory=uuid4)
    organization: UUID = field(default_factory=uuid4)
    condition: UUID = field(default_factory=uuid4)
    credit_condition: UUID = field(default_factory=uuid4)
    financing_condition: UUID = field(default_factory=uuid4)
    cash_type: UUID = field(default_factory=uuid4)
    credit_type: UUID = field(default_factory=uuid4)
    financing_type: UUID = field(default_factory=uuid4)
    payment_method: UUID = field(default_factory=uuid4)
    inactive_payment_method: UUID = field(default_factory=uuid4)
    product: UUID = field(default_factory=uuid4)
    product_2: UUID = field(default_factory=uuid4)
    product_no_inventory: UUID = field(default_factory=uuid4)
    global_product: UUID = field(default_factory=uuid4)
    global_product_2: UUID = field(default_factory=uuid4)
    presentation: UUID = field(default_factory=uuid4)
    global_presentation: UUID = field(default_factory=uuid4)
    supplier_product: UUID = field(default_factory=uuid4)
    unit: UUID = field(default_factory=uuid4)


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
        user_id = user_id or uuid4()
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
            from purchase_service.application.exceptions import OperationalAccessDeniedError

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


class FakeCommercial:
    def __init__(self, world: World) -> None:
        self.availability = Unavailable(COMMERCIAL_RELATIONSHIP)
        self.uncovered: set[UUID] = set()  # spec 021: presentaciones sin política de ganancia aplicable
        self.suppliers = {world.supplier: SupplierInfo(world.supplier, world.company, world.organization, "Distribuidora Ficticia S.A.S.", "ACTIVE")}
        self.conditions = {
            world.condition: PaymentConditionInfo(
                world.condition, world.company, world.supplier, world.cash_type, "COP", 0, None, None, "ACTIVE"
            ),
            world.credit_condition: PaymentConditionInfo(
                world.credit_condition, world.company, world.supplier, world.credit_type, "COP", 30, None, None, "ACTIVE"
            ),
            world.financing_condition: PaymentConditionInfo(
                world.financing_condition, world.company, world.supplier, world.financing_type, "COP", 60, None, None, "ACTIVE"
            ),
        }
        self.products = {
            # Spec 021: tasas de impuesto de compra ficticias (el 19 % no es una tarifa real).
            world.product: CompanyProductInfo(
                world.product, world.company, world.global_product, "000045", "Arroz ficticio 500 g", True, True, "ACTIVE",
                Decimal("19"),
            ),
            world.product_2: CompanyProductInfo(
                world.product_2, world.company, world.global_product_2, "000046", "Aceite ficticio 1 L", True, True, "ACTIVE",
                Decimal("0"),
            ),
            world.product_no_inventory: CompanyProductInfo(
                world.product_no_inventory, world.company, world.global_product_2, "000099", "Servicio ficticio", True, False,
                "ACTIVE", Decimal("0"),
            ),
        }
        self.presentations = {
            world.presentation: CompanyPresentationInfo(
                world.presentation, world.company, world.product, world.global_presentation, True, "ACTIVE"
            )
        }
        for product in (world.product, world.product_2, world.product_no_inventory):
            unit = unit_presentation_of(product)
            self.presentations[unit] = CompanyPresentationInfo(
                unit, world.company, product, global_unit_presentation_of(product), True, "ACTIVE"
            )
        self.supplier_products = {
            world.supplier_product: SupplierProductInfo(
                world.supplier_product, world.company, world.supplier, world.product, None, Decimal("48.50"), "ACTIVE"
            )
        }

    def get_supplier(self, supplier_id: UUID) -> SupplierInfo | None:
        self.availability.hit("supplier", supplier_id)
        return self.suppliers.get(supplier_id)

    def get_payment_condition(self, condition_id: UUID) -> PaymentConditionInfo | None:
        self.availability.hit("condition", condition_id)
        return self.conditions.get(condition_id)

    def lookup_products(self, ids) -> dict[UUID, CompanyProductInfo]:
        self.availability.hit("products", tuple(ids))
        return {value: self.products[value] for value in ids if value in self.products}

    def lookup_presentations(self, ids) -> dict[UUID, CompanyPresentationInfo]:
        self.availability.hit("presentations", tuple(ids))
        return {value: self.presentations[value] for value in ids if value in self.presentations}

    def lookup_pricing_coverage(self, company_id: UUID, currency_code: str, ids) -> dict[UUID, bool]:
        """Spec 021 (FR-021-35): por omisión toda presentación de la empresa está cubierta; `uncovered` las excluye."""
        self.availability.hit("pricing_coverage", (company_id, currency_code, tuple(ids)))
        return {
            value: value in self.presentations
            and self.presentations[value].company_id == company_id
            and value not in self.uncovered
            for value in ids
        }

    def get_supplier_product(self, supplier_product_id: UUID) -> SupplierProductInfo | None:
        self.availability.hit("supplier_product", supplier_product_id)
        return self.supplier_products.get(supplier_product_id)


class FakeCatalog:
    def __init__(self, world: World) -> None:
        self.availability = Unavailable(PRODUCT_CATALOG)
        self.presentations = {
            world.global_presentation: GlobalPresentationInfo(world.global_presentation, "CAJA12", "Caja x12", Decimal("12"))
        }
        for product in (world.product, world.product_2, world.product_no_inventory):
            unit = global_unit_presentation_of(product)
            self.presentations[unit] = GlobalPresentationInfo(unit, "UND", "Unidad", Decimal("1"))
        self.products = {
            world.global_product: GlobalProductInfo(world.global_product, world.unit),
            world.global_product_2: GlobalProductInfo(world.global_product_2, world.unit),
        }
        self.units = {world.unit: UnitInfo(world.unit, "UND")}

    def lookup_presentations(self, ids):
        self.availability.hit("presentations", tuple(ids))
        return {value: self.presentations[value] for value in dict.fromkeys(ids) if value in self.presentations}

    def get_product(self, product_id: UUID):
        self.availability.hit("product", product_id)
        return self.products.get(product_id)

    def get_unit(self, unit_id: UUID):
        self.availability.hit("unit", unit_id)
        return self.units.get(unit_id)


class FakeParty:
    def __init__(self, world: World) -> None:
        self.availability = Unavailable(PARTY_IDENTITY)
        self.organizations = {world.organization: OrganizationInfo(world.organization, "NIT", "900123456")}

    def get_organization(self, organization_id: UUID):
        self.availability.hit("organization", organization_id)
        return self.organizations.get(organization_id)


def build_methods(world: World) -> dict[UUID, PaymentMethodInfo]:
    return {
        world.payment_method: PaymentMethodInfo(world.payment_method, "CASH", "Efectivo", "ACTIVE"),
        world.inactive_payment_method: PaymentMethodInfo(world.inactive_payment_method, "CHECK", "Cheque", "INACTIVE"),
    }


class FakePaymentReference:
    def __init__(self, world: World) -> None:
        self.availability = Unavailable(PAYMENT_REFERENCE)
        self.types = {
            world.cash_type: PaymentConditionTypeInfo(world.cash_type, "CASH", "ACTIVE"),
            world.credit_type: PaymentConditionTypeInfo(world.credit_type, "CREDIT", "ACTIVE"),
            world.financing_type: PaymentConditionTypeInfo(world.financing_type, "FINANCING", "ACTIVE"),
        }
        self.methods = build_methods(world)

    def get_condition_type(self, type_id: UUID):
        self.availability.hit("condition_type", type_id)
        return self.types.get(type_id)

    def get_payment_method(self, method_id: UUID):
        self.availability.hit("payment_method", method_id)
        return self.methods.get(method_id)


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
class StoredOperation:
    ref: InventoryOperationRef
    key: str
    payload: dict[str, Any]
    kind: str
    company_id: str
    reversed_by: UUID | None = None


class FakeInventory:
    """Contrato de Inventory (012 + 013) con estado en memoria."""

    def __init__(self) -> None:
        self.availability = Unavailable(INVENTORY)
        self.by_key: dict[str, StoredOperation] = {}
        self.by_id: dict[UUID, StoredOperation] = {}
        self.balances: dict[tuple[str, str], Decimal] = {}
        self.consumed: set[UUID] = set()
        self.reject_entry: tuple[int, str] | None = None
        self.lose_response = 0  # aplica y responde como no disponible (respuesta perdida)
        self.entry_calls = 0
        self.lock = threading.Lock()

    def _maybe_lose(self, operation: str) -> None:
        if self.lose_response > 0:
            self.lose_response -= 1
            raise DependencyUnavailableError(INVENTORY, operation=operation, cause="respuesta_perdida")

    def apply_entry(self, payload: dict[str, Any]) -> InventoryOperationRef:
        self.availability.hit("entry", payload)
        with self.lock:
            self.entry_calls += 1
            key = payload["operation_key"]
            existing = self.by_key.get(key)
            if existing is not None:
                if _canonical(existing.payload) != _canonical(payload):
                    raise InventoryRejection(409, "OPERATION_KEY_CONFLICT")
                result = existing.ref
            else:
                if self.reject_entry is not None:
                    status, code = self.reject_entry
                    raise InventoryRejection(status, code)
                for line in payload["lines"]:
                    assert "unit_cost" in line, "unit_cost es obligatorio (delta 013)"
                    slot = (payload["branch_id"], line["company_product_id"])
                    self.balances[slot] = self.balances.get(slot, Decimal("0")) + Decimal(line["quantity"])
                stored = StoredOperation(InventoryOperationRef(uuid4(), "ENTRY"), key, payload, "ENTRY", payload["company_id"])
                self.by_key[key] = stored
                self.by_id[stored.ref.id] = stored
                result = stored.ref
        self._maybe_lose("inventory_entry")
        return result

    def reverse_entry(self, operation_id: UUID, payload: dict[str, Any]) -> InventoryOperationRef:
        self.availability.hit("reversal", (operation_id, payload))
        with self.lock:
            key = payload["operation_key"]
            existing = self.by_key.get(key)
            if existing is not None:
                if _canonical(existing.payload) != _canonical({**payload, "target": str(operation_id)}):
                    raise InventoryRejection(409, "OPERATION_KEY_CONFLICT")
                result = existing.ref
            else:
                entry = self.by_id.get(operation_id)
                if entry is None or entry.kind != "ENTRY" or entry.company_id != payload["company_id"]:
                    raise InventoryRejection(404, "NOT_FOUND")
                if entry.reversed_by is not None:
                    raise InventoryRejection(409, "ALREADY_REVERSED")
                if operation_id in self.consumed:
                    raise InventoryRejection(409, "ENTRY_LAYER_CONSUMED")
                for line in entry.payload["lines"]:
                    slot = (entry.payload["branch_id"], line["company_product_id"])
                    self.balances[slot] -= Decimal(line["quantity"])
                stored = StoredOperation(
                    InventoryOperationRef(uuid4(), "ENTRY_REVERSAL", operation_id),
                    key,
                    {**payload, "target": str(operation_id)},
                    "ENTRY_REVERSAL",
                    payload["company_id"],
                )
                entry.reversed_by = stored.ref.id
                self.by_key[key] = stored
                self.by_id[stored.ref.id] = stored
                result = stored.ref
        self._maybe_lose("inventory_entry_reversal")
        return result

    def find_by_key(self, company_id: UUID, operation_key: UUID) -> InventoryOperationRef | None:
        self.availability.hit("by_key", operation_key)
        stored = self.by_key.get(str(operation_key))
        if stored is None or stored.company_id != str(company_id):
            return None
        return stored.ref

    def entries(self) -> list[StoredOperation]:
        return [item for item in self.by_key.values() if item.kind == "ENTRY"]

    def balance(self, branch: UUID, product: UUID) -> Decimal:
        return self.balances.get((str(branch), str(product)), Decimal("0"))


@dataclass
class Fakes:
    world: World
    oc: FakeOperationalContext
    cr: FakeCommercial
    catalog: FakeCatalog
    party: FakeParty
    pr: FakePaymentReference
    inventory: FakeInventory

    def directories(self) -> Directories:
        return Directories(self.oc, self.cr, self.catalog, self.party, self.pr)

    def add_unit_presentations(self, product: UUID, count: int) -> list[UUID]:
        """Registra `count` presentaciones de factor 1 distintas del producto (spec 021: una línea por presentación)."""
        created = []
        for index in range(count):
            company = uuid5(UNIT_NAMESPACE, f"company:{product}:{index}")
            global_ = uuid5(UNIT_NAMESPACE, f"global:{product}:{index}")
            self.cr.presentations[company] = CompanyPresentationInfo(company, self.world.company, product, global_, True, "ACTIVE")
            self.catalog.presentations[global_] = GlobalPresentationInfo(global_, f"U{index:03d}", f"Unidad {index}", Decimal("1"))
            created.append(company)
        return created

    def all_availability(self) -> list[Unavailable]:
        return [
            self.oc.availability,
            self.cr.availability,
            self.catalog.availability,
            self.party.availability,
            self.pr.availability,
            self.inventory.availability,
        ]


def build_fakes(world: World | None = None) -> Fakes:
    world = world or World()
    return Fakes(
        world=world,
        oc=FakeOperationalContext(world),
        cr=FakeCommercial(world),
        catalog=FakeCatalog(world),
        party=FakeParty(world),
        pr=FakePaymentReference(world),
        inventory=FakeInventory(),
    )


def today() -> date:
    return date.today()
