"""Vista de contrato v1 de personas de contacto (constitución 3.0.0, D27; spec 025, T059).

Revision ID: 0022_contract_contact_persons_v1
Revises: 0021_contract_views_v1
Create Date: 2026-11-16

Crea ``contract.v1_organization_contact_persons`` con ``id``, ``organization_identity_id``, ``person_identity_id`` e
``is_active``: los mismos valores de ``GET /organization-contact-persons/{id}``, en cualquier estado (activas e
inactivas). La consume Commercial Relationship para validar que la persona de contacto de un cliente o proveedor
pertenece a su organización y está vigente. No se publican cargo, correo, teléfono ni ``is_primary``.

Los cambios compatibles se hacen con ``CREATE OR REPLACE VIEW`` agregando columnas al final; un cambio
incompatible crea ``v2_``. Los roles de lectura no se crean aquí (infrastructure/scripts/contract-readers).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0022_contract_contact_persons_v1"
down_revision: str | None = "0021_contract_views_v1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VIEW = "v1_organization_contact_persons"

CONTACT_PERSONS = """
CREATE OR REPLACE VIEW contract.v1_organization_contact_persons AS
SELECT c.id,
       c.organization_identity_id,
       c.person_identity_id,
       c.is_active
  FROM public.organization_contact_persons c
"""


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS contract")
    op.execute(CONTACT_PERSONS)
    op.execute(f"COMMENT ON VIEW contract.{VIEW} IS 'Vista de contrato de party-identity (D27, spec 025).'")


def downgrade() -> None:
    op.execute(f"DROP VIEW IF EXISTS contract.{VIEW}")
