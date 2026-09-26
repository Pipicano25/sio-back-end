"""Obtención de un token técnico `client_credentials` (D5, FR-018).

Solo lo usa el `seed` en modo Geography. No valida tokens (eso sigue en
`sio-auth`, Principio V) y nunca registra ni expone el secreto (Principio IX).
"""

import httpx


class TokenRequestError(RuntimeError):
    """No fue posible obtener el token técnico."""


def fetch_client_credentials_token(
    token_url: str,
    client_id: str,
    client_secret: str,
    *,
    timeout: float,
    transport: httpx.BaseTransport | None = None,
) -> str:
    """Pide un `access_token` con el flujo OAuth 2.0 `client_credentials`.

    Args:
        token_url: Endpoint de tokens del realm.
        client_id: Cliente técnico del servicio.
        client_secret: Secreto del cliente (leído del entorno).
        timeout: Tiempo de espera propio de Keycloak
            (`KEYCLOAK_TIMEOUT_SECONDS`).
        transport: Transporte `httpx` opcional para pruebas.

    Returns:
        El `access_token`.

    Raises:
        TokenRequestError: Ante error de red, tiempo agotado o respuesta
            distinta de `200` con token.
    """
    try:
        with httpx.Client(timeout=timeout, transport=transport) as client:
            response = client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )

    except httpx.HTTPError as exc:
        raise TokenRequestError(
            f"No fue posible contactar a Keycloak ({type(exc).__name__})."
        ) from None

    if response.status_code != 200:
        raise TokenRequestError(
            f"Keycloak rechazó la solicitud de token del cliente {client_id} "
            f"(estado {response.status_code})."
        )

    try:
        return response.json()["access_token"]

    except (ValueError, KeyError, TypeError):
        raise TokenRequestError("Keycloak no devolvió un access_token.") from None
