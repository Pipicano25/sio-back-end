"""Commercial Relationship leído de sus vistas de contrato (spec 025, T043; D27).

- `ContractCommercialDirectory`: mismo puerto que `HTTPCommercialDirectory`.
  - `get_customer` y `get_price_list` leen `v1_company_customers` y `v1_price_lists` por id (sin fila → `None`).
  - `lookup_products` y `lookup_presentations` leen `v1_company_products` y `v1_company_product_presentations` en
    lotes de 100, como el batch-lookup de hoy (`found=false` → ausente). Igual que el batch-lookup técnico, devuelven
    la fila aunque sea de otra empresa: la aplicación compara `company_id` y responde lo mismo que hoy.
  - `resolve_prices` sigue por HTTP (`applicable-prices/resolve`, FR-031).
- `ContractCustomerRegistry`: el lado de lectura de `HTTPCustomerRegistry.find`. Hoy Commercial Relationship exige
  con el token del vendedor el permiso `company_customers:read` y la membresía `ACTIVE` (que a su vez pide a
  Operational Context con `application_users:read`). Aquí se exigen los mismos dos permisos del token y la membresía
  se lee de `v1_operational_access`; si falta algo, la misma indisponibilidad que hoy produce el `403`/`404`.
  El alta (`create`) sigue por HTTP (FR-032).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sio_auth import SioPermission, TokenClaims
from sio_auth.permissions import has_permission
from sio_contract_read import contract_errors
from sio_contract_read.operational_access import ROUTE_PERMISSION, read_operational_access
from sqlalchemy import Engine

from sales_service.application.exceptions import COMMERCIAL_RELATIONSHIP
from sales_service.application.ports import (
    PERSON,
    CompanyPresentationInfo,
    CompanyProductInfo,
    CustomerInfo,
    PriceListInfo,
    PriceRequestLine,
    ResolvedPrice,
)
from sales_service.infrastructure.commercial_relationship_directory import HTTPCommercialDirectory
from sales_service.infrastructure.contract_support import BATCH_LIMIT, ContractReader, distinct_ids
from sales_service.infrastructure.customer_registry import HTTPCustomerRegistry

_CUSTOMER_COLUMNS = "id, company_id, customer_kind, person_identity_id, organization_identity_id, display_name, status"
_CUSTOMER = f"SELECT {_CUSTOMER_COLUMNS} FROM contract.v1_company_customers WHERE id = :id"
_PRICE_LIST = "SELECT company_id, status FROM contract.v1_price_lists WHERE id = :id"
_PRODUCTS = (
    "SELECT id, company_id, global_product_id, internal_code, display_name, is_sellable, inventory_control_enabled,"
    " status FROM contract.v1_company_products WHERE id = ANY(:ids)"
)
_PRESENTATIONS = (
    "SELECT id, company_id, company_product_id, global_product_presentation_id, is_sellable, status"
    " FROM contract.v1_company_product_presentations WHERE id = ANY(:ids)"
)
_CUSTOMERS_BY_IDENTITY = (
    f"SELECT {_CUSTOMER_COLUMNS} FROM contract.v1_company_customers"
    " WHERE company_id = :company_id AND customer_kind = :kind AND {field} = ANY(:ids)"
)
_CUSTOMERS_READ = SioPermission("commercial-relationship", "company_customers", "read")
_OC_READ = SioPermission(*ROUTE_PERMISSION)
_NOT_MEMBER = frozenset({"USER_NOT_MEMBER", "USER_MEMBERSHIP_INACTIVE"})


def _customer(reader: ContractReader, operation: str, row: dict) -> CustomerInfo:
    required = reader.required
    return CustomerInfo(
        id=required(operation, row, "id"),
        company_id=required(operation, row, "company_id"),
        customer_kind=required(operation, row, "customer_kind"),
        person_identity_id=row.get("person_identity_id"),
        organization_identity_id=row.get("organization_identity_id"),
        display_name=required(operation, row, "display_name"),
        status=required(operation, row, "status"),
    )


class ContractCommercialDirectory:
    def __init__(self, *, engine: Engine, http: HTTPCommercialDirectory) -> None:
        self._reader = ContractReader(engine, COMMERCIAL_RELATIONSHIP)
        self._http = http

    def get_customer(self, customer_id: UUID) -> CustomerInfo | None:
        operation = "company_customer"
        row = self._reader.one(operation, _CUSTOMER, {"id": customer_id})
        return None if row is None else _customer(self._reader, operation, row)

    def _batch(self, operation: str, sql: str, ids: Sequence[UUID]) -> list[dict]:
        found: list[dict] = []
        distinct = distinct_ids(ids)
        for start in range(0, len(distinct), BATCH_LIMIT):
            found.extend(self._reader.rows(operation, sql, {"ids": distinct[start : start + BATCH_LIMIT]}))
        return found

    def lookup_products(self, ids: Sequence[UUID]) -> dict[UUID, CompanyProductInfo]:
        operation = "company_products_batch"
        required = self._reader.required
        return {
            row["id"]: CompanyProductInfo(
                id=row["id"],
                company_id=required(operation, row, "company_id"),
                global_product_id=required(operation, row, "global_product_id"),
                internal_code=required(operation, row, "internal_code"),
                display_name=required(operation, row, "display_name"),
                is_sellable=required(operation, row, "is_sellable"),
                inventory_control_enabled=required(operation, row, "inventory_control_enabled"),
                status=required(operation, row, "status"),
            )
            for row in self._batch(operation, _PRODUCTS, ids)
        }

    def lookup_presentations(self, ids: Sequence[UUID]) -> dict[UUID, CompanyPresentationInfo]:
        operation = "company_product_presentations_batch"
        required = self._reader.required
        return {
            row["id"]: CompanyPresentationInfo(
                id=row["id"],
                company_id=required(operation, row, "company_id"),
                company_product_id=required(operation, row, "company_product_id"),
                global_product_presentation_id=required(operation, row, "global_product_presentation_id"),
                is_sellable=required(operation, row, "is_sellable"),
                status=required(operation, row, "status"),
            )
            for row in self._batch(operation, _PRESENTATIONS, ids)
        }

    def resolve_prices(
        self, company_id: UUID, lines: Sequence[PriceRequestLine], at: datetime
    ) -> dict[str, ResolvedPrice]:
        return self._http.resolve_prices(company_id, lines, at)

    def get_price_list(self, price_list_id: UUID) -> PriceListInfo | None:
        operation = "price_list"
        row = self._reader.one(operation, _PRICE_LIST, {"id": price_list_id})
        if row is None:
            return None
        required = self._reader.required
        return PriceListInfo(
            id=price_list_id, company_id=required(operation, row, "company_id"), status=required(operation, row, "status")
        )


class ContractCustomerRegistry:
    """Búsqueda de clientes por identidad sobre `v1_company_customers`; el alta sigue por HTTP."""

    def __init__(
        self, *, engine: Engine, access_engine: Engine, claims: TokenClaims | None, http: HTTPCustomerRegistry
    ) -> None:
        self._reader = ContractReader(engine, COMMERCIAL_RELATIONSHIP)
        self._access_engine = access_engine
        self._claims = claims
        self._http = http

    def _require_member(self, operation: str, company_id: UUID) -> None:
        claims = self._claims
        if claims is None:
            raise self._reader.unavailable(operation, "estado=401")
        if not has_permission(claims.permissions, _CUSTOMERS_READ) or not has_permission(claims.permissions, _OC_READ):
            raise self._reader.unavailable(operation, "estado=403")
        with contract_errors(lambda cause: self._reader.unavailable(operation, cause), dependency="operational-context"):
            access = read_operational_access(self._access_engine, subject=claims.subject, company_id=company_id)
        if access.reason in _NOT_MEMBER:
            raise self._reader.unavailable(operation, "estado=404")

    def find(self, company_id: UUID, customer_kind: str, identity_ids: Sequence[UUID]) -> dict[UUID, CustomerInfo]:
        operation = "company_customers_by_identity"
        distinct = distinct_ids(identity_ids)
        if not distinct:
            return {}
        self._require_member(operation, company_id)
        field = "person_identity_id" if customer_kind == PERSON else "organization_identity_id"
        rows = self._reader.rows(
            operation,
            _CUSTOMERS_BY_IDENTITY.format(field=field),
            {"company_id": company_id, "kind": customer_kind, "ids": distinct},
        )
        result: dict[UUID, CustomerInfo] = {}
        for row in rows:
            customer = _customer(self._reader, operation, row)
            identity_id = customer.person_identity_id if customer_kind == PERSON else customer.organization_identity_id
            if identity_id is not None:
                result[identity_id] = customer
        return result

    def create(
        self, company_id: UUID, customer_kind: str, identity_id: UUID, internal_code: str, display_name: str
    ) -> CustomerInfo:
        return self._http.create(company_id, customer_kind, identity_id, internal_code, display_name)
