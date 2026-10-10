"""Carga idempotente de las reglas iniciales (FR-016, FR-017, R-10).

- Llave natural: `party_kind` + `country_id` + `identification_type` entre
  reglas **activas**. Si ya existe, se omite (no se sobrescribe: los cambios
  posteriores se hacen con versiones de regla).
- El país se resuelve **antes** de escribir: con `country_id` explícito (modo
  independiente, sin Geography) o consultando `COL` en Geography.
- Todo ocurre en una transacción: un error no deja filas escritas.
- Las 8 reglas de las migraciones históricas (ids fijos, `HISTORIC_RULE_IDS`) cuentan como
  existentes una vez que la migración 0020 corrigió su país. Si alguna sigue activa con otro país
  (migración pendiente o país distinto del de `PARTY_IDENTITY_SEED_COUNTRY_ID`), la carga se
  rechaza sin escribir en vez de crear copias equivalentes (G-017-01).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from party_identity_service.application.ports import CountryDirectory
from party_identity_service.infrastructure.models import IdentificationTypeRuleModel
from party_identity_service.seed.constants import (
    COUNTRY_ISO3,
    HISTORIC_RULE_IDS,
    SEED_ACTOR,
)
from party_identity_service.seed.data import COLOMBIAN_RULES


class HistoricRuleCountryMismatchError(ValueError):
    """Una regla histórica activa está asociada a un país distinto del resuelto."""


@dataclass(slots=True)
class SeedStats:
    """Resultado de una ejecución del `seed`.

    Attributes:
        country_id: País usado para las reglas.
        mode: `explicit` (país indicado) o `geography` (resuelto por `COL`).
        created: Reglas creadas.
        skipped: Reglas omitidas porque ya existía una activa.
        warnings: Reglas activas equivalentes asociadas a otro país.
    """

    country_id: UUID
    mode: str
    created: int = 0
    skipped: int = 0
    warnings: list[str] = field(default_factory=list)


def resolve_country(
    *,
    country_id: UUID | None,
    country_directory: CountryDirectory | None,
) -> tuple[UUID, str]:
    """Determina el país de las reglas y el modo usado.

    Raises:
        ValueError: Si no hay país explícito ni puerto de Geography.
        CountryNotFoundError, DependencyUnavailableError: Desde Geography.
    """
    if country_id is not None:
        return country_id, "explicit"

    if country_directory is None:
        raise ValueError(
            "Indique el país con --country-id o PARTY_IDENTITY_SEED_COUNTRY_ID, "
            "o configure el acceso a Geography."
        )

    return country_directory.find_id_by_iso3(COUNTRY_ISO3), "geography"


def load_seed(
    session: Session,
    *,
    country_id: UUID | None = None,
    country_directory: CountryDirectory | None = None,
) -> SeedStats:
    """Carga las reglas iniciales de Colombia de forma idempotente.

    Args:
        session: Sesión de la base del servicio.
        country_id: UUID explícito del país (modo independiente).
        country_directory: Puerto de Geography (modo por defecto).

    Returns:
        Estadísticas de la carga.
    """
    resolved_country, mode = resolve_country(
        country_id=country_id,
        country_directory=country_directory,
    )
    stats = SeedStats(country_id=resolved_country, mode=mode)

    try:
        _check_historic_rules(session, resolved_country)

        for rule in COLOMBIAN_RULES:
            existing = session.scalar(
                select(IdentificationTypeRuleModel.id).where(
                    IdentificationTypeRuleModel.party_kind == rule["party_kind"],
                    IdentificationTypeRuleModel.country_id == resolved_country,
                    IdentificationTypeRuleModel.identification_type
                    == rule["identification_type"],
                    IdentificationTypeRuleModel.is_active.is_(True),
                )
            )

            if existing is not None:
                stats.skipped += 1
                continue

            session.add(
                IdentificationTypeRuleModel(
                    **rule,
                    country_id=resolved_country,
                    is_active=True,
                    created_by=SEED_ACTOR,
                    updated_by=SEED_ACTOR,
                )
            )
            stats.created += 1

        stats.warnings = _foreign_country_rules(session, resolved_country)
        session.commit()

    except Exception:
        session.rollback()
        raise

    return stats


def _check_historic_rules(session: Session, country_id: UUID) -> None:
    """Rechaza la carga si una regla histórica activa apunta a otro país.

    Crear la regla del `seed` en ese caso dejaría dos reglas colombianas equivalentes (una de
    ellas huérfana si su país no existe en Geography).
    """
    rows = session.execute(
        select(
            IdentificationTypeRuleModel.id,
            IdentificationTypeRuleModel.party_kind,
            IdentificationTypeRuleModel.identification_type,
            IdentificationTypeRuleModel.country_id,
        ).where(
            IdentificationTypeRuleModel.id.in_([UUID(value) for value in HISTORIC_RULE_IDS.values()]),
            IdentificationTypeRuleModel.is_active.is_(True),
            IdentificationTypeRuleModel.country_id != country_id,
        )
    ).all()

    if rows:
        rule_id, party_kind, identification_type, other_country = rows[0]
        raise HistoricRuleCountryMismatchError(
            f"{len(rows)} regla(s) histórica(s) de las migraciones siguen activas con otro país "
            f"(p. ej. {rule_id} {party_kind}/{identification_type} → {other_country}; país resuelto "
            f"{country_id}). Aplique 'alembic upgrade head' con PARTY_IDENTITY_SEED_COUNTRY_ID igual "
            "al UUID de Colombia de este entorno; la carga no crea copias equivalentes."
        )


def _foreign_country_rules(session: Session, country_id: UUID) -> list[str]:
    """Reglas activas equivalentes asociadas a otro país (p. ej. un UUID de
    Colombia no canónico dejado por migraciones históricas, C-12)."""
    keys = {
        (rule["party_kind"], rule["identification_type"])
        for rule in COLOMBIAN_RULES
    }
    rows = session.execute(
        select(
            IdentificationTypeRuleModel.party_kind,
            IdentificationTypeRuleModel.identification_type,
            IdentificationTypeRuleModel.country_id,
        ).where(
            IdentificationTypeRuleModel.is_active.is_(True),
            IdentificationTypeRuleModel.country_id != country_id,
        )
    ).all()

    return [
        f"Regla activa {party_kind}/{identification_type} asociada a otro país "
        f"({other_country}); no se modifica."
        for party_kind, identification_type, other_country in rows
        if (party_kind, identification_type) in keys
    ]
