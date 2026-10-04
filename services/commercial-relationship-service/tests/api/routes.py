"""Catálogo de las 22 rutas funcionales del contrato con su permiso (rest-api.md).

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
    target: str  # "company" (empresa en la ruta), "product", "customer", "supplier", "batch" o "summary"
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
