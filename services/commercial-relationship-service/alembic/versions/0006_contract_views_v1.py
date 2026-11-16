"""Vistas de contrato v1 de Commercial Relationship para Sales (constitución 3.0.0, D27; spec 025, T039).

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-16

Crea el esquema ``contract`` y cuatro vistas de solo lectura (contracts/contract-views.md, sección CR):

- ``v1_company_products``: reemplaza ``company-products/batch-lookup`` y el conteo de
  ``GET /companies/{c}/company-products``.
- ``v1_company_product_presentations``: reemplaza ``company-product-presentations/batch-lookup`` y ``by-products``.
- ``v1_company_customers``: reemplaza ``GET /company-customers/{id}`` y la búsqueda por identidad.
- ``v1_price_lists``: reemplaza ``GET /price-lists/{id}``.

Todas las columnas son columnas directas de su tabla (ninguna se deriva). Las vistas incluyen todas las empresas y
todos los estados: el consumidor filtra por ``company_id`` y decide qué hacer con un estado no ``ACTIVE``, como hoy
con la respuesta del API.

Las vistas de compras (proveedores, condiciones de pago, productos de proveedor y cobertura de precios) se publican
en una migración posterior. Los cambios compatibles se hacen con ``CREATE OR REPLACE VIEW`` agregando columnas al
final; un cambio incompatible crea ``v2_``. Los roles de lectura no se crean aquí
(``contract/grants.yaml`` e ``infrastructure/scripts/contract-readers``).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VIEWS = ("v1_company_products", "v1_company_product_presentations", "v1_company_customers", "v1_price_lists")

COMPANY_PRODUCTS = """
CREATE OR REPLACE VIEW contract.v1_company_products AS
SELECT p.id,
       p.company_id,
       p.global_product_id,
       p.internal_code,
       p.reference_code,
       p.display_name,
       p.status,
       p.is_sellable,
       p.is_purchasable,
       p.inventory_control_enabled,
       p.purchase_tax_percentage,
       p.created_at
  FROM public.company_products p
"""

COMPANY_PRODUCT_PRESENTATIONS = """
CREATE OR REPLACE VIEW contract.v1_company_product_presentations AS
SELECT pp.id,
       pp.company_id,
       pp.company_product_id,
       pp.global_product_presentation_id,
       pp.internal_code,
       pp.sku,
       pp.reference_code,
       pp.is_sellable,
       pp.is_purchasable,
       pp.status
  FROM public.company_product_presentations pp
"""

COMPANY_CUSTOMERS = """
CREATE OR REPLACE VIEW contract.v1_company_customers AS
SELECT c.id,
       c.company_id,
       c.customer_kind,
       c.person_identity_id,
       c.organization_identity_id,
       c.display_name,
       c.status
  FROM public.company_customers c
"""

PRICE_LISTS = """
CREATE OR REPLACE VIEW contract.v1_price_lists AS
SELECT l.id, l.company_id, l.status
  FROM public.price_lists l
"""


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS contract")
    for statement in (COMPANY_PRODUCTS, COMPANY_PRODUCT_PRESENTATIONS, COMPANY_CUSTOMERS, PRICE_LISTS):
        op.execute(statement)
    for view in VIEWS:
        op.execute(f"COMMENT ON VIEW contract.{view} IS 'Vista de contrato de commercial-relationship (D27, spec 025).'")


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
