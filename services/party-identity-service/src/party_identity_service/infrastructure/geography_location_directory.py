"""Adaptador HTTP de país, división y ciudad contra Geography Service (R-07).

Única implementación productiva del puerto `LocationDirectory`, usada en todos
los entornos (FR-038). Propaga el token del usuario y `traceparent`; solo lee
`id`, `status`, `country_id` y `administrative_division_id`, que se usan en
memoria y no se persisten (Principio III).
Contrato: `specs/006-party-identity-complementary/contracts/geography-dependency.md`.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import httpx

from party_identity_service.application.exceptions import (
    COUNTRY_VALIDATION_DENIED,
    GEOGRAPHY_UNAVAILABLE,
    DependencyUnavailableError,
)
from party_identity_service.application.ports import LocationRecord
from party_identity_service.observability import (
    SERVICE_LOGGER,
    build_traceparent,
    current_trace_id,
)

logger = logging.getLogger(SERVICE_LOGGER)

VALID_STATUSES = {"ACTIVE", "INACTIVE"}


class HTTPGeographyLocationDirectory:
    """Consulta niveles geográficos por UUID."""

    def __init__(
        self,
        *,
        base_url: str,
        authorization: str | None,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.authorization = authorization
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    def get_country(self, country_id: UUID) -> LocationRecord | None:
        body = self._get_json("get_country", f"/global-countries/{country_id}")
        if body is None:
            return None
        return LocationRecord(id=country_id, status=self._status(body, "get_country"))

    def get_administrative_division(self, division_id: UUID) -> LocationRecord | None:
        operation = "get_administrative_division"
        body = self._get_json(operation, f"/global-administrative-divisions/{division_id}")
        if body is None:
            return None
        return LocationRecord(
            id=division_id,
            status=self._status(body, operation),
            country_id=self._uuid(body, "country_id", operation),
        )

    def get_city(self, city_id: UUID) -> LocationRecord | None:
        operation = "get_city"
        body = self._get_json(operation, f"/global-cities/{city_id}")
        if body is None:
            return None
        if "administrative_division_id" not in body:
            raise self._unavailable(operation, "cuerpo sin administrative_division_id")
        division = body["administrative_division_id"]
        return LocationRecord(
            id=city_id,
            status=self._status(body, operation),
            country_id=self._uuid(body, "country_id", operation),
            administrative_division_id=(
                None if division is None else self._uuid(body, "administrative_division_id", operation)
            ),
        )

    # -- interno --------------------------------------------------------------

    def _get_json(self, operation: str, path: str) -> dict[str, Any] | None:
        headers: dict[str, str] = {}
        if self.authorization:
            headers["Authorization"] = self.authorization
        trace_id = current_trace_id()
        if trace_id:
            headers["traceparent"] = build_traceparent(trace_id)

        try:
            with httpx.Client(timeout=self.timeout_seconds, transport=self.transport) as client:
                response = client.get(f"{self.base_url}{path}", headers=headers)
        except httpx.HTTPError as exc:
            raise self._unavailable(operation, type(exc).__name__) from None

        if response.status_code == 404:
            return None
        if response.status_code in {401, 403}:
            logger.warning(
                "Geography rechazó la consulta causa=%s operacion=%s estado=%s",
                COUNTRY_VALIDATION_DENIED,
                operation,
                response.status_code,
            )
            return self._raise_denied()
        if response.status_code != 200:
            raise self._unavailable(operation, f"estado {response.status_code}")

        try:
            body = response.json()
        except ValueError:
            raise self._unavailable(operation, "cuerpo no JSON") from None
        if not isinstance(body, dict):
            raise self._unavailable(operation, "cuerpo inesperado")
        return body

    @staticmethod
    def _raise_denied() -> None:
        raise DependencyUnavailableError(dependency="geography", cause=COUNTRY_VALIDATION_DENIED)

    @staticmethod
    def _unavailable(operation: str, outcome: str) -> DependencyUnavailableError:
        logger.error(
            "Geography no disponible causa=%s operacion=%s resultado=%s",
            GEOGRAPHY_UNAVAILABLE,
            operation,
            outcome,
        )
        return DependencyUnavailableError(dependency="geography", cause=GEOGRAPHY_UNAVAILABLE)

    def _status(self, body: dict[str, Any], operation: str) -> str:
        status = body.get("status")
        if status not in VALID_STATUSES:
            raise self._unavailable(operation, "status ausente o inválido")
        return status

    def _uuid(self, body: dict[str, Any], key: str, operation: str) -> UUID:
        try:
            return UUID(str(body[key]))
        except (KeyError, ValueError, TypeError):
            raise self._unavailable(operation, f"campo {key} ausente o inválido") from None
