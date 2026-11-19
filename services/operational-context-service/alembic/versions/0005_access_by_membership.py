"""Acceso por membresía: la asignación a sucursal ya no limita (enmienda 2026-11-19).

La membresía `ACTIVE` da acceso a todas las sucursales activas de la empresa; los límites
los ponen los permisos de Keycloak. `contract.v1_operational_access` conserva sus columnas
y deja de producir `BRANCH_NOT_ASSIGNED` y `USER_BRANCH_INACTIVE`: el cambio es compatible
(los consumidores ya manejan el resto de causas), así que se reemplaza la ``v1``.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

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
       END::varchar(40) AS denial_reason
  FROM m
  JOIN public.companies c ON c.id = m.company_id
  JOIN public.branches b ON b.company_id = c.id
"""

PREVIOUS = """
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


def upgrade() -> None:
    op.execute(OPERATIONAL_ACCESS)


def downgrade() -> None:
    op.execute(PREVIOUS)
