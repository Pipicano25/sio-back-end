"""Adaptador HTTP de países contra Geography Service.

Es la única implementación productiva del puerto `CountryDirectory` y se usa
en todos los entornos (FR-044). Solo interpreta el código de estado para
validar existencia; no copia datos del país (Principio III).
"""

import logging
from uuid import UUID

import httpx

from party_identity_service.application.exceptions import (
    COUNTRY_VALIDATION_DENIED,
    GEOGRAPHY_UNAVAILABLE,
    CountryNotFoundError,
    DependencyUnavailableError,
)
from party_identity_service.observability import (
    SERVICE_LOGGER,
    build_traceparent,
    current_trace_id,
)

logger = logging.getLogger(SERVICE_LOGGER)

DEFAULT_TIMEOUT_SECONDS = 5.0


class HTTPGeographyCountryValidator:
    """Consulta países en Geography Service mediante su contrato HTTP."""

    def __init__(
        self,
        *,
        base_url: str,
        authorization: str | None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        """Inicializa el adaptador.

        Args:
            base_url: URL base de Geography Service, con su prefijo de ruta.
            authorization: Cabecera `Authorization` a propagar (token del
                usuario o token técnico del `seed`).
            timeout_seconds: Tiempo de espera de cada llamada.
            transport: Transporte `httpx` opcional (las pruebas usan
                `httpx.MockTransport`).
        """
        self.base_url = base_url.rstrip("/")
        self.authorization = authorization
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    def exists(
        self,
        country_id: UUID,
    ) -> bool:
        """Indica si el país existe en Geography Service.

        Raises:
            DependencyUnavailableError: Si no fue posible validar.
        """
        response = self._get(f"/global-countries/{country_id}")

        if response.status_code == 200:
            return True

        if response.status_code == 404:
            return False

        raise self._unavailable(response.status_code)

    def find_id_by_iso3(
        self,
        iso3_code: str,
    ) -> UUID:
        """Resuelve el UUID de un país por su código ISO alfa-3.

        Raises:
            CountryNotFoundError: Si no hay exactamente un país con ese código.
            DependencyUnavailableError: Si no fue posible consultar.
        """
        response = self._get(
            "/global-countries",
            params={"iso3_code": iso3_code},
        )

        if response.status_code != 200:
            raise self._unavailable(response.status_code)

        try:
            items = response.json()["items"]
            matches = [
                item
                for item in items
                if str(item.get("iso3_code", "")).upper() == iso3_code.upper()
            ]
        except (ValueError, KeyError, TypeError, AttributeError):
            raise self._unavailable(response.status_code) from None

        if len(matches) != 1:
            raise CountryNotFoundError(
                f"Geography Service devolvió {len(matches)} países con el "
                f"código {iso3_code}; se esperaba exactamente uno."
            )

        return UUID(str(matches[0]["id"]))

    def _get(
        self,
        path: str,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        headers: dict[str, str] = {}

        if self.authorization:
            headers["Authorization"] = self.authorization

        trace_id = current_trace_id()

        if trace_id:
            headers["traceparent"] = build_traceparent(trace_id)

        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                return client.get(
                    f"{self.base_url}{path}",
                    params=params,
                    headers=headers,
                )

        except httpx.HTTPError as exc:
            logger.warning(
                "Geography no disponible causa=%s error=%s",
                GEOGRAPHY_UNAVAILABLE,
                type(exc).__name__,
            )
            raise DependencyUnavailableError(cause=GEOGRAPHY_UNAVAILABLE) from None

    @staticmethod
    def _unavailable(status_code: int) -> DependencyUnavailableError:
        if status_code in {401, 403}:
            # Se expone como 503 al consumidor; la causa real queda en el log (A1).
            logger.warning(
                "Geography rechazó la validación del país causa=%s estado=%s",
                COUNTRY_VALIDATION_DENIED,
                status_code,
            )
            return DependencyUnavailableError(cause=COUNTRY_VALIDATION_DENIED)

        logger.warning(
            "Geography respondió de forma inesperada causa=%s estado=%s",
            GEOGRAPHY_UNAVAILABLE,
            status_code,
        )
        return DependencyUnavailableError(cause=GEOGRAPHY_UNAVAILABLE)
