"""Vistas de contrato v1 de Commercial Relationship para Purchase (constitución 3.0.0, D27; spec 025, T051).

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-16

Agrega al esquema ``contract`` (creado en ``0006``) cuatro vistas de solo lectura (contracts/contract-views.md,
sección CR):

- ``v1_company_suppliers``: reemplaza ``GET /company-suppliers/{id}``.
- ``v1_supplier_payment_conditions``: reemplaza ``GET /supplier-payment-conditions/{id}``.
- ``v1_supplier_products``: reemplaza ``GET /supplier-products/{id}``.
- ``v1_pricing_coverage``: reemplaza ``POST /companies/{c}/pricing-policies/coverage``.

Las tres primeras son columnas directas de su tabla, con todas las empresas y todos los estados (``BLOCKED`` e
``INACTIVE`` incluidos): el consumidor filtra por ``company_id`` y decide, como hoy con la respuesta del API.

``v1_pricing_coverage`` tiene una fila por (empresa, presentación, lista, moneda) para cada lista que cubre la
presentación AHORA. Replica exactamente ``PricingPolicyRepository.coverage`` (``pricing_repositories.py``): política
``ACTIVE``; asignación de la presentación y término de porcentaje vigentes en ``now()`` (``[valid_from, valid_to)``);
lista ``ACTIVE`` y vigente en ``now()`` (vigencias nulas = abiertas); política, asignación y lista de la misma empresa.
``now()`` es el inicio de la transacción del consumidor, como ``select(func.now())`` en ``PricingCoverageService``.
No expone ``markup_percentage``. ``found`` (la presentación existe en la empresa) se lee de
``v1_company_product_presentations``; la consulta de referencia está en ``tests/contract_views``.

Los cambios compatibles se hacen con ``CREATE OR REPLACE VIEW`` agregando columnas al final; un cambio incompatible
crea ``v2_``. Los permisos de lectura están en ``contract/grants.yaml``.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VIEWS = ("v1_company_suppliers", "v1_supplier_payment_conditions", "v1_supplier_products", "v1_pricing_coverage")

COMPANY_SUPPLIERS = """
CREATE OR REPLACE VIEW contract.v1_company_suppliers AS
SELECT s.id,
       s.company_id,
       s.organization_identity_id,
       s.display_name,
       s.status
  FROM public.company_suppliers s
"""

SUPPLIER_PAYMENT_CONDITIONS = """
CREATE OR REPLACE VIEW contract.v1_supplier_payment_conditions AS
SELECT c.id,
       c.company_id,
       c.company_supplier_id,
       c.payment_condition_type_id,
       c.currency_code,
       c.payment_terms_days,
       c.valid_from,
       c.valid_to,
       c.status
  FROM public.supplier_payment_conditions c
"""

SUPPLIER_PRODUCTS = """
CREATE OR REPLACE VIEW contract.v1_supplier_products AS
SELECT sp.id,
       sp.company_id,
       sp.company_supplier_id,
       sp.company_product_id,
       sp.company_product_presentation_id,
       sp.expected_supplier_lead_time_hours,
       sp.status
  FROM public.supplier_products sp
"""

PRICING_COVERAGE = """
CREATE OR REPLACE VIEW contract.v1_pricing_coverage AS
SELECT DISTINCT
       a.company_id,
       a.company_product_presentation_id,
       l.id AS price_list_id,
       l.currency_code
  FROM public.price_list_pricing_policy_presentations a
  JOIN public.price_list_pricing_policies p ON p.id = a.policy_id
  JOIN public.price_list_pricing_policy_terms t ON t.policy_id = p.id
  JOIN public.price_lists l ON l.id = p.price_list_id
 WHERE p.company_id = a.company_id
   AND l.company_id = a.company_id
   AND p.status = 'ACTIVE'
   AND a.valid_from <= now()
   AND (a.valid_to IS NULL OR a.valid_to > now())
   AND t.valid_from <= now()
   AND (t.valid_to IS NULL OR t.valid_to > now())
   AND l.status = 'ACTIVE'
   AND (l.valid_from IS NULL OR l.valid_from <= now())
   AND (l.valid_to IS NULL OR l.valid_to > now())
"""


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS contract")
    for statement in (COMPANY_SUPPLIERS, SUPPLIER_PAYMENT_CONDITIONS, SUPPLIER_PRODUCTS, PRICING_COVERAGE):
        op.execute(statement)
    for view in VIEWS:
        op.execute(f"COMMENT ON VIEW contract.{view} IS 'Vista de contrato de commercial-relationship (D27, spec 025).'")


def downgrade() -> None:
    for view in reversed(VIEWS):
        op.execute(f"DROP VIEW IF EXISTS contract.{view}")
