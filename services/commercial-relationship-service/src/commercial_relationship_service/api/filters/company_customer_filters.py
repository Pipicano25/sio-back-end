"""Filtros del listado de clientes (FR-026)."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import Query

from commercial_relationship_service.api.filters.common import normalize_search


class CompanyCustomerFilters:
    """`search` (código interno, nombre), `status`, tipo e identidades."""

    def __init__(
        self,
        search: str | None = Query(default=None, max_length=100),
        status: Literal["ACTIVE", "INACTIVE", "ALL"] | None = Query(default=None),
        customer_kind: Literal["PERSON", "ORGANIZATION"] | None = Query(default=None),
        person_identity_id: UUID | None = Query(default=None),
        organization_identity_id: UUID | None = Query(default=None),
    ) -> None:
        self.search = normalize_search(search)
        self.status = status
        self.columns: dict[str, Any] = {
            "customer_kind": customer_kind,
            "person_identity_id": person_identity_id,
            "organization_identity_id": organization_identity_id,
        }
