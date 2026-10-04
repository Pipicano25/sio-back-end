"""Filtros del listado de proveedores (FR-035)."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import Query

from commercial_relationship_service.api.filters.common import normalize_search


class CompanySupplierFilters:
    """`search` (código interno, nombre), `status` (incluido `BLOCKED`) y organización."""

    def __init__(
        self,
        search: str | None = Query(default=None, max_length=100),
        status: Literal["ACTIVE", "INACTIVE", "BLOCKED", "ALL"] | None = Query(default=None),
        organization_identity_id: UUID | None = Query(default=None),
    ) -> None:
        self.search = normalize_search(search)
        self.status = status
        self.columns: dict[str, Any] = {"organization_identity_id": organization_identity_id}
