"""Validador HTTP de países contra Geography Service."""

from uuid import UUID

import httpx

from party_identity_service.application.exceptions import (
    CountryValidationUnavailableError,
)


class HTTPGeographyCountryValidator:
    """Valida países consultando el microservicio Geography."""

    def __init__(
        self,
        *,
        base_url: str,
        authorization: str | None,
        timeout_seconds: float = 5.0,
    ) -> None:
        """Inicializa el validador.

        Args:
            base_url: URL base de Geography Service.
            authorization: Header Authorization de la solicitud actual.
            timeout_seconds: Timeout HTTP.
        """
        self.base_url = base_url.rstrip("/")
        self.authorization = authorization
        self.timeout_seconds = timeout_seconds

    def exists(
        self,
        country_id: UUID,
    ) -> bool:
        """Indica si el país existe en Geography Service."""
        headers = {}

        if self.authorization:
            headers["Authorization"] = self.authorization

        try:
            response = httpx.get(
                f"{self.base_url}/global-countries/{country_id}",
                headers=headers,
                timeout=self.timeout_seconds,
            )

        except httpx.HTTPError as exc:
            raise CountryValidationUnavailableError(
                "No fue posible validar el país contra Geography Service."
            ) from exc

        if response.status_code == 200:
            return True

        if response.status_code == 404:
            return False

        raise CountryValidationUnavailableError(
            "Geography Service no permitió validar el país indicado."
        )
