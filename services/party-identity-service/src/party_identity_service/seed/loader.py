"""Carga idempotente de las reglas iniciales (FR-016, FR-017, R-10).

- Llave natural: `party_kind` + `country_id` + `identification_type` entre
  reglas **activas**. Si ya existe, se omite (no se sobrescribe: los cambios
  posteriores se hacen con versiones de regla).
- El país se resuelve **antes** de escribir: con `country_id` explícito (modo
  independiente, sin Geography) o consultando `COL` en Geography.
- Todo ocurre en una transacción: un error no deja filas escritas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from party_identity_service.application.ports import CountryDirectory
from party_identity_service.infrastructure.models import IdentificationTypeRuleModel
from party_identity_service.seed.constants import COUNTRY_ISO3, SEED_ACTOR
from party_identity_service.seed.data import COLOMBIAN_RULES


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
