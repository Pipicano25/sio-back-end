"""Vistas de contrato v1 de Party Identity (constitución 3.0.0, D27; spec 025, T040).

Revision ID: 0021_contract_views_v1
Revises: 0020_fix_co_rule_country
Create Date: 2026-11-16

Crea el esquema ``contract`` y dos vistas de solo lectura para los consumidores (contracts/contract-views.md):

- ``v1_person_identities``: ``id``, ``identification_type``, ``identification_number``, ``first_name``,
  ``middle_name``, ``last_name``, ``second_last_name``, ``status``.
- ``v1_organization_identities``: ``id``, ``identification_type``, ``identification_number``, ``legal_name``,
  ``trade_name``, ``status``.

Cada columna es el mismo valor que devuelven ``GET /person-identities/{id}`` y ``GET /organization-identities/{id}``
(``identification_type`` es el código guardado en la tabla, sin derivar). No se publican correo, teléfono, fecha de
nacimiento, sitio web ni estado de verificación. Las vistas incluyen identidades ``ACTIVE`` e ``INACTIVE``; la
búsqueda de identidades activas la hace el consumidor con ``ILIKE`` y el orden documentado en el README.

Los cambios compatibles se hacen con ``CREATE OR REPLACE VIEW`` agregando columnas al final; un cambio
incompatible crea ``v2_``. Los roles de lectura no se crean aquí (infrastructure/scripts/contract-readers).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0021_contract_views_v1"
down_revision: str | None = "0020_fix_co_rule_country"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VIEWS = ("v1_person_identities", "v1_organization_identities")

PERSON_IDENTITIES = """
CREATE OR REPLACE VIEW contract.v1_person_identities AS
SELECT p.id,
       p.identification_type,
       p.identification_number,
       p.first_name,
       p.middle_name,
       p.last_name,
       p.second_last_name,
       p.status
  FROM public.person_identities p
"""

ORGANIZATION_IDENTITIES = """
CREATE OR REPLACE VIEW contract.v1_organization_identities AS
SELECT o.id,
       o.identification_type,
       o.identification_number,
       o.legal_name,
       o.trade_name,
       o.status
  FROM public.organization_identities o
"""


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS contract")
    for statement in (PERSON_IDENTITIES, ORGANIZATION_IDENTITIES):
        op.execute(statement)
    for view in VIEWS:
        op.execute(f"COMMENT ON VIEW contract.{view} IS 'Vista de contrato de party-identity (D27, spec 025).'")


def downgrade() -> None:
    for view in reversed(VIEWS):
        op.execute(f"DROP VIEW IF EXISTS contract.{view}")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'contract'
            ) THEN
                DROP SCHEMA IF EXISTS contract;
            END IF;
        END $$
        """
    )
