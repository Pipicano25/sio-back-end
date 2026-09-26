"""Adaptador HTTP de fabricantes contra Party Identity Service (R-16).

Contrato: `specs/002-product-catalog-service/contracts/party-identity-dependency.md`.
"""

from __future__ import annotations

from uuid import UUID

import httpx
from fastapi import Request

from product_catalog_service.api.tracing import build_traceparent
from product_catalog_service.application.exceptions import (
    ManufacturerDirectoryAccessDeniedError,
    ManufacturerDirectoryUnavailableError,
)
from product_catalog_service.config import Settings


class HTTPPartyIdentityManufacturerDirectory:
    """Consulta `GET {base}/organization-identities/{id}` propagando el token del usuario."""

    def __init__(
        self,
        *,
        base_url: str,
        authorization: str | None,
        trace_id: str | None,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._authorization = authorization
        self._trace_id = trace_id
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def exists(self, organization_id: UUID) -> bool:
        headers: dict[str, str] = {}

        if self._authorization:
            headers["Authorization"] = self._authorization

        if self._trace_id:
            headers["traceparent"] = build_traceparent(self._trace_id)

        try:
            with httpx.Client(
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = client.get(
                    f"{self._base_url}/organization-identities/{organization_id}",
                    headers=headers,
                )
        except httpx.HTTPError as exc:
            raise ManufacturerDirectoryUnavailableError(
                "No fue posible consultar Party Identity Service."
            ) from exc

        if response.status_code == 200:
            return True

        if response.status_code == 404:
            return False

        if response.status_code in {401, 403}:
            raise ManufacturerDirectoryAccessDeniedError(
                "Party Identity Service rechazó la consulta de la organización."
            )

        raise ManufacturerDirectoryUnavailableError(
            f"Party Identity Service respondió {response.status_code}."
        )


def build_manufacturer_directory(
    request: Request,
    settings: Settings,
) -> HTTPPartyIdentityManufacturerDirectory:
    """Construye el adaptador para la solicitud actual."""
    return HTTPPartyIdentityManufacturerDirectory(
        base_url=settings.party_identity_service_base_url,
        authorization=request.headers.get("authorization"),
        trace_id=getattr(request.state, "trace_id", None),
        timeout_seconds=settings.party_identity_timeout_seconds,
    )
