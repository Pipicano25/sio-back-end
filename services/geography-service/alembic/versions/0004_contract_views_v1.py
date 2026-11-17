"""Vistas de contrato v1 de Geography (constitución 3.0.0, D27; spec 025, T067).

Revision ID: 0004
Revises: 60c72b765588
Create Date: 2026-11-17

Crea el esquema ``contract`` y tres vistas de solo lectura para Operational Context y Party Identity, que hoy
leen ``GET /global-countries/{id}``, ``GET /global-administrative-divisions/{id}`` y ``GET /global-cities/{id}``
con el token del usuario. Solo publican las columnas que esos consumidores usan de la respuesta:

- ``v1_countries``: ``id``, ``status``.
- ``v1_administrative_divisions``: ``id``, ``country_id``, ``status``.
- ``v1_cities``: ``id``, ``country_id``, ``administrative_division_id`` (nulo si la ciudad no tiene división),
  ``status``.

Las filas salen en cualquier estado, igual que el ``GET`` por id. El permiso de lectura de cada ruta
(``perm:geography:<recurso>:read``) lo comprueba el consumidor con el token del usuario (FR-037). La búsqueda de
país por ISO3 sigue por API (FR-036).

Los cambios compatibles se hacen con ``CREATE OR REPLACE VIEW`` agregando columnas al final; un cambio
incompatible crea ``v2_``. Los roles de lectura no se crean aquí (infrastructure/scripts/contract-readers).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "60c72b765588"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VIEWS = ("v1_countries", "v1_administrative_divisions", "v1_cities")

COUNTRIES = """
CREATE OR REPLACE VIEW contract.v1_countries AS
SELECT c.id, c.status
  FROM public.global_countries c
"""

ADMINISTRATIVE_DIVISIONS = """
CREATE OR REPLACE VIEW contract.v1_administrative_divisions AS
SELECT d.id, d.country_id, d.status
  FROM public.global_administrative_divisions d
"""

CITIES = """
CREATE OR REPLACE VIEW contract.v1_cities AS
SELECT c.id, c.country_id, c.administrative_division_id, c.status
  FROM public.global_cities c
"""


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS contract")
    for statement in (COUNTRIES, ADMINISTRATIVE_DIVISIONS, CITIES):
        op.execute(statement)
    for view in VIEWS:
        op.execute(f"COMMENT ON VIEW contract.{view} IS 'Vista de contrato de geography (D27, spec 025).'")


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
