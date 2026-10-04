"""Resumen de las empresas del usuario (Historia 8; FR-046, DS-18).

Las empresas salen de las membresías `ACTIVE` del usuario en Operational Context
(no hay alcance de plataforma, DS-03). Los conteos se calculan solo para las
empresas de la página, con una consulta agrupada por recurso. La razón social es
dato de presentación: se consulta en cada solicitud y nunca se guarda.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from commercial_relationship_service.application.pagination import PageResult
from commercial_relationship_service.application.ports import (
    CompanyAccessDirectory,
    CompanyDirectory,
    PartyDirectory,
)

PRODUCT_STATUSES = ("ACTIVE", "INACTIVE")
CUSTOMER_STATUSES = ("ACTIVE", "INACTIVE")
SUPPLIER_STATUSES = ("ACTIVE", "INACTIVE", "BLOCKED")


class StatusCounter(Protocol):
    def count_by_company_status(self, company_ids: list[UUID]) -> dict[UUID, dict[str, int]]: ...


@dataclass(frozen=True, slots=True)
class CompanySummary:
    company_id: UUID
    company_status: str
    legal_name: str | None
    company_products: dict[str, int]
    company_customers: dict[str, int] | None
    company_suppliers: dict[str, int] | None


def _counts(by_status: dict[str, int], statuses: tuple[str, ...]) -> dict[str, int]:
    values = {status: by_status.get(status, 0) for status in statuses}
    return {"total": sum(values.values()), **values}


class CompanySummaryService:
    def __init__(
        self,
        access_directory: CompanyAccessDirectory,
        company_directory: Callable[[], CompanyDirectory],
        party_directory: Callable[[], PartyDirectory],
        *,
        products: StatusCounter,
        customers: StatusCounter | None,
        suppliers: StatusCounter | None,
    ) -> None:
        self._access = access_directory
        self._company_directory = company_directory
        self._party_directory = party_directory
        self._products = products
        self._customers = customers
        self._suppliers = suppliers

    def summarize(self, *, page: int, page_size: int) -> PageResult[CompanySummary]:
        """Página de empresas con membresía `ACTIVE` y sus conteos.

        `customers`/`suppliers` en `None` significan que el usuario no tiene su
        permiso de lectura: su conteo sale `None`.
        """
        companies = self._access.list_member_companies()
        selected = companies[(page - 1) * page_size : page * page_size]
        ids = [company.company_id for company in selected]

        products = self._products.count_by_company_status(ids)
        customers = None if self._customers is None else self._customers.count_by_company_status(ids)
        suppliers = None if self._suppliers is None else self._suppliers.count_by_company_status(ids)

        items = [
            CompanySummary(
                company_id=company.company_id,
                company_status=company.company_status,
                legal_name=self._legal_name(company.company_id),
                company_products=_counts(products.get(company.company_id, {}), PRODUCT_STATUSES),
                company_customers=None
                if customers is None
                else _counts(customers.get(company.company_id, {}), CUSTOMER_STATUSES),
                company_suppliers=None
                if suppliers is None
                else _counts(suppliers.get(company.company_id, {}), SUPPLIER_STATUSES),
            )
            for company in selected
        ]
        return PageResult(items=items, page=page, page_size=page_size, total_records=len(companies))

    def _legal_name(self, company_id: UUID) -> str | None:
        organization_id = self._company_directory().find_company_organization(company_id)
        if organization_id is None:
            return None
        return self._party_directory().find_organization_name(organization_id)
