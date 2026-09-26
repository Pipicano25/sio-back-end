"""Adaptador HTTP de países, divisiones y ciudades contra Geography Service.

Única implementación productiva del puerto `GeographyDirectory` (R-12). Solo
lee `id`, `status`, `country_id` y `administrative_division_id`; los valores se
usan en memoria y no se persisten (Principio III).
Contrato: `contracts/geography-dependency.md`.
"""

from typing import Any
from uuid import UUID

import httpx

from operational_context_service.application.exceptions import (
    GEOGRAPHY_UNAVAILABLE,
    GEOGRAPHY_VALIDATION_DENIED,
)
from operational_context_service.application.ports import CityRef, DivisionRef, ExternalRef
from operational_context_service.infrastructure.http_lookup import HTTPLookupClient

PROVIDER = "geography"
VALID_STATUSES = {"ACTIVE", "INACTIVE"}


class HTTPGeographyDirectory:
    """Consulta Geography por UUID propagando el token del usuario."""

    def __init__(
        self,
        *,
        base_url: str,
        authorization: str | None,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = HTTPLookupClient(
            provider=PROVIDER,
            base_url=base_url,
            authorization=authorization,
            timeout_seconds=timeout_seconds,
            denied_cause=GEOGRAPHY_VALIDATION_DENIED,
            unavailable_cause=GEOGRAPHY_UNAVAILABLE,
            transport=transport,
        )

    def get_country(self, country_id: UUID) -> ExternalRef | None:
        operation = "get_country"
        body = self._client.get_json(operation, f"/global-countries/{country_id}")

        if body is None:
            return None

        return ExternalRef(id=country_id, status=self._status(body, operation))

    def get_administrative_division(self, division_id: UUID) -> DivisionRef | None:
        operation = "get_administrative_division"
        body = self._client.get_json(
            operation,
            f"/global-administrative-divisions/{division_id}",
        )

        if body is None:
            return None

        return DivisionRef(
            id=division_id,
            status=self._status(body, operation),
            country_id=self._uuid(body, "country_id", operation),
        )

    def get_city(self, city_id: UUID) -> CityRef | None:
        operation = "get_city"
        body = self._client.get_json(operation, f"/global-cities/{city_id}")

        if body is None:
            return None

        if "administrative_division_id" not in body:
            raise self._client.unexpected_body(operation)

        division = body["administrative_division_id"]

        return CityRef(
            id=city_id,
            status=self._status(body, operation),
            country_id=self._uuid(body, "country_id", operation),
            administrative_division_id=(
                None if division is None else self._uuid(body, "administrative_division_id", operation)
            ),
        )

    def _status(self, body: dict[str, Any], operation: str) -> str:
        status = body.get("status")

        if status not in VALID_STATUSES:
            raise self._client.unexpected_body(operation)

        return status

    def _uuid(self, body: dict[str, Any], key: str, operation: str) -> UUID:
        try:
            return UUID(str(body[key]))
        except (KeyError, ValueError, TypeError):
            raise self._client.unexpected_body(operation) from None
