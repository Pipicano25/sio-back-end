"""Validación de referencias, precio y captura de snapshots (FR-002 a FR-006, FR-009, FR-015; R-06, R-07).

Todo se consulta **fuera de transacción** (sin bloqueos abiertos mientras se espera a la
red), por valores distintos y en paralelo acotado (`SALES_LOOKUP_CONCURRENCY`).

Regla P-03 (uniforme en borrador y confirmación):

- `422 VALIDATION_ERROR`: la referencia enviada no existe, es de otra empresa, no puede
  resolverse o es incoherente con la operación (presentación de otro producto).
- `409 REFERENCES_NOT_ELIGIBLE`: existe, pero su estado o configuración actual impide
  usarla (inactiva, no vendible, sin control de inventario, sin precio, lista no aplicable,
  otra moneda).

Si hay errores de ambas clases se informa primero el `422`.

Precio (R-07): una llamada a `applicable-prices/resolve` con la intención original de cada
línea (lista solo si el vendedor la pidió, P-02). `PRICE_LIST_NOT_APPLICABLE` se
desambigua con la consulta de la lista (P-03): inexistente o de otra empresa → `422`;
existente no aplicable → `409`; no disponible → `503`. El precio con base `BASE_UNIT` en una
línea con presentación se convierte con el factor a 4 decimales (P-04).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, TypeVar
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sales_service.application.exceptions import (
    COMMERCIAL_RELATIONSHIP,
    OPERATIONAL_CONTEXT,
    DependencyUnavailableError,
    NotFoundError,
    ReferencesNotEligibleError,
    ValidationFailedError,
    field_error,
)
from sales_service.application.ports import (
    ORGANIZATION,
    PERSON,
    CompanyInfo,
    CompanyPresentationInfo,
    CompanyProductInfo,
    Directories,
    PriceRequestLine,
    ResolvedPrice,
)
from sales_service.domain.conversion import DEFAULT_FACTOR, PRICE_BASES, base_quantity, sale_unit_price
from sales_service.domain.money import DomainRuleError

ACTIVE = "ACTIVE"
CUSTOMER_IDENTIFICATION_MAX = 100
PRICE_LIST_ITEM = "PRICE_LIST_ITEM"
COMPANY_PRODUCT_SALE_PRICE = "COMPANY_PRODUCT_SALE_PRICE"
NO_PRICE_IN_LIST = "NO_PRICE_IN_LIST"
PRICE_LIST_NOT_APPLICABLE = "PRICE_LIST_NOT_APPLICABLE"
NOT_FOUND = "NOT_FOUND"
T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class HeaderInput:
    branch_id: UUID
    company_customer_id: UUID


@dataclass(frozen=True, slots=True)
class HeaderSnapshot:
    currency_code: str
    customer_name: str
    customer_identification: str
    branch_timezone: str


@dataclass(frozen=True, slots=True)
class LineInput:
    """Línea a validar; `price_list_id` es la lista **pedida** por el vendedor (o `None`)."""

    company_product_id: UUID
    company_product_presentation_id: UUID | None
    price_list_id: UUID | None
    quantity: Decimal
    field_prefix: str = ""
    line_number: int | None = None


@dataclass(frozen=True, slots=True)
class LineSnapshot:
    product_code: str
    product_name: str
    presentation_code: str | None
    presentation_name: str | None
    factor: Decimal
    unit_code: str
    unit_price: Decimal
    price_list_id: UUID | None
    price_list_item_id: UUID | None
    price_list_requested: bool


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


def today_in(timezone: str, now: datetime) -> date:
    """Fecha de negocio: el día actual en la zona horaria de la sucursal (R-12)."""
    try:
        return now.astimezone(ZoneInfo(timezone)).date()
    except (ZoneInfoNotFoundError, ValueError):
        raise DependencyUnavailableError(
            OPERATIONAL_CONTEXT, operation="branch", cause=f"zona_horaria_desconocida={timezone}"
        ) from None


class ReferenceResolver:
    """Consulta los dueños de las referencias y construye los snapshots (DS-02, DS-03, R-07)."""

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
            # Cada hilo con una copia del contexto: conserva el trace_id en logs y `traceparent`.
            futures = [pool.submit(copy_context().run, function, value) for value in distinct]
            return dict(zip(distinct, (future.result() for future in futures), strict=True))

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
        """Sucursal (y su zona horaria), cliente e identificación (FR-002, FR-003, FR-009, C-01)."""
        findings = Findings()
        oc = self._dirs.operational_context
        commercial = self._dirs.commercial

        tasks: dict[str, Callable[[], Any]] = {
            "branch": lambda: oc.get_branch(header.branch_id),
            "customer": lambda: commercial.get_customer(header.company_customer_id),
        }
        results = self._parallel(lambda name: tasks[name](), tasks)

        branch = results["branch"]
        timezone = ""
        if branch is None or branch.company_id != company.id:
            findings.bad("branch_id", "BRANCH_NOT_FOUND", "La sucursal no existe en la empresa.")
        elif branch.status != ACTIVE:
            findings.unfit("branch_id", "BRANCH_INACTIVE", "La sucursal no está activa.")
        else:
            timezone = branch.effective_timezone
            today_in(timezone, self._clock())  # zona horaria desconocida → 503 operational-context

        customer = results["customer"]
        customer_name = customer_identification = ""
        field_name = "company_customer_id"
        if customer is None or customer.company_id != company.id:
            findings.bad(field_name, "CUSTOMER_NOT_FOUND", "El cliente no existe en la empresa.")
            customer = None
        elif customer.status != ACTIVE:
            findings.unfit(field_name, "CUSTOMER_NOT_ELIGIBLE", f"El cliente no está activo ({customer.status}).")

        if customer is not None:
            customer_name = customer.display_name[:200]
            party = self._dirs.party
            if customer.customer_kind == PERSON and customer.person_identity_id is not None:
                identity = party.get_person(customer.person_identity_id)
                missing_code = "PERSON_IDENTITY_NOT_FOUND"
            elif customer.customer_kind == ORGANIZATION and customer.organization_identity_id is not None:
                identity = party.get_organization(customer.organization_identity_id)
                missing_code = "ORGANIZATION_IDENTITY_NOT_FOUND"
            else:
                raise DependencyUnavailableError(
                    COMMERCIAL_RELATIONSHIP, operation="company_customer", cause="cliente_sin_identidad"
                )
            if identity is None:
                findings.bad(field_name, missing_code, "La identidad del cliente no existe en Party Identity.")
            elif not identity.identification_type or not identity.identification_number:
                findings.unfit(
                    field_name,
                    "CUSTOMER_IDENTIFICATION_MISSING",
                    "La identidad del cliente no tiene el tipo y el número de identificación obligatorios.",
                )
            else:
                customer_identification = (
                    f"{identity.identification_type} {identity.identification_number}"
                )[:CUSTOMER_IDENTIFICATION_MAX]

        findings.raise_if_any()
        return HeaderSnapshot(
            currency_code=company.default_currency,
            customer_name=customer_name,
            customer_identification=customer_identification,
            branch_timezone=timezone,
        )

    # ----------------------------------------------------------------- líneas

    def resolve_lines(
        self, company_id: UUID, currency_code: str, lines: Sequence[LineInput]
    ) -> list[LineSnapshot]:
        """Producto, presentación, datos del catálogo global y precio vigente (FR-005, FR-006, DS-03, DS-04)."""
        if not lines:
            return []

        commercial = self._dirs.commercial
        catalog = self._dirs.catalog
        product_ids = [line.company_product_id for line in lines]
        presentation_ids = [line.company_product_presentation_id for line in lines if line.company_product_presentation_id]

        first: dict[str, Callable[[], Any]] = {"products": lambda: commercial.lookup_products(product_ids)}
        if presentation_ids:
            first["presentations"] = lambda: commercial.lookup_presentations(presentation_ids)
        stage_one = self._parallel(lambda name: first[name](), first)
        products: dict[UUID, CompanyProductInfo] = stage_one["products"]
        presentations: dict[UUID, CompanyPresentationInfo] = stage_one.get("presentations", {})

        findings = Findings()
        accepted: list[tuple[LineInput, CompanyProductInfo, CompanyPresentationInfo | None]] = []

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
            elif not product.is_sellable:
                findings.unfit(f"{prefix}company_product_id", "PRODUCT_NOT_SELLABLE", "El producto no es vendible.", number)
                line_ok = False
            elif not product.inventory_control_enabled:
                findings.unfit(
                    f"{prefix}company_product_id",
                    "PRODUCT_NOT_INVENTORY_CONTROLLED",
                    "El producto no tiene control de inventario: la venta confirmada debe generar salida en Inventory.",
                    number,
                )
                line_ok = False

            presentation = None
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
                elif not presentation.is_sellable:
                    findings.unfit(field_name, "PRESENTATION_NOT_SELLABLE", "La presentación no es vendible.", number)
                    line_ok = False

            if line_ok:
                accepted.append((line, product, presentation))

        if findings.invalid or findings.not_eligible:
            findings.raise_if_any()

        global_presentations = self._parallel(
            catalog.get_presentation,
            [presentation.global_product_presentation_id for _, _, presentation in accepted if presentation],
        )
        global_products = self._parallel(catalog.get_product, [product.global_product_id for _, product, _ in accepted])
        unit_ids = [item.base_unit_id for item in global_products.values() if item is not None]
        units = self._parallel(catalog.get_unit, unit_ids)

        prepared: list[tuple[int, LineInput, CompanyProductInfo, Decimal, str | None, str | None, str]] = []
        for index, (line, product, presentation) in enumerate(accepted):
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

            factor = DEFAULT_FACTOR
            presentation_code = presentation_name = None
            if presentation is not None:
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
                base_quantity(line.quantity, factor, field=f"{prefix}quantity")
            except DomainRuleError as error:
                findings.bad(error.field or f"{prefix}quantity", error.code, error.message, number)
                continue
            prepared.append((index, line, product, factor, presentation_code, presentation_name, unit.code[:20]))

        findings.raise_if_any()

        prices = commercial.resolve_prices(
            company_id,
            [
                PriceRequestLine(
                    line_id=str(index),
                    company_product_id=line.company_product_id,
                    company_product_presentation_id=line.company_product_presentation_id,
                    price_list_id=line.price_list_id,
                )
                for index, line, *_ in prepared
            ],
            self._clock(),
        )
        not_applicable = [
            line.price_list_id
            for index, line, *_ in prepared
            if line.price_list_id is not None and _price(prices, index).resolution == PRICE_LIST_NOT_APPLICABLE
        ]
        price_lists = self._parallel(commercial.get_price_list, not_applicable)

        snapshots: list[LineSnapshot] = []
        for index, line, product, factor, presentation_code, presentation_name, unit_code in prepared:
            prefix, number = line.field_prefix, line.line_number
            price = _price(prices, index)
            unit_price = self._interpret_price(
                price, line, factor, currency_code, company_id, price_lists, findings, prefix, number
            )
            if unit_price is None:
                continue
            snapshots.append(
                LineSnapshot(
                    product_code=product.internal_code[:80],
                    product_name=product.display_name[:200],
                    presentation_code=presentation_code,
                    presentation_name=presentation_name,
                    factor=factor,
                    unit_code=unit_code,
                    unit_price=unit_price,
                    price_list_id=price.price_list_id,
                    price_list_item_id=price.price_list_item_id,
                    price_list_requested=line.price_list_id is not None,
                )
            )

        findings.raise_if_any()
        return snapshots

    def _interpret_price(
        self,
        price: ResolvedPrice,
        line: LineInput,
        factor: Decimal,
        currency_code: str,
        company_id: UUID,
        price_lists: dict,
        findings: Findings,
        prefix: str,
        number: int | None,
    ) -> Decimal | None:
        """`resolution` → precio por unidad de venta, o el hallazgo `422`/`409` que corresponde (R-07)."""
        list_field = f"{prefix}price_list_id"
        if not price.found or price.resolution == NOT_FOUND:
            findings.bad(f"{prefix}company_product_id", "COMPANY_PRODUCT_NOT_FOUND", "El producto no existe en la empresa.", number)
            return None
        if price.resolution == NO_PRICE_IN_LIST:
            findings.unfit(list_field, "PRICE_NOT_IN_LIST", "La lista de precios indicada no tiene precio para el producto.", number)
            return None
        if price.resolution == PRICE_LIST_NOT_APPLICABLE:
            price_list = price_lists.get(line.price_list_id)
            if price_list is None or price_list.company_id != company_id:
                findings.bad(list_field, "PRICE_LIST_NOT_FOUND", "La lista de precios no existe en la empresa.", number)
            else:
                findings.unfit(
                    list_field,
                    "PRICE_LIST_NOT_APPLICABLE",
                    "La lista de precios no está activa o no está vigente.",
                    number,
                )
            return None
        if price.resolution not in (PRICE_LIST_ITEM, COMPANY_PRODUCT_SALE_PRICE):
            raise DependencyUnavailableError(
                COMMERCIAL_RELATIONSHIP, operation="applicable_prices", cause=f"resolucion_desconocida={price.resolution}"
            )
        if price.unit_price is None:
            findings.unfit(f"{prefix}company_product_id", "PRICE_NOT_AVAILABLE", "El producto no tiene precio de venta.", number)
            return None
        if price.basis not in PRICE_BASES or not price.currency_code:
            raise DependencyUnavailableError(
                COMMERCIAL_RELATIONSHIP, operation="applicable_prices", cause="precio_sin_base_o_moneda"
            )
        if price.currency_code != currency_code:
            findings.unfit(
                f"{prefix}company_product_id",
                "PRICE_CURRENCY_MISMATCH",
                "El precio está en una moneda distinta de la moneda funcional de la empresa.",
                number,
            )
            return None
        if price.unit_price < 0:
            raise DependencyUnavailableError(
                COMMERCIAL_RELATIONSHIP, operation="applicable_prices", cause="precio_negativo"
            )
        return sale_unit_price(price.unit_price, price.basis, factor)

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


def _price(prices: dict[str, ResolvedPrice], index: int) -> ResolvedPrice:
    price = prices.get(str(index))
    if price is None:
        raise DependencyUnavailableError(
            COMMERCIAL_RELATIONSHIP, operation="applicable_prices", cause="linea_sin_precio_en_respuesta"
        )
    return price


def resolve_together(header_call: Callable[[], T], lines_call: Callable[[], Any]) -> tuple[T, Any]:
    """Resuelve cabecera y líneas en paralelo reuniendo sus hallazgos: primero `422`, luego `409` (P-03)."""

    def run(call: Callable[[], Any]) -> Any:
        try:
            return call()
        except (ValidationFailedError, ReferencesNotEligibleError) as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(copy_context().run, run, call) for call in (header_call, lines_call)]
        outcomes: list[Any] = [future.result() for future in futures]
    errors = [item for item in outcomes if isinstance(item, ValidationFailedError | ReferencesNotEligibleError)]
    invalid = [entry for item in errors if isinstance(item, ValidationFailedError) for entry in item.errors]
    if invalid:
        raise ValidationFailedError(invalid)
    if errors:
        raise ReferencesNotEligibleError([entry for item in errors for entry in item.errors])
    return outcomes[0], outcomes[1]
