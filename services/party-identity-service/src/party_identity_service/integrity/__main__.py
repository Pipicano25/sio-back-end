"""Validadores de integridad.

- `python -m party_identity_service.integrity country-references`: `country_id` de las reglas de
  identificación ⊆ países de Geography. Lee la base del servicio (`DATABASE_URL`) y consulta
  Geography con el token técnico del cliente `party-identity-service` (mismas variables que el
  `seed` en modo Geography). Solo lectura.

Códigos de salida: `0` sin referencias huérfanas; `1` hay huérfanas; `2` no se pudo validar
(Geography, Keycloak o configuración).
"""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

from party_identity_service.application.exceptions import PartyIdentityError
from party_identity_service.config import load_settings
from party_identity_service.infrastructure.database import Database
from party_identity_service.infrastructure.keycloak_token_client import TokenRequestError
from party_identity_service.integrity.country_references import (
    check_rule_country_references,
    rule_country_pairs,
)
from party_identity_service.seed.__main__ import build_geography_directory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m party_identity_service.integrity",
        description="Validadores de integridad de Party Identity frente a Geography.",
    )
    parser.add_argument("command", choices=["country-references"], help="Validación a ejecutar.")
    parser.parse_args(argv)

    load_dotenv(override=False)
    settings = load_settings()
    database = Database(settings.database_url)

    try:
        directory = build_geography_directory(settings)

        with database.session_factory() as session:
            pairs = rule_country_pairs(session)

        report = check_rule_country_references(pairs, directory)

    except (PartyIdentityError, TokenRequestError) as exc:
        print(f"Error: no se pudo validar contra Geography. {exc}", file=sys.stderr)
        return 2

    finally:
        database.dispose()

    print(
        f"identification_type_rules: {report.checked_rules} reglas, "
        f"{len(report.rules_by_country)} países referenciados"
    )

    for country_id, count in sorted(report.rules_by_country.items(), key=lambda item: str(item[0])):
        state = "INEXISTENTE en Geography" if country_id in report.orphans else "existe en Geography"
        print(f"  {country_id}: {count} reglas, {state}")

    for country_id, rule_ids in report.orphans.items():
        print(f"Huérfanas de {country_id}: {', '.join(str(rule_id) for rule_id in rule_ids)}")

    print(f"Referencias huérfanas: {report.orphan_count}")

    return 1 if report.orphan_count else 0


if __name__ == "__main__":
    sys.exit(main())
