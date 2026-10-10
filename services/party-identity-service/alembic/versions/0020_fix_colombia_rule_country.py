"""Corrige el país de las 8 reglas colombianas de las migraciones históricas (G-017-01).

Revision ID: 0020_fix_co_rule_country
Revises: 0019_audit_outbox
Create Date: 2026-10-09

Las migraciones `0006` y `0010` (históricas, intocables: Principio VIII) insertan las 8 reglas
colombianas con el UUID fijo `cf160c2d-…`, que era el `id` de Colombia en el Geography de desarrollo
de septiembre (C-12). En un Geography cargado desde su `seed`, Colombia tiene otro `id` y esas reglas
apuntan a un país inexistente; además, el `seed` de Party Identity crea 8 copias equivalentes con el
país real.

Esta migración, sin llamadas HTTP (las bases de los microservicios son independientes y no hay FK
hacia Geography):

- toma el `id` de Colombia **del entorno** en `PARTY_IDENTITY_SEED_COUNTRY_ID` (la misma variable del
  modo país explícito del `seed`); si no está definida, falla sin escribir nada. Ningún UUID de
  Geography se trata como canónico: el identificador de negocio del país sigue siendo `COL`;
- identifica las 8 reglas por sus `id` fijos y cambia `country_id` **solo** si todavía apuntan al UUID
  histórico (en un entorno donde Colombia es `cf160c2d-…` no cambia nada);
- opción A (decisión del usuario, 2026-10-09): las 8 reglas históricas quedan activas con el país
  corregido y sus copias activas creadas por el `seed` (`system:party-identity-seed`) se retiran
  (`is_active = false` y `valid_to`, como `/deactivate`); no se borra ningún registro (D7);
- guarda el estado anterior de cada fila tocada en `identification_type_rule_country_corrections`,
  que documenta la corrección y permite que el `downgrade` restaure exactamente `country_id`,
  `is_active`, `valid_to`, `version`, `updated_by` y `updated_at`.

Falla de forma explícita, sin escribir, si otra regla apunta al UUID histórico, si la copia
equivalente no la creó el `seed` o si su patrón, sigla o edades difieren de la regla histórica.
Como el `seed`, la corrección no se audita (no hay autor autenticado).
"""

import os
from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from alembic import op

revision: str = "0020_fix_co_rule_country"
down_revision: str | None = "0019_audit_outbox"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COUNTRY_VARIABLE = "PARTY_IDENTITY_SEED_COUNTRY_ID"
HISTORIC_COUNTRY_ID = "cf160c2d-b6de-4ef5-9257-a0a8539058d9"
MIGRATION_ACTOR = "system:party-identity-migration"
SEED_ACTOR = "system:party-identity-seed"
CORRECTIONS_TABLE = "identification_type_rule_country_corrections"

# Reglas insertadas por 0006 (personas) y 0010 (NIT de organización): (party_kind, tipo) -> id.
HISTORIC_RULE_IDS = {
    ("PERSON", "CIVIL_REGISTRY"): "f1d6549f-7fbb-58bf-8573-b2c629f3d6ae",
    ("PERSON", "IDENTITY_CARD_MODERN"): "09eb08a5-50fc-51bd-a163-9a8493138f02",
    ("PERSON", "IDENTITY_CARD_OLD"): "475acf19-dde0-560d-817f-eec73217fed8",
    ("PERSON", "CITIZEN_ID_MODERN"): "b645336b-b71e-5006-8990-e791a57014d0",
    ("PERSON", "CITIZEN_ID_OLD"): "8628a6ba-2d1c-59fc-a6c9-e8b66452effa",
    ("PERSON", "FOREIGN_CARD"): "a3e75773-1168-5e38-9a21-7354fe7cf38f",
    ("PERSON", "TAX_ID"): "48f7382b-7443-5130-b96e-c19f8f819cc2",
    ("ORGANIZATION", "TAX_ID"): "9c4f89ac-3a77-56e4-9f10-d765c1236df2",
}

SEMANTIC_COLUMNS = ("sigla", "number_pattern", "min_age_years", "max_age_years")


def _country_id() -> str:
    value = (os.environ.get(COUNTRY_VARIABLE) or "").strip()

    if not value:
        raise RuntimeError(
            f"La migración 0020 necesita {COUNTRY_VARIABLE} con el UUID de Colombia (COL) en el "
            "Geography de este entorno (GET /global-countries?iso3_code=COL). Defínala y repita "
            "'alembic upgrade head'; no se escribió nada."
        )

    try:
        return str(UUID(value))
    except ValueError:
        raise RuntimeError(
            f"{COUNTRY_VARIABLE} no es un UUID válido ('{value}'); no se escribió nada."
        ) from None


def upgrade() -> None:
    country_id = _country_id()
    connection = op.get_bind()

    op.create_table(
        CORRECTIONS_TABLE,
        sa.Column("rule_id", sa.Uuid(), primary_key=True),
        sa.Column("correction", sa.String(30), nullable=False),
        sa.Column("previous_country_id", sa.Uuid(), nullable=False),
        sa.Column("new_country_id", sa.Uuid(), nullable=False),
        sa.Column("previous_is_active", sa.Boolean(), nullable=False),
        sa.Column("previous_valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("previous_version", sa.Integer(), nullable=False),
        sa.Column("previous_updated_by", sa.String(255), nullable=False),
        sa.Column("previous_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "correction IN ('COUNTRY_CORRECTED', 'DUPLICATE_RETIRED')",
            name=f"ck_{CORRECTIONS_TABLE}_correction",
        ),
    )

    if country_id == HISTORIC_COUNTRY_ID:
        # Colombia conserva en este entorno el UUID histórico: las reglas ya son válidas.
        return

    historic_ids = list(HISTORIC_RULE_IDS.values())
    others = connection.execute(
        sa.text(
            "SELECT count(*) FROM identification_type_rules "
            "WHERE country_id = :historic AND NOT (id = ANY(CAST(:ids AS uuid[])))"
        ),
        {"historic": HISTORIC_COUNTRY_ID, "ids": historic_ids},
    ).scalar_one()

    if others:
        raise RuntimeError(
            f"La migración 0020 encontró {others} regla(s) con el UUID histórico "
            f"{HISTORIC_COUNTRY_ID} que no son las 8 reglas de 0006/0010; revíselas antes de "
            "migrar. No se escribió nada."
        )

    rules = connection.execute(
        sa.text(
            "SELECT id, party_kind, identification_type, sigla, number_pattern, min_age_years, "
            "max_age_years, is_active FROM identification_type_rules "
            "WHERE id = ANY(CAST(:ids AS uuid[])) AND country_id = :historic "
            "ORDER BY party_kind, identification_type"
        ),
        {"ids": historic_ids, "historic": HISTORIC_COUNTRY_ID},
    ).mappings().all()

    for rule in rules:
        if rule["is_active"]:
            _retire_seed_copy(connection, rule, country_id)

        _record(connection, rule["id"], "COUNTRY_CORRECTED", country_id)
        connection.execute(
            sa.text(
                "UPDATE identification_type_rules SET country_id = :country, version = version + 1, "
                "updated_by = :actor, updated_at = now() WHERE id = :id"
            ),
            {"country": country_id, "actor": MIGRATION_ACTOR, "id": rule["id"]},
        )


def _retire_seed_copy(connection: sa.Connection, rule: sa.RowMapping, country_id: str) -> None:
    """Retira la copia activa equivalente creada por el `seed` con el país real."""
    copy = connection.execute(
        sa.text(
            "SELECT id, created_by, sigla, number_pattern, min_age_years, max_age_years, "
            "valid_from <= now() AS started FROM identification_type_rules "
            "WHERE party_kind = :party_kind AND identification_type = :identification_type "
            "AND country_id = :country AND is_active AND id <> :id"
        ),
        {
            "party_kind": rule["party_kind"],
            "identification_type": rule["identification_type"],
            "country": country_id,
            "id": rule["id"],
        },
    ).mappings().one_or_none()

    if copy is None:
        return

    label = f"{rule['party_kind']}/{rule['identification_type']}"

    if copy["created_by"] != SEED_ACTOR:
        raise RuntimeError(
            f"La regla activa {copy['id']} ({label}) para el país {country_id} no la creó el seed "
            f"({copy['created_by']}); la migración 0020 no la retira. No se escribió nada."
        )

    differences = [column for column in SEMANTIC_COLUMNS if copy[column] != rule[column]]

    if differences:
        raise RuntimeError(
            f"La copia del seed {copy['id']} ({label}) difiere de la regla histórica "
            f"{rule['id']} en {', '.join(differences)}; la migración 0020 no elige entre ellas. "
            "No se escribió nada."
        )

    _record(connection, copy["id"], "DUPLICATE_RETIRED", country_id)
    # Igual que `/deactivate`: `valid_to` solo se fija si la regla ya entró en vigencia.
    connection.execute(
        sa.text(
            "UPDATE identification_type_rules SET is_active = false, "
            "valid_to = CASE WHEN :started AND (valid_to IS NULL OR valid_to > now()) "
            "THEN now() ELSE valid_to END, "
            "version = version + 1, updated_by = :actor, updated_at = now() WHERE id = :id"
        ),
        {"started": copy["started"], "actor": MIGRATION_ACTOR, "id": copy["id"]},
    )


def _record(connection: sa.Connection, rule_id: UUID, correction: str, country_id: str) -> None:
    connection.execute(
        sa.text(
            f"INSERT INTO {CORRECTIONS_TABLE} (rule_id, correction, previous_country_id, "
            "new_country_id, previous_is_active, previous_valid_to, previous_version, "
            "previous_updated_by, previous_updated_at) "
            "SELECT id, :correction, country_id, :country, is_active, valid_to, version, "
            "updated_by, updated_at FROM identification_type_rules WHERE id = :id"
        ),
        {"correction": correction, "country": country_id, "id": rule_id},
    )


def downgrade() -> None:
    connection = op.get_bind()
    restore = (
        "UPDATE identification_type_rules AS rule SET country_id = fix.previous_country_id, "
        "is_active = fix.previous_is_active, valid_to = fix.previous_valid_to, "
        "version = fix.previous_version, updated_by = fix.previous_updated_by, "
        f"updated_at = fix.previous_updated_at FROM {CORRECTIONS_TABLE} AS fix "
        "WHERE rule.id = fix.rule_id AND fix.correction = :correction"
    )

    # Primero las reglas históricas (liberan la llave activa del país real), luego las copias.
    connection.execute(sa.text(restore), {"correction": "COUNTRY_CORRECTED"})
    connection.execute(sa.text(restore), {"correction": "DUPLICATE_RETIRED"})
    op.drop_table(CORRECTIONS_TABLE)
