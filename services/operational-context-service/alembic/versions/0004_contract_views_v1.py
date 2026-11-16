"""Vistas de contrato v1 de Operational Context (constitución 3.0.0, D27; spec 025, T021).

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-15

Crea el esquema ``contract`` y cinco vistas de solo lectura para los consumidores (contracts/contract-views.md):

- ``v1_operational_access``: una fila por membresía elegida y empresa (``branch_id`` nulo) y otra por cada sucursal
  de esa empresa. ``denial_reason`` es la primera causa que falla en el orden de ``domain/access.py``
  (``USER_MEMBERSHIP_INACTIVE`` → ``COMPANY_INACTIVE`` → ``BRANCH_INACTIVE`` → ``BRANCH_NOT_ASSIGNED`` →
  ``USER_BRANCH_INACTIVE``), o nulo si se permite. Sin fila → ``USER_NOT_MEMBER``. El permiso lo evalúa el
  consumidor con el token, como hoy hace ``operational-access``.
- ``v1_companies``, ``v1_branches``, ``v1_application_users`` y ``v1_user_memberships``.

La membresía se elige igual que ``membership_lookup.find_membership``: la ``ACTIVE`` primero y, entre las demás, la
más reciente por ``updated_at`` y luego ``id``.

Los cambios compatibles se hacen con ``CREATE OR REPLACE VIEW`` agregando columnas al final; un cambio
incompatible crea ``v2_``. Los roles de lectura no se crean aquí (infrastructure/scripts/contract-readers).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VIEWS = ("v1_operational_access", "v1_companies", "v1_branches", "v1_application_users", "v1_user_memberships")

OPERATIONAL_ACCESS = """
CREATE OR REPLACE VIEW contract.v1_operational_access AS
WITH m AS NOT MATERIALIZED (
    SELECT DISTINCT ON (u.company_id, u.keycloak_user_id)
           u.id AS application_user_id,
           u.company_id,
           u.keycloak_user_id,
           u.status AS membership_status
      FROM public.application_users u
     ORDER BY u.company_id, u.keycloak_user_id, (u.status = 'ACTIVE') DESC, u.updated_at DESC, u.id
)
SELECT m.keycloak_user_id,
       c.id AS company_id,
       NULL::uuid AS branch_id,
       m.application_user_id,
       CASE
           WHEN m.membership_status <> 'ACTIVE' THEN 'USER_MEMBERSHIP_INACTIVE'
           WHEN c.status <> 'ACTIVE' THEN 'COMPANY_INACTIVE'
       END::varchar(40) AS denial_reason
  FROM m
  JOIN public.companies c ON c.id = m.company_id
UNION ALL
SELECT m.keycloak_user_id,
       c.id AS company_id,
       b.id AS branch_id,
       m.application_user_id,
       CASE
           WHEN m.membership_status <> 'ACTIVE' THEN 'USER_MEMBERSHIP_INACTIVE'
           WHEN c.status <> 'ACTIVE' THEN 'COMPANY_INACTIVE'
           WHEN b.status <> 'ACTIVE' THEN 'BRANCH_INACTIVE'
           WHEN ub.id IS NULL THEN 'BRANCH_NOT_ASSIGNED'
           WHEN ub.status <> 'ACTIVE' THEN 'USER_BRANCH_INACTIVE'
       END::varchar(40) AS denial_reason
  FROM m
  JOIN public.companies c ON c.id = m.company_id
  JOIN public.branches b ON b.company_id = c.id
  LEFT JOIN public.user_branches ub ON ub.application_user_id = m.application_user_id AND ub.branch_id = b.id
"""

COMPANIES = """
CREATE OR REPLACE VIEW contract.v1_companies AS
SELECT c.id, c.status, c.organization_identity_id, c.default_currency, c.timezone
  FROM public.companies c
"""

BRANCHES = """
CREATE OR REPLACE VIEW contract.v1_branches AS
SELECT b.id,
       b.company_id,
       b.code,
       b.name,
       b.status,
       c.status AS company_status,
       coalesce(b.timezone, c.timezone) AS effective_timezone,
       b.created_at
  FROM public.branches b
  JOIN public.companies c ON c.id = b.company_id
"""

APPLICATION_USERS = """
CREATE OR REPLACE VIEW contract.v1_application_users AS
SELECT u.id, u.company_id, u.keycloak_user_id, u.status, c.status AS company_status
  FROM public.application_users u
  JOIN public.companies c ON c.id = u.company_id
"""

USER_MEMBERSHIPS = """
CREATE OR REPLACE VIEW contract.v1_user_memberships AS
SELECT u.keycloak_user_id,
       u.id AS application_user_id,
       u.company_id,
       u.status,
       c.status AS company_status,
       u.created_at
  FROM public.application_users u
  JOIN public.companies c ON c.id = u.company_id
"""


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS contract")
    for statement in (OPERATIONAL_ACCESS, COMPANIES, BRANCHES, APPLICATION_USERS, USER_MEMBERSHIPS):
        op.execute(statement)
    for view in VIEWS:
        op.execute(f"COMMENT ON VIEW contract.{view} IS 'Vista de contrato de operational-context (D27, spec 025).'")


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
