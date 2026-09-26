"""Comando de carga inicial: `python -m party_identity_service.seed load`.

Modos (FR-017):

- país explícito: `load --country-id <uuid>` o `PARTY_IDENTITY_SEED_COUNTRY_ID`
  (el parámetro prevalece). No consulta Geography ni pide token.
- Geography (por defecto): obtiene un token `client_credentials` del cliente
  `party-identity-service` y resuelve `COL` en Geography Service.
"""

from __future__ import annotations

import argparse
import sys
from uuid import UUID

from dotenv import load_dotenv

from party_identity_service.application.exceptions import PartyIdentityError
from party_identity_service.config import Settings, load_settings
from party_identity_service.infrastructure.database import Database
from party_identity_service.infrastructure.geography_country_validator import (
    HTTPGeographyCountryValidator,
)
from party_identity_service.infrastructure.keycloak_token_client import (
    TokenRequestError,
    fetch_client_credentials_token,
)
from party_identity_service.seed.constants import COUNTRY_ID_VARIABLE
from party_identity_service.seed.loader import load_seed


def _uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' no es un UUID válido.") from None


def build_geography_directory(settings: Settings) -> HTTPGeographyCountryValidator:
    """Adaptador HTTP de Geography autenticado con el token técnico del servicio."""
    missing = [
        name
        for name, value in (
            ("KEYCLOAK_TOKEN_URL", settings.keycloak_token_url),
            ("PARTY_IDENTITY_CLIENT_ID", settings.client_id),
            ("PARTY_IDENTITY_CLIENT_SECRET", settings.client_secret),
        )
        if not value
    ]

    if missing:
        raise TokenRequestError(
            "Faltan variables para el modo Geography: "
            f"{', '.join(missing)}. Use --country-id para el modo independiente."
        )

    token = fetch_client_credentials_token(
        settings.keycloak_token_url,
        settings.client_id,
        settings.client_secret,
        timeout=settings.keycloak_timeout_seconds,
    )

    return HTTPGeographyCountryValidator(
        base_url=settings.geography_service_base_url,
        authorization=f"Bearer {token}",
        timeout_seconds=settings.geography_timeout_seconds,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m party_identity_service.seed",
        description="Carga idempotente de las reglas de identificación iniciales de Colombia.",
    )
    parser.add_argument("command", choices=["load"], help="Operación a ejecutar.")
    parser.add_argument(
        "--country-id",
        type=_uuid,
        default=None,
        help=(
            "UUID de Colombia en el Geography de su entorno (modo independiente, "
            f"sin Geography). También puede indicarse con {COUNTRY_ID_VARIABLE}."
        ),
    )
    args = parser.parse_args(argv)

    load_dotenv(override=False)
    settings = load_settings()
    country_id = args.country_id or settings.seed_country_id
    database = Database(settings.database_url)

    try:
        directory = None if country_id else build_geography_directory(settings)

        with database.session_factory() as session:
            stats = load_seed(
                session,
                country_id=country_id,
                country_directory=directory,
            )

    except (PartyIdentityError, TokenRequestError, ValueError) as exc:
        print(f"Error: la carga inicial no escribió datos. {exc}", file=sys.stderr)
        return 1

    finally:
        database.dispose()

    mode = "país explícito" if stats.mode == "explicit" else "Geography (COL)"
    print(f"Modo: {mode}; país {stats.country_id}")
    print(f"identification_type_rules: {stats.created} creadas, {stats.skipped} omitidas")

    for warning in stats.warnings:
        print(f"Advertencia: {warning}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
