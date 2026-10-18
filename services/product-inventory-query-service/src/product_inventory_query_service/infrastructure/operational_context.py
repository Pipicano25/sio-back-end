"""Adaptador de Operational Context, **siempre con el token del usuario** (D5, research R-02; FR-022-11).

- `operational-access?company_id=`: membresía `ACTIVE`. `allowed = false`, `403` o `404` → sin acceso.
- `companies/{c}/branches?status=`: sucursales, siguiendo las páginas. Un `403` o `404` (usuario sin
  membresía) devuelve una lista vacía: la decisión la toma la verificación de acceso.

Cualquier otro estado, un cuerpo inesperado, la red o el tiempo agotado → `503`.
"""

from __future__ import annotations

import logging
from uuid import UUID

from product_inventory_query_service.application.ports import BranchInfo
from product_inventory_query_service.infrastructure.http_client import AsyncDependencyClient
from product_inventory_query_service.infrastructure.parsing import UnexpectedBody, bool_of, int_of, items, obj, text_of, uuid_of
from product_inventory_query_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)
PAGE_SIZE = 100
MAX_PAGES = 50


class HTTPOperationalContext:
    def __init__(self, client: AsyncDependencyClient, authorization: str | None) -> None:
        self._client = client
        self._authorization = authorization

    async def has_company_access(self, company_id: UUID) -> bool:
        operation = "operational_access"
        response = await self._client.send(
            operation, "GET", "/operational-access", authorization=self._authorization,
            params={"company_id": str(company_id)},
        )
        if response.status_code in (403, 404):
            logger.info("Operational Context negó el acceso a la empresa estado=%s", response.status_code)
            return False
        if response.status_code != 200:
            raise self._client.unavailable(operation, f"estado={response.status_code}")
        try:
            body = obj(response.json())
            allowed = bool_of(body, "allowed")
            returned = uuid_of(body, "company_id", optional=True)
        except (ValueError, UnexpectedBody):
            raise self._client.unavailable(operation, "cuerpo_inesperado") from None
        return allowed and (returned is None or returned == company_id)

    async def branches(self, company_id: UUID, *, status: str) -> list[BranchInfo]:
        operation = "branches"
        found: list[BranchInfo] = []
        for page in range(1, MAX_PAGES + 1):
            response = await self._client.send(
                operation, "GET", f"/companies/{company_id}/branches", authorization=self._authorization,
                params={"status": status, "page": page, "page_size": PAGE_SIZE},
            )
            if response.status_code in (403, 404):
                return []
            if response.status_code != 200:
                raise self._client.unavailable(operation, f"estado={response.status_code}")
            try:
                body = response.json()
                for item in items(body):
                    branch = BranchInfo(uuid_of(item, "id"), uuid_of(item, "company_id"), text_of(item, "status"))
                    if branch.company_id != company_id:
                        logger.error("Incidente de integridad: Operational Context devolvió una sucursal de otra empresa")
                        continue
                    found.append(branch)
                total_pages = int_of(obj(body), "total_pages")
            except (ValueError, UnexpectedBody):
                raise self._client.unavailable(operation, "cuerpo_inesperado") from None
            if page >= total_pages:
                return found
        raise self._client.unavailable(operation, "demasiadas_paginas")
