"""Validación de referencias y captura de snapshots (FR-002 a FR-005, FR-012 a FR-016, FR-047; R-06).

Todo se consulta **fuera de transacción** (sin bloqueos abiertos mientras se espera a la
red), por valores distintos y en paralelo acotado (`PURCHASE_LOOKUP_CONCURRENCY`).

Regla P-03 (uniforme en borrador y confirmación):

- `422 VALIDATION_ERROR`: la referencia enviada no existe, es de otra empresa, no puede
  resolverse o es incoherente con la operación (de otro proveedor o de otro producto).
- `409 REFERENCES_NOT_ELIGIBLE`: existe, pero su estado o configuración actual impide
  usarla (inactiva, bloqueada, no comprable, sin control de inventario, no vigente, otra
  moneda).

Si hay errores de ambas clases se informa primero el `422`.

Spec 020: solo contado (una condición de pago cuyo tipo no es `CASH` → `409
PAYMENT_CONDITION_NOT_AVAILABLE`); medio de pago declarado y activo de Payment Reference
(`PAYMENT_METHOD_NOT_FOUND` `422` / `PAYMENT_METHOD_INACTIVE` `409`); presentación obligatoria
(`PRESENTATION_REQUIRED`) y costo por unidad base mayor que cero (`BASE_UNIT_COST_NOT_POSITIVE`).

Spec 021 (Historia 8): una presentación aparece a lo sumo en una línea de la compra
(`409 DUPLICATE_PRESENTATION_IN_PURCHASE`, `check_unique_presentations`).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, TypeVar
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from purchase_service.application.exceptions import (
    OPERATIONAL_CONTEXT,
    DependencyUnavailableError,
    DuplicatePresentationInPurchaseError,
    NotFoundError,
    ReferencesNotEligibleError,
    ValidationFailedError,
    field_error,
)
from purchase_service.application.ports import (
    CompanyInfo,
    CompanyPresentationInfo,
    CompanyProductInfo,
    Directories,
    PaymentMethodInfo,
    SupplierProductInfo,
)
from purchase_service.domain.conversion import base_quantity, check_base_unit_cost
from purchase_service.domain.money import DomainRuleError
from purchase_service.domain.status import CASH, PAYMENT_CODES

ACTIVE = "ACTIVE"
SUPPLIER_IDENTIFICATION_MAX = 100
T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class HeaderInput:
    branch_id: UUID
    company_supplier_id: UUID
    operation_date: date
    supplier_payment_condition_id: UUID | None
    payment_method_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class HeaderSnapshot:
    currency_code: str
    supplier_name: str
    supplier_identification: str
    payment_condition_code: str
    payment_terms_days: int
    due_date: date
    payment_method_id: UUID | None = None
    payment_method_code: str | None = None
    payment_method_name: str | None = None


@dataclass(frozen=True, slots=True)
class LineInput:
    """Línea a validar; `field_prefix` ubica el error (`lines[3].` o vacío)."""

    company_product_id: UUID
    company_product_presentation_id: UUID | None
    supplier_product_id: UUID | None
    quantity: Decimal
    field_prefix: str = ""
    line_number: int | None = None
    net_cost: Decimal | None = None
    """`subtotal − descuento` de la línea: con él se comprueba el costo por unidad base (spec 020)."""


@dataclass(frozen=True, slots=True)
class LineSnapshot:
    product_code: str
    product_name: str
    presentation_code: str | None
    presentation_name: str | None
    factor: Decimal
    unit_code: str
    lead_time_hours: Decimal | None
    purchase_tax_percentage: Decimal | None = None
    """Spec 021: tasa predeterminada del producto en Commercial Relationship (`None` = sin configurar)."""


@dataclass
class Findings:
    invalid: list[dict[str, Any]] = field(default_factory=list)
    not_eligible: list[dict[str, Any]] = field(default_factory=list)

    def bad(self, field_name: str, code: str, message: str, line_number: int | None = None) -> None:
        self.invalid.append(field_error(field_name, code, message, line_number=line_number))

    def unfit(self, field_name: str, code: str, message: str, line_number: int | None = None) -> None:
        self.not_eligible.append(field_error(field_name, code, message, line_number=line_number))

    def raise_if_any(self) -> None:
        if self.invalid:
            raise ValidationFailedError(self.invalid)
        if self.not_eligible:
            raise ReferencesNotEligibleError(self.not_eligible)


DUPLICATE_PRESENTATION = "DUPLICATE_PRESENTATION_IN_PURCHASE"


def check_unique_presentations(lines: Iterable[tuple[str, int | None, UUID | None]]) -> None:
    """`(campo, número de línea, presentación)` de todas las líneas que quedarían en la compra.

    Se informa cada línea que repite una presentación ya usada en una línea anterior (Historia 8, CP-29).
    """
    seen: dict[UUID, int | None] = {}
    errors = []
    for field_name, line_number, presentation_id in lines:
        if presentation_id is None:
            continue  # la presentación obligatoria la valida `resolve_lines` (Spec 020)
        if presentation_id in seen:
            first = seen[presentation_id]
            where = f"la línea {first}" if first is not None else "otra línea"
            errors.append(field_error(
                field_name, DUPLICATE_PRESENTATION, f"La presentación ya está en {where} de la compra.",
                line_number=line_number,
            ) | {"company_product_presentation_id": str(presentation_id)})
        else:
            seen[presentation_id] = line_number
    if errors:
        raise DuplicatePresentationInPurchaseError(errors)


def today_in(timezone: str, now: datetime) -> date:
    try:
        return now.astimezone(ZoneInfo(timezone)).date()
    except (ZoneInfoNotFoundError, ValueError):
        raise DependencyUnavailableError(
            OPERATIONAL_CONTEXT, operation="branch", cause=f"zona_horaria_desconocida={timezone}"
        ) from None


class ReferenceResolver:
    """Consulta los dueños de las referencias y construye los snapshots (DS-02, DS-03)."""

    def __init__(self, directories: Directories, *, concurrency: int, clock: Callable[[], datetime]) -> None:
        self._dirs = directories
        self._concurrency = max(1, concurrency)
        self._clock = clock

    # ------------------------------------------------------------------ util

    def _parallel(self, function: Callable[[Any], T], values: Iterable[Any]) -> dict[Any, T]:
        distinct = list(dict.fromkeys(values))
        if not distinct:
            return {}
        if len(distinct) == 1 or self._concurrency == 1:
            return {value: function(value) for value in distinct}
        with ThreadPoolExecutor(max_workers=min(self._concurrency, len(distinct))) as pool:
            return dict(zip(distinct, pool.map(function, distinct), strict=True))

    # --------------------------------------------------------------- empresa

    def company(self, company_id: UUID) -> CompanyInfo:
        """Empresa de la ruta (ya autorizada por membresía): inexistente → `404`; inactiva → `409`."""
        company = self._dirs.operational_context.get_company(company_id)
        if company is None:
            raise NotFoundError()
        if company.status != ACTIVE:
            raise ReferencesNotEligibleError(
                [field_error("company_id", "COMPANY_INACTIVE", "La empresa no está activa.")]
            )
        return company

    # --------------------------------------------------------------- cabecera

    def resolve_header(self, company: CompanyInfo, header: HeaderInput) -> HeaderSnapshot:
        """Sucursal, proveedor e identificación, condición de pago y fecha (FR-002, FR-003, FR-012–FR-014)."""
        findings = Findings()
        oc = self._dirs.operational_context
        commercial = self._dirs.commercial

        tasks: dict[str, Callable[[], Any]] = {
            "branch": lambda: oc.get_branch(header.branch_id),
            "supplier": lambda: commercial.get_supplier(header.company_supplier_id),
        }
        if header.supplier_payment_condition_id is not None:
            condition_id = header.supplier_payment_condition_id
            tasks["condition"] = lambda: commercial.get_payment_condition(condition_id)
        if header.payment_method_id is not None:
            method_id = header.payment_method_id
            tasks["method"] = lambda: self._dirs.payment_reference.get_payment_method(method_id)
        results = self._parallel(lambda name: tasks[name](), tasks)

        branch = results["branch"]
        if branch is None or branch.company_id != company.id:
            findings.bad("branch_id", "BRANCH_NOT_FOUND", "La sucursal no existe en la empresa.")
        elif branch.status != ACTIVE:
            findings.unfit("branch_id", "BRANCH_INACTIVE", "La sucursal no está activa.")
        elif header.operation_date > today_in(branch.effective_timezone, self._clock()):
            findings.bad("operation_date", "OPERATION_DATE_IN_FUTURE", "La fecha de la compra no puede ser futura.")

        supplier = results["supplier"]
        supplier_name = supplier_identification = ""
        if supplier is None or supplier.company_id != company.id:
            findings.bad("company_supplier_id", "SUPPLIER_NOT_FOUND", "El proveedor no existe en la empresa.")
            supplier = None
        elif supplier.status != ACTIVE:
            findings.unfit(
                "company_supplier_id", "SUPPLIER_NOT_ELIGIBLE", f"El proveedor no está activo ({supplier.status})."
            )

        payment_code, terms_days = CASH, 0
        condition = results.get("condition")
        condition_type = None
        if header.supplier_payment_condition_id is not None:
            field_name = "supplier_payment_condition_id"
            if condition is None or condition.company_id != company.id:
                findings.bad(field_name, "PAYMENT_CONDITION_NOT_FOUND", "La condición de pago no existe en la empresa.")
                condition = None
            elif supplier is not None and condition.company_supplier_id != supplier.id:
                findings.bad(
                    field_name,
                    "PAYMENT_CONDITION_OF_OTHER_SUPPLIER",
                    "La condición de pago pertenece a otro proveedor.",
                )
                condition = None
            elif condition.status != ACTIVE:
                findings.unfit(field_name, "PAYMENT_CONDITION_INACTIVE", "La condición de pago no está activa.")
            elif (condition.valid_from and header.operation_date < condition.valid_from) or (
                condition.valid_to and header.operation_date > condition.valid_to
            ):
                findings.unfit(
                    field_name,
                    "PAYMENT_CONDITION_NOT_VALID_ON_DATE",
                    "La condición de pago no está vigente en la fecha de la compra.",
                )
            elif condition.currency_code != company.default_currency:
                findings.unfit(
                    field_name,
                    "PAYMENT_CONDITION_CURRENCY_MISMATCH",
                    "La condición de pago está en una moneda distinta de la moneda funcional de la empresa.",
                )

        organization = None
        follow_up: dict[str, Callable[[], Any]] = {}
        if supplier is not None:
            organization_id = supplier.organization_identity_id
            follow_up["organization"] = lambda: self._dirs.party.get_organization(organization_id)
        if condition is not None:
            type_id = condition.payment_condition_type_id
            follow_up["type"] = lambda: self._dirs.payment_reference.get_condition_type(type_id)
        if follow_up:
            second = self._parallel(lambda name: follow_up[name](), follow_up)
            organization = second.get("organization")
            condition_type = second.get("type")

        if supplier is not None:
            supplier_name = supplier.display_name[:200]
            if organization is None:
                findings.bad(
                    "company_supplier_id",
                    "ORGANIZATION_IDENTITY_NOT_FOUND",
                    "La identidad de organización del proveedor no existe en Party Identity.",
                )
            elif not organization.identification_type or not organization.identification_number:
                findings.unfit(
                    "company_supplier_id",
                    "ORGANIZATION_IDENTIFICATION_MISSING",
                    "La organización del proveedor no tiene la identificación obligatoria para la compra.",
                )
            else:
                supplier_identification = (
                    f"{organization.identification_type} {organization.identification_number}"
                )[:SUPPLIER_IDENTIFICATION_MAX]

        if condition is not None:
            if condition_type is None:
                findings.bad(
                    "supplier_payment_condition_id",
                    "PAYMENT_CONDITION_TYPE_NOT_FOUND",
                    "El tipo de la condición de pago no existe en Payment Reference.",
                )
            elif condition_type.status != ACTIVE or condition_type.code not in PAYMENT_CODES:
                findings.unfit(
                    "supplier_payment_condition_id",
                    "PAYMENT_CONDITION_TYPE_INACTIVE",
                    "El tipo de la condición de pago no está activo o no es CASH, CREDIT ni FINANCING.",
                )
            elif condition_type.code != CASH:
                # Spec 020 (FR-020-08, RC-MVP-3): solo contado durante el MVP.
                findings.unfit(
                    "supplier_payment_condition_id",
                    "PAYMENT_CONDITION_NOT_AVAILABLE",
                    f"Las compras con condición {condition_type.code} no están disponibles en el MVP: "
                    "solo se admiten compras de contado (CASH).",
                )

        method = self._payment_method(header.payment_method_id, results.get("method"), findings)

        findings.raise_if_any()
        due_date = header.operation_date + timedelta(days=terms_days)
        return HeaderSnapshot(
            currency_code=company.default_currency,
            supplier_name=supplier_name,
            supplier_identification=supplier_identification,
            payment_condition_code=payment_code,
            payment_terms_days=terms_days,
            payment_method_id=header.payment_method_id,
            payment_method_code=method.code if method else None,
            payment_method_name=method.name if method else None,
            due_date=due_date,
        )

    # ----------------------------------------------------------------- líneas

    def _payment_method(
        self, method_id: UUID | None, method: PaymentMethodInfo | None, findings: Findings
    ) -> PaymentMethodInfo | None:
        """Medio de pago declarado (spec 020, FR-020-09): uno solo, existente y `ACTIVE`."""
        field_name = "payment_method_id"
        if method_id is None:
            findings.bad(field_name, "PAYMENT_METHOD_REQUIRED", "La compra debe indicar un medio de pago.")
            return None
        if method is None:
            findings.bad(field_name, "PAYMENT_METHOD_NOT_FOUND", "El medio de pago no existe en Payment Reference.")
            return None
        if method.status != ACTIVE:
            findings.unfit(field_name, "PAYMENT_METHOD_INACTIVE", f"El medio de pago {method.code} no está activo.")
            return None
        return method

    def resolve_lines(
        self, company_id: UUID, supplier_id: UUID, lines: Sequence[LineInput]
    ) -> list[LineSnapshot]:
        """Producto, presentación, producto de proveedor y datos del catálogo global (FR-005, DS-03)."""
        if not lines:
            return []

        commercial = self._dirs.commercial
        catalog = self._dirs.catalog
        product_ids = [line.company_product_id for line in lines]
        presentation_ids = [line.company_product_presentation_id for line in lines if line.company_product_presentation_id]
        supplier_product_ids = [line.supplier_product_id for line in lines if line.supplier_product_id]

        first: dict[str, Callable[[], Any]] = {"products": lambda: commercial.lookup_products(product_ids)}
        if presentation_ids:
            first["presentations"] = lambda: commercial.lookup_presentations(presentation_ids)
        stage_one = self._parallel(lambda name: first[name](), first)
        supplier_products = self._parallel(commercial.get_supplier_product, supplier_product_ids)
        products: dict[UUID, CompanyProductInfo] = stage_one["products"]
        presentations: dict[UUID, CompanyPresentationInfo] = stage_one.get("presentations", {})

        findings = Findings()
        accepted: list[tuple[LineInput, CompanyProductInfo, CompanyPresentationInfo | None, SupplierProductInfo | None]] = []

        for line in lines:
            prefix, number = line.field_prefix, line.line_number
            product = products.get(line.company_product_id)
            line_ok = True

            if product is None or product.company_id != company_id:
                findings.bad(f"{prefix}company_product_id", "COMPANY_PRODUCT_NOT_FOUND", "El producto no existe en la empresa.", number)
                continue
            if product.status != ACTIVE:
                findings.unfit(f"{prefix}company_product_id", "PRODUCT_INACTIVE", "El producto no está activo.", number)
                line_ok = False
            elif not product.is_purchasable:
                findings.unfit(f"{prefix}company_product_id", "PRODUCT_NOT_PURCHASABLE", "El producto no es comprable.", number)
                line_ok = False
            elif not product.inventory_control_enabled:
                findings.unfit(
                    f"{prefix}company_product_id",
                    "PRODUCT_NOT_INVENTORY_CONTROLLED",
                    "El producto no tiene control de inventario: la compra confirmada debe generar entrada en Inventory.",
                    number,
                )
                line_ok = False

            presentation = None
            if line.company_product_presentation_id is None:
                # Spec 020 (FR-020-11): toda línea indica su presentación (borradores anteriores).
                findings.bad(
                    f"{prefix}company_product_presentation_id",
                    "PRESENTATION_REQUIRED",
                    "Toda línea de compra indica su presentación, también la de factor 1.",
                    number,
                )
                continue
            if line.company_product_presentation_id is not None:
                presentation = presentations.get(line.company_product_presentation_id)
                field_name = f"{prefix}company_product_presentation_id"
                if presentation is None or presentation.company_id != company_id:
                    findings.bad(field_name, "PRESENTATION_NOT_FOUND", "La presentación no existe en la empresa.", number)
                    continue
                if presentation.company_product_id != line.company_product_id:
                    findings.bad(
                        field_name, "PRESENTATION_OF_OTHER_PRODUCT", "La presentación pertenece a otro producto.", number
                    )
                    continue
                if presentation.status != ACTIVE:
                    findings.unfit(field_name, "PRESENTATION_INACTIVE", "La presentación no está activa.", number)
                    line_ok = False
                elif not presentation.is_purchasable:
                    findings.unfit(field_name, "PRESENTATION_NOT_PURCHASABLE", "La presentación no es comprable.", number)
                    line_ok = False

            supplier_product = None
            if line.supplier_product_id is not None:
                supplier_product = supplier_products.get(line.supplier_product_id)
                field_name = f"{prefix}supplier_product_id"
                if supplier_product is None or supplier_product.company_id != company_id:
                    findings.bad(
                        field_name, "SUPPLIER_PRODUCT_NOT_FOUND", "El producto de proveedor no existe en la empresa.", number
                    )
                    continue
                if (
                    supplier_product.company_supplier_id != supplier_id
                    or supplier_product.company_product_id != line.company_product_id
                    or (
                        supplier_product.company_product_presentation_id is not None
                        and supplier_product.company_product_presentation_id != line.company_product_presentation_id
                    )
                ):
                    findings.bad(
                        field_name,
                        "SUPPLIER_PRODUCT_MISMATCH",
                        "El producto de proveedor corresponde a otro proveedor, producto o presentación.",
                        number,
                    )
                    continue
                if supplier_product.status != ACTIVE:
                    findings.unfit(field_name, "SUPPLIER_PRODUCT_INACTIVE", "El producto de proveedor no está activo.", number)
                    line_ok = False

            if line_ok:
                accepted.append((line, product, presentation, supplier_product))

        if findings.invalid or findings.not_eligible:
            findings.raise_if_any()

        # Spec 021 (H-2): una consulta por cada 100 presentaciones globales, no una por presentación.
        global_ids = [presentation.global_product_presentation_id for _, _, presentation, _ in accepted if presentation]
        global_presentations = catalog.lookup_presentations(global_ids) if global_ids else {}
        global_products = self._parallel(catalog.get_product, [product.global_product_id for _, product, _, _ in accepted])
        unit_ids = [item.base_unit_id for item in global_products.values() if item is not None]
        units = self._parallel(catalog.get_unit, unit_ids)

        snapshots: list[LineSnapshot] = []
        for line, product, presentation, supplier_product in accepted:
            prefix, number = line.field_prefix, line.line_number
            global_product = global_products.get(product.global_product_id)
            unit = units.get(global_product.base_unit_id) if global_product else None
            if global_product is None or unit is None:
                findings.bad(
                    f"{prefix}company_product_id",
                    "COMPANY_PRODUCT_NOT_FOUND",
                    "El producto global o su unidad base no existen en Product Catalog.",
                    number,
                )
                continue

            global_presentation = global_presentations.get(presentation.global_product_presentation_id)
            if global_presentation is None or global_presentation.base_quantity <= 0:
                findings.bad(
                    f"{prefix}company_product_presentation_id",
                    "PRESENTATION_NOT_FOUND",
                    "La presentación global no existe en Product Catalog.",
                    number,
                )
                continue
            factor = global_presentation.base_quantity
            presentation_code = global_presentation.code[:80]
            presentation_name = global_presentation.name[:160]

            try:
                base_qty = base_quantity(line.quantity, factor, field=f"{prefix}quantity")
                if line.net_cost is not None:
                    # Spec 020 (FR-020-12, RC-MVP-5): nunca una capa FIFO con costo 0.
                    check_base_unit_cost(line.net_cost, Decimal("0"), base_qty, field=f"{prefix}unit_cost")
            except DomainRuleError as error:
                findings.bad(error.field or f"{prefix}quantity", error.code, error.message, number)
                continue

            snapshots.append(
                LineSnapshot(
                    product_code=product.internal_code[:80],
                    product_name=product.display_name[:200],
                    presentation_code=presentation_code,
                    presentation_name=presentation_name,
                    factor=factor,
                    unit_code=unit.code[:20],
                    lead_time_hours=supplier_product.expected_supplier_lead_time_hours if supplier_product else None,
                    purchase_tax_percentage=product.purchase_tax_percentage,
                )
            )

        findings.raise_if_any()
        return snapshots

    # -------------------------------------------------------- cobertura de políticas (spec 021)

    def uncovered_presentations(self, company_id: UUID, currency_code: str, presentation_ids: Iterable[UUID]) -> frozenset[UUID]:
        """Presentaciones sin política de ganancia aplicable (FR-021-35); un fallo de CR es `503` (nunca se asume)."""
        distinct = list(dict.fromkeys(presentation_ids))
        if not distinct:
            return frozenset()
        covered = self._dirs.commercial.lookup_pricing_coverage(company_id, currency_code, distinct)
        return frozenset(value for value in distinct if not covered.get(value, False))

    # -------------------------------------------------------- usuario operativo

    def check_operator(self, company_id: UUID, application_user_id: UUID) -> None:
        """Usuario operativo que confirma: existe en la empresa y está `ACTIVE`."""
        user = self._dirs.operational_context.get_application_user(application_user_id)
        if user is None or user.company_id != company_id:
            raise DependencyUnavailableError(
                OPERATIONAL_CONTEXT, operation="application_user", cause="usuario_operativo_inconsistente"
            )
        if user.status != ACTIVE:
            raise ReferencesNotEligibleError(
                [field_error("application_user_id", "APPLICATION_USER_INACTIVE", "Su usuario operativo no está activo.")]
            )


def resolve_together(header_call: Callable[[], T], lines_call: Callable[[], Any]) -> tuple[T, Any]:
    """Resuelve cabecera y líneas reuniendo sus hallazgos: primero `422`, luego `409` (P-03)."""
    outcomes: list[Any] = []
    for call in (header_call, lines_call):
        try:
            outcomes.append(call())
        except (ValidationFailedError, ReferencesNotEligibleError) as error:
            outcomes.append(error)
    errors = [item for item in outcomes if isinstance(item, ValidationFailedError | ReferencesNotEligibleError)]
    invalid = [entry for item in errors if isinstance(item, ValidationFailedError) for entry in item.errors]
    if invalid:
        raise ValidationFailedError(invalid)
    if errors:
        raise ReferencesNotEligibleError([entry for item in errors for entry in item.errors])
    return outcomes[0], outcomes[1]
