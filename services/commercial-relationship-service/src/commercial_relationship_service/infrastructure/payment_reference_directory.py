"""Adaptador HTTP de Payment Reference (`contracts/payment-reference-dependency.md`, R-08).

Usa la identidad técnica propia (`client_credentials`, DS-02) con el mismo
cliente de token que Product Catalog. Ante `401` renueva el token y repite la
llamada **una** vez; un segundo `401` o un `403` son un error de configuración
del cliente técnico y se exponen como `503`.

El proveedor aún no publica RFC 9457 (GAP-PR-15) ni `/api/v1` (GAP-PR-14): se
interpreta **por código HTTP** y la URL base se configura sin prefijo (C-06).
"""

from __future__ import annotations

from uuid import UUID

import httpx

from commercial_relationship_service.application.exceptions import (
    PAYMENT_REFERENCE,
    PAYMENT_REFERENCE_ACCESS_DENIED,
    PAYMENT_REFERENCE_UNREACHABLE,
    DependencyUnavailableError,
)
from commercial_relationship_service.application.ports import PaymentConditionTypeRef
from commercial_relationship_service.infrastructure.http_lookup import (
    HTTPDependencyClient,
    json_object,
)
from commercial_relationship_service.infrastructure.keycloak_token_client import (
    KeycloakTokenClient,
)


class HTTPPaymentReferenceDirectory:
    """`global-payment-condition-types/{id}` con el token técnico del servicio."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        token_client: KeycloakTokenClient,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = HTTPDependencyClient(
            provider=PAYMENT_REFERENCE,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            unavailable_cause=PAYMENT_REFERENCE_UNREACHABLE,
            transport=transport,
        )
        self._tokens = token_client

    def get_condition_type(self, condition_type_id: UUID) -> PaymentConditionTypeRef | None:
        operation = "global_payment_condition_types_get"
        path = f"/global-payment-condition-types/{condition_type_id}"
        response = self._client.send(operation, "GET", path, authorization=self._bearer())

        if response.status_code == 401:
            # Token caducado o revocado: se renueva y se repite una sola vez.
            self._tokens.invalidate()
            response = self._client.send(operation, "GET", path, authorization=self._bearer())

        if response.status_code in {401, 403}:
            raise self._client.unavailable(
                operation,
                cause=PAYMENT_REFERENCE_ACCESS_DENIED,
                outcome=f"estado={response.status_code}",
            )

        if response.status_code == 404:
            return None

        if response.status_code != 200:
            raise self._client.unavailable(operation, outcome=f"estado={response.status_code}")

        body = json_object(response) or {}
        code = body.get("code")
        status = body.get("status")

        if not isinstance(code, str) or not code or status not in {"ACTIVE", "INACTIVE"}:
            raise self._client.unavailable(operation, outcome="cuerpo_inesperado")

        return PaymentConditionTypeRef(id=condition_type_id, code=code, status=status)

    def _bearer(self) -> str:
        try:
            return f"Bearer {self._tokens.get_token()}"
        except DependencyUnavailableError as exc:
            # El cliente de token es compartido con Product Catalog; aquí la
            # dependencia que no se pudo usar es Payment Reference (errors.md).
            raise DependencyUnavailableError(
                provider=PAYMENT_REFERENCE, cause=exc.cause, operation=exc.operation
            ) from None
