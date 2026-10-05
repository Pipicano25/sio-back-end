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
