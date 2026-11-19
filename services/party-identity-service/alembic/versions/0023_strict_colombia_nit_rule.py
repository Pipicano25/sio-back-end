"""NIT colombiano estricto: base solo numérica de 6 a 10 dígitos (enmienda del 2026-11-18).

Revision ID: 0023_strict_co_nit_rule
Revises: 0022_contract_contact_persons_v1
Create Date: 2026-11-18

Las dos reglas `NIT` de Colombia (persona y organización) aceptaban una base alfanumérica de 4 a 11
caracteres (`^[A-Z0-9]{4,11}-[0-9]$`), lo que dejaba pasar valores como `GENERICO-0`, que no son un
NIT. Esta migración cambia su patrón a `^[0-9]{6,10}-[0-9]$`, con la descripción y el ejemplo
nuevos. El dígito de verificación (módulo 11 de la DIAN) lo valida la aplicación.

Solo cambia las reglas `NIT` activas que todavía tienen el patrón anterior: las de las migraciones
históricas (ids fijos) y, si existieran, las equivalentes del `seed`. Sube su `version`. Como el
`seed`, el cambio no se audita (no hay autor autenticado).

Antes de aplicarla, ninguna identidad activa debe tener un NIT con letras: la migración falla sin
escribir si encuentra alguno, para no dejar identidades que la regla nueva rechazaría.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023_strict_co_nit_rule"
down_revision: str | None = "0022_contract_contact_persons_v1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACTOR = "system:party-identity-migration"

OLD_PATTERN = "^[A-Z0-9]{4,11}-[0-9]$"
NEW_PATTERN = "^[0-9]{6,10}-[0-9]$"

OLD_EXAMPLE = "900123456-7"
NEW_EXAMPLE = "900123456-8"

DESCRIPTIONS = {
    "PERSON": (
        "Numero de Identificacion Tributaria: base alfanumerica de 4 a 11 "
        "caracteres, guion y digito de verificacion.",
        "Numero de Identificacion Tributaria: base de 6 a 10 digitos, guion "
        "y digito de verificacion de la DIAN (modulo 11).",
    ),
    "ORGANIZATION": (
        "Numero de Identificacion Tributaria de organizacion: base "
        "alfanumerica de 4 a 11 caracteres, guion y digito de verificacion.",
        "Numero de Identificacion Tributaria de organizacion: base de 6 a 10 "
        "digitos, guion y digito de verificacion de la DIAN (modulo 11).",
    ),
}

IDENTITY_TABLES = {
    "PERSON": "person_identities",
    "ORGANIZATION": "organization_identities",
}


def _check_identities(bind: sa.Connection) -> None:
    """Falla si alguna identidad activa con NIT no cumple el patrón nuevo."""
    for party_kind, table in IDENTITY_TABLES.items():
        count = bind.execute(
            sa.text(
                f"""
                SELECT count(*) FROM {table}
                WHERE identification_type = 'NIT'
                  AND status = 'ACTIVE'
                  AND identification_number !~ :pattern
                """
            ),
            {"pattern": NEW_PATTERN},
        ).scalar_one()

        if count:
            raise RuntimeError(
                f"{count} identidad(es) {party_kind} activas tienen un NIT que no cumple "
                f"{NEW_PATTERN}. Corríjalas o inactívelas antes de aplicar 0023."
            )


def _replace(bind: sa.Connection, *, old: str, new: str, old_example: str, new_example: str,
             descriptions_index: tuple[int, int]) -> None:
    for party_kind, texts in DESCRIPTIONS.items():
        bind.execute(
            sa.text(
                """
                UPDATE identification_type_rules
                SET number_pattern = :new,
                    number_pattern_description = :description,
                    example_value = CASE WHEN example_value = :old_example
                                         THEN :new_example ELSE example_value END,
                    version = version + 1,
                    updated_by = :actor,
                    updated_at = now()
                WHERE sigla = 'NIT'
                  AND party_kind = :party_kind
                  AND is_active = true
                  AND number_pattern = :old
                """
            ),
            {
                "new": new,
                "old": old,
                "description": texts[descriptions_index[1]],
                "old_example": old_example,
                "new_example": new_example,
                "actor": ACTOR,
                "party_kind": party_kind,
            },
        )


def upgrade() -> None:
    bind = op.get_bind()
    _check_identities(bind)
    _replace(bind, old=OLD_PATTERN, new=NEW_PATTERN, old_example=OLD_EXAMPLE,
             new_example=NEW_EXAMPLE, descriptions_index=(0, 1))


def downgrade() -> None:
    _replace(op.get_bind(), old=NEW_PATTERN, new=OLD_PATTERN, old_example=NEW_EXAMPLE,
             new_example=OLD_EXAMPLE, descriptions_index=(1, 0))
