"""Consulta de eventos por alcance (FR-030 a FR-037; RC-07, RC-10).

- **Empresa**: exige membresía `ACTIVE` del usuario, evaluada en cada solicitud
  contra Operational Context y sin caché; fuera del alcance → `404`.
- **Plataforma**: solo eventos con `company_id` nulo; no consulta Operational
  Context.

El alcance siempre viaja al repositorio como condición SQL; los filtros nunca lo
modifican.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any
from uuid import UUID

from audit_service.application.exceptions import NotFoundError
from audit_service.application.ports import (
    AuditEventFilters,
    AuditEventRepository,
    CompanyAccessDirectory,
    Page,
)

NOT_FOUND_MESSAGE = "El recurso solicitado no existe o no está disponible para su usuario."


@dataclass(frozen=True, slots=True)
class PageRequest:
    page: int
    page_size: int


class QueryService:
    """Caso de uso de consulta de eventos."""

    def __init__(
        self,
        repository: AuditEventRepository,
        *,
        access_directory: Callable[[], CompanyAccessDirectory],
    ) -> None:
        self._repository = repository
        self._access_directory = access_directory

    def _check_company(self, company_id: UUID) -> None:
        access = self._access_directory().check_company_access(company_id)

        if not access.member_active:
            raise NotFoundError(NOT_FOUND_MESSAGE)

    # Empresa ---------------------------------------------------------------

    def list_company(self, company_id: UUID, filters: AuditEventFilters, page: PageRequest) -> Page:
        self._check_company(company_id)
        return self._repository.list(
            company_id=company_id, filters=filters, page=page.page, page_size=page.page_size
        )

    def get_company(self, company_id: UUID, audit_id: UUID) -> Any:
        self._check_company(company_id)
        row = self._repository.get(audit_id, company_id=company_id)

        if row is None:
            raise NotFoundError(NOT_FOUND_MESSAGE)

        return row

    def company_entity_history(
        self,
        company_id: UUID,
        entity_type: str,
        entity_id: UUID,
        filters: AuditEventFilters,
        page: PageRequest,
    ) -> Page:
        self._check_company(company_id)
        return self._repository.list(
            company_id=company_id,
            filters=_with_entity(filters, entity_type, entity_id),
            page=page.page,
            page_size=page.page_size,
            ascending=True,
        )

    # Plataforma ------------------------------------------------------------

    def list_platform(self, filters: AuditEventFilters, page: PageRequest) -> Page:
        return self._repository.list(
            company_id=None, filters=filters, page=page.page, page_size=page.page_size
        )

    def get_platform(self, audit_id: UUID) -> Any:
        row = self._repository.get(audit_id, company_id=None)

        if row is None:
            raise NotFoundError(NOT_FOUND_MESSAGE)

        return row

    def platform_entity_history(
        self,
        entity_type: str,
        entity_id: UUID,
        filters: AuditEventFilters,
        page: PageRequest,
    ) -> Page:
        return self._repository.list(
            company_id=None,
            filters=_with_entity(filters, entity_type, entity_id),
            page=page.page,
            page_size=page.page_size,
            ascending=True,
        )


def _with_entity(filters: AuditEventFilters, entity_type: str, entity_id: UUID) -> AuditEventFilters:
    return replace(filters, entity_type=entity_type, entity_id=entity_id)
