"""Catálogo de las 55 rutas funcionales (22 de la Fase A y 33 de la Fase B) con su permiso (rest-api.md).

Lo usan las pruebas de aislamiento (T066), autenticación (T067) y OpenAPI
(T083) para recorrer **todas** las rutas sin omitir ninguna.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Route:
    method: str
    path: str
    resource: str
    action: str
    target: str  # "company", "product", "customer", "supplier", "batch", "summary", "resolve" o un recurso de la Fase B
    write: bool
    allows_inactive_company: bool = False


ROUTES: tuple[Route, ...] = (
    Route("GET", "/api/v1/companies/{company_id}/company-products", "company_products", "read", "company", False),
    Route("POST", "/api/v1/companies/{company_id}/company-products", "company_products", "create", "company", True),
    Route("POST", "/api/v1/company-products/batch-lookup", "company_products", "read", "batch", False),
    Route("GET", "/api/v1/company-products/{company_product_id}", "company_products", "read", "product", False),
    Route("PUT", "/api/v1/company-products/{company_product_id}", "company_products", "update", "product", True),
    Route("POST", "/api/v1/company-products/{company_product_id}/deactivate", "company_products", "delete", "product", True, True),
    Route("POST", "/api/v1/company-products/{company_product_id}/reactivate", "company_products", "update", "product", True),
    Route("GET", "/api/v1/companies/{company_id}/company-customers", "company_customers", "read", "company", False),
    Route("POST", "/api/v1/companies/{company_id}/company-customers", "company_customers", "create", "company", True),
    Route("GET", "/api/v1/company-customers/{company_customer_id}", "company_customers", "read", "customer", False),
    Route("PUT", "/api/v1/company-customers/{company_customer_id}", "company_customers", "update", "customer", True),
    Route("POST", "/api/v1/company-customers/{company_customer_id}/deactivate", "company_customers", "delete", "customer", True, True),
    Route("POST", "/api/v1/company-customers/{company_customer_id}/reactivate", "company_customers", "update", "customer", True),
    Route("GET", "/api/v1/companies/{company_id}/company-suppliers", "company_suppliers", "read", "company", False),
    Route("POST", "/api/v1/companies/{company_id}/company-suppliers", "company_suppliers", "create", "company", True),
    Route("GET", "/api/v1/company-suppliers/{company_supplier_id}", "company_suppliers", "read", "supplier", False),
    Route("PUT", "/api/v1/company-suppliers/{company_supplier_id}", "company_suppliers", "update", "supplier", True),
    Route("POST", "/api/v1/company-suppliers/{company_supplier_id}/deactivate", "company_suppliers", "delete", "supplier", True, True),
    Route("POST", "/api/v1/company-suppliers/{company_supplier_id}/reactivate", "company_suppliers", "update", "supplier", True),
    Route("POST", "/api/v1/company-suppliers/{company_supplier_id}/block", "company_suppliers", "delete", "supplier", True),
    Route("POST", "/api/v1/company-suppliers/{company_supplier_id}/unblock", "company_suppliers", "update", "supplier", True),
    Route("GET", "/api/v1/company-summaries", "company_products", "read", "summary", False),
)


def route_id(route: Route) -> str:
    return f"{route.method} {route.path}"


# --------------------------------------------------------------------------
# Fase B: 33 rutas de specs/010-commercial-relationship-commercial-product/contracts/rest-api.md (T070)
# --------------------------------------------------------------------------


def _resource_routes(resource: str, base: str, param: str, target: str) -> tuple[Route, ...]:
    item = f"/api/v1/{base}/{{{param}}}"
    return (
        Route("GET", f"/api/v1/companies/{{company_id}}/{base}", resource, "read", "company", False),
        Route("POST", f"/api/v1/companies/{{company_id}}/{base}", resource, "create", "company", True),
        Route("GET", item, resource, "read", target, False),
        Route("PUT", item, resource, "update", target, True),
        Route("POST", item + "/deactivate", resource, "delete", target, True, True),
        Route("POST", item + "/reactivate", resource, "update", target, True),
    )


PHASE_B_ROUTES: tuple[Route, ...] = (
    *_resource_routes("company_product_presentations", "company-product-presentations", "presentation_id", "presentation"),
    Route("POST", "/api/v1/company-product-presentations/batch-lookup", "company_product_presentations", "read", "batch", False),
    *_resource_routes("supplier_products", "supplier-products", "supplier_product_id", "supplier_product"),
    *_resource_routes("supplier_payment_conditions", "supplier-payment-conditions", "condition_id", "condition"),
    *_resource_routes("price_lists", "price-lists", "price_list_id", "price_list"),
    *_resource_routes("price_list_items", "price-list-items", "price_list_item_id", "price_item"),
    Route("POST", "/api/v1/price-list-items/{price_list_item_id}/change-price", "price_list_items", "update", "price_item", True),
    Route("POST", "/api/v1/companies/{company_id}/applicable-prices/resolve", "price_list_items", "read", "resolve", False),
)

PHASE_A_ROUTES = ROUTES
ROUTES = PHASE_A_ROUTES + PHASE_B_ROUTES

# Spec 021: rutas nuevas. Sus permisos, su aislamiento y sus errores los prueban `test_pricing_policies*.py` y
# `test_company_product_purchase_tax.py` y `test_automatic_price_applications.py`; aquí solo se contrastan con el OpenAPI y el contrato.
SPEC_021_ROUTES: tuple[Route, ...] = (
    Route("GET", "/api/v1/companies/{company_id}/price-lists/{price_list_id}/pricing-policies", "pricing_policies", "read", "company", False),
    Route("POST", "/api/v1/companies/{company_id}/price-lists/{price_list_id}/pricing-policies", "pricing_policies", "create", "company", True),
    Route("GET", "/api/v1/pricing-policies/{policy_id}", "pricing_policies", "read", "policy", False),
    Route("PUT", "/api/v1/pricing-policies/{policy_id}", "pricing_policies", "update", "policy", True),
    Route("POST", "/api/v1/pricing-policies/{policy_id}/percentage", "pricing_policies", "update", "policy", True),
    Route("POST", "/api/v1/pricing-policies/{policy_id}/presentations", "pricing_policies", "update", "policy", True),
    Route("GET", "/api/v1/pricing-policies/{policy_id}/presentations", "pricing_policies", "read", "policy", False),
    Route("POST", "/api/v1/pricing-policies/{policy_id}/presentations/remove", "pricing_policies", "update", "policy", True),
    Route("POST", "/api/v1/pricing-policies/{policy_id}/deactivate", "pricing_policies", "delete", "policy", True, True),
    Route("GET", "/api/v1/pricing-policies/{policy_id}/terms", "pricing_policies", "read", "policy", False),
    Route("PUT", "/api/v1/company-products/{company_product_id}/purchase-tax", "company_product_purchase_taxes", "update", "product", True),
    Route("POST", "/api/v1/companies/{company_id}/company-products/purchase-taxes/batch", "company_product_purchase_taxes", "update", "company", True),
    Route("POST", "/api/v1/companies/{company_id}/automatic-price-update-requests", "automatic_price_update_requests", "submit", "technical", True),
    Route("POST", "/api/v1/companies/{company_id}/pricing-policies/coverage", "pricing_policy_coverage", "read", "technical", False),
    Route("GET", "/api/v1/companies/{company_id}/automatic-price-applications", "automatic_price_applications", "read", "company", False),
    Route("GET", "/api/v1/companies/{company_id}/automatic-price-applications/{application_id}", "automatic_price_applications", "read", "company", False),
    Route("POST", "/api/v1/companies/{company_id}/automatic-price-applications/{application_id}/resolution", "automatic_price_applications", "resolve", "company", True),
)

# Spec 022 (CR-1 y CR-2): búsquedas de solo lectura. Sus permisos, su aislamiento y sus límites los prueban
# `test_company_products_search.py` y `test_presentations_by_products.py`; aquí solo se contrastan con el OpenAPI.
SPEC_022_ROUTES: tuple[Route, ...] = (
    Route("POST", "/api/v1/companies/{company_id}/company-products/search", "company_products", "read", "company", False),
    Route("POST", "/api/v1/companies/{company_id}/company-product-presentations/by-products", "company_product_presentations", "read", "company", False),
)

RESOURCES = (
    "company_products",
    "company_customers",
    "company_suppliers",
    "company_product_presentations",
    "supplier_products",
    "supplier_payment_conditions",
    "price_lists",
    "price_list_items",
)
"""Recursos de permiso del servicio (Fase A y Fase B)."""
