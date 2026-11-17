"""Vistas de contrato v1 del resumen de productos (constitución 3.0.0, D27; spec 025, T072).

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-17

Agrega al esquema ``contract`` tres vistas de solo lectura que reemplazan ``POST /products/summaries/batch-lookup``
(PC-1) **sin campos de imagen** (la URL firmada sigue por API, FR-036). Consumidores: PIQ y Business Reporting
(contracts/contract-views.md):

- ``v1_product_summaries``: ``id``, ``canonical_name``, ``product_type``, ``status``, ``brand_id``, ``brand_code``,
  ``brand_name``, ``base_unit_id``, ``base_unit_code``, ``base_unit_name``. Una fila por producto en cualquier estado
  (PC-1 no filtra por estado). Marca y unidad con ``LEFT JOIN``: sin marca, las tres columnas de marca son nulas, como
  ``brand: null`` en PC-1.
- ``v1_product_summary_categories``: ``global_product_id``, ``category_id``, ``code``, ``name``, ``is_primary``. Solo
  asociaciones ``ACTIVE`` (como PC-1); el consumidor ordena por ``is_primary DESC, code``, el orden de PC-1.
- ``v1_product_summary_identifiers``: ``global_product_id``, ``identifier_type``, ``value``, ``is_primary``,
  ``global_product_presentation_id``. Solo identificadores ``ACTIVE``; el consumidor ordena por
  ``is_primary DESC, identifier_type, value``, el orden de PC-1.

Las vistas no ordenan: el orden lo fija la consulta del consumidor, en la misma base y con la misma intercalación que
usa PC-1. Los cambios compatibles se hacen con ``CREATE OR REPLACE VIEW`` agregando columnas al final; un cambio
incompatible crea ``v2_``. Los roles de lectura no se crean aquí (infrastructure/scripts/contract-readers, con
``contract/grants.yaml``).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VIEWS = ("v1_product_summaries", "v1_product_summary_categories", "v1_product_summary_identifiers")

SUMMARIES = """
CREATE OR REPLACE VIEW contract.v1_product_summaries AS
SELECT p.id,
       p.canonical_name,
       p.product_type,
       p.status,
       b.id AS brand_id,
       b.code AS brand_code,
       b.name AS brand_name,
       u.id AS base_unit_id,
       u.code AS base_unit_code,
       u.name AS base_unit_name
  FROM public.global_products p
  LEFT JOIN public.global_brands b ON b.id = p.global_brand_id
  LEFT JOIN public.global_units_of_measure u ON u.id = p.base_unit_id
"""

CATEGORIES = """
CREATE OR REPLACE VIEW contract.v1_product_summary_categories AS
SELECT pc.global_product_id,
       c.id AS category_id,
       c.code,
       c.name,
       pc.is_primary
  FROM public.global_product_categories pc
  JOIN public.global_categories c ON c.id = pc.global_category_id
 WHERE pc.status = 'ACTIVE'
"""

IDENTIFIERS = """
CREATE OR REPLACE VIEW contract.v1_product_summary_identifiers AS
SELECT i.global_product_id,
       i.identifier_type,
       i.value,
       i.is_primary,
       i.global_product_presentation_id
  FROM public.global_product_identifiers i
 WHERE i.status = 'ACTIVE'
"""


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS contract")
    for statement in (SUMMARIES, CATEGORIES, IDENTIFIERS):
        op.execute(statement)
    for view in VIEWS:
        op.execute(f"COMMENT ON VIEW contract.{view} IS 'Vista de contrato de product-catalog (D27, spec 025).'")


def downgrade() -> None:
    for view in reversed(VIEWS):
        op.execute(f"DROP VIEW IF EXISTS contract.{view}")
