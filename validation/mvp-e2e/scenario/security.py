"""Pasos de la etapa `seguridad` (Historia 4; ítem 21): aislamiento entre empresas y permisos.

Aislamiento (`contracts/e2e-scenarios.md` §3, research R-11): cada lectura o escritura la hace un usuario
**con** el permiso y **sin** membresía en la empresa consultada, para que el rechazo se deba al
aislamiento: `admin.dao` (grupo `admin`, solo en B) sobre A y `admin.sio` (solo en A) sobre
la auditoría de B. Códigos de §3 (completados en T042): `404` en todos los servicios.

Permisos (§4): S-01..S-07. Ningún caso cambia datos.
"""

from __future__ import annotations

from scenario.steps import EX7, Step

ISOLATION_CODE = 404


def _iso(step_id: str, title: str, user: str, permission: str, service: str, method: str, path: str, body=None) -> Step:
    return Step(
        step_id, title, EX7, (21,), user, permission, service, method, path, ISOLATION_CODE, body=body,
        why="El usuario tiene el permiso, pero no es miembro de la empresa: el servicio responde 404 sin revelar si el recurso existe.",
    )


ISOLATION = [
    _iso("I-01.empresa", "admin.dao consulta la empresa A", "admin.dao", "perm:operational-context:companies:read",
         "operational-context", "GET", "/companies/{empresa_a}"),
    _iso("I-01.sucursales", "admin.dao consulta las sucursales de A", "admin.dao", "perm:operational-context:branches:read",
         "operational-context", "GET", "/companies/{empresa_a}/branches"),
    _iso("I-01.usuarios", "admin.dao consulta los usuarios operativos de A", "admin.dao", "perm:operational-context:application_users:read",
         "operational-context", "GET", "/companies/{empresa_a}/application-users"),
    _iso("I-02.clientes", "admin.dao consulta los clientes de A", "admin.dao", "perm:commercial-relationship:company_customers:read",
         "commercial-relationship", "GET", "/companies/{empresa_a}/company-customers"),
    _iso("I-02.proveedores", "admin.dao consulta los proveedores de A", "admin.dao", "perm:commercial-relationship:company_suppliers:read",
         "commercial-relationship", "GET", "/companies/{empresa_a}/company-suppliers"),
    _iso("I-02.productos", "admin.dao consulta los productos de A", "admin.dao", "perm:commercial-relationship:company_products:read",
         "commercial-relationship", "GET", "/companies/{empresa_a}/company-products"),
    _iso("I-02.listas", "admin.dao consulta las listas de precios de A", "admin.dao", "perm:commercial-relationship:price_lists:read",
         "commercial-relationship", "GET", "/companies/{empresa_a}/price-lists"),
    _iso("I-03.compras", "admin.dao consulta las compras de A", "admin.dao", "perm:purchase:purchases:read",
         "purchase", "GET", "/companies/{empresa_a}/purchases"),
    _iso("I-03.compra", "admin.dao consulta la compra P1", "admin.dao", "perm:purchase:purchases:read",
         "purchase", "GET", "/companies/{empresa_a}/purchases/{compra_1}"),
    _iso("I-04.ventas", "admin.dao consulta las ventas de A", "admin.dao", "perm:sales:sales:read",
         "sales", "GET", "/companies/{empresa_a}/sales"),
    _iso("I-04.venta", "admin.dao consulta la venta V2", "admin.dao", "perm:sales:sales:read",
         "sales", "GET", "/companies/{empresa_a}/sales/{venta_2}"),
    _iso("I-05.saldos", "admin.dao consulta los saldos de A1", "admin.dao", "perm:inventory:balances:read",
         "inventory", "GET", "/companies/{empresa_a}/branches/{sucursal_a1}/balances"),
    _iso("I-05.kardex", "admin.dao consulta el kardex del producto A en A1", "admin.dao", "perm:inventory:movements:read",
         "inventory", "GET", "/companies/{empresa_a}/branches/{sucursal_a1}/kardex/{producto_empresa_a}"),
    _iso("I-05.valoracion", "admin.dao consulta la valoración de A1", "admin.dao", "perm:inventory:valuation:read",
         "inventory", "GET", "/companies/{empresa_a}/branches/{sucursal_a1}/valuation"),
    _iso("I-05.ajuste", "admin.dao intenta un ajuste en A1", "admin.dao", "perm:inventory:adjustments:create",
         "inventory", "POST", "/companies/{empresa_a}/inventory-adjustments",
         body={
             "adjustment_key": "{clave_ajuste}",
             "branch_id": "{sucursal_a1}",
             "company_product_id": "{producto_empresa_a}",
             "adjustment_type": "NEGATIVE",
             "quantity": "1",
             "reason": "Intento de ajuste ajeno (validación MVP {run}, dato ficticio)",
         }),
    _iso("I-06.eventos", "admin.sio consulta los eventos de auditoría de B", "admin.sio", "perm:audit:audit-events:read",
         "audit", "GET", "/companies/{empresa_b}/audit-events"),
    _iso("I-06.historial", "admin.sio consulta el historial de la empresa B", "admin.sio", "perm:audit:audit-events:read",
         "audit", "GET", "/companies/{empresa_b}/entity-history/Company/{empresa_b}"),
]

PURCHASE_BODY = {
    "branch_id": "{sucursal_a1}",
    "company_supplier_id": "{proveedor}",
    "operation_date": "{fecha_negocio}",
    "lines": [{"company_product_id": "{producto_empresa_a}", "quantity": "1", "unit_cost": "1000"}],
}
SALE_BODY = {"branch_id": "{sucursal_a1}", "company_customer_id": "{cliente}", "lines": [{"company_product_id": "{producto_empresa_a}", "quantity": "1"}]}


def _perm(step_id: str, title: str, user: str, permission: str, service: str, method: str, path: str, expect: int, body=None, idempotent=False) -> Step:
    return Step(step_id, title, EX7, (21,), user, permission, service, method, path, expect, body=body, idempotent=idempotent)


PERMISSIONS = [
    # Los rechazos se observan entre grupos (superadmin, admin y el operario de las tres áreas). Todos son POST que el servicio rechaza antes de leer el cuerpo: ningún caso cambia datos.
    _perm("S-01", "operario.dao (operario) intenta crear una empresa", "operario.dao", "perm:operational-context:companies:create",
          "operational-context", "POST", "/companies", 403, {}),
    _perm("S-02", "operario.dao (operario) intenta crear una categoría del catálogo global", "operario.dao",
          "perm:product-catalog:categories:create", "product-catalog", "POST", "/categories", 403, {}),
    _perm("S-03", "admin.dao (Admin) intenta crear una empresa", "admin.dao",
          "perm:operational-context:platform:administer", "operational-context", "POST", "/companies", 403, {}),
    _perm("S-04.crear", "La cuenta de servicio sales-service intenta registrar una venta", "service-account-sales-service",
          "perm:sales:sales:create", "sales", "POST", "/companies/{empresa_a}/sales", 403, SALE_BODY),
    _perm("S-04.confirmar", "La cuenta de servicio sales-service intenta confirmar la venta V4", "service-account-sales-service",
          "perm:sales:sales:update", "sales", "POST", "/companies/{empresa_a}/sales/{venta_4}/confirmation", 403,
          {"version": "{venta_4_version}"}, idempotent=True),
    _perm("S-05.crear", "La cuenta de servicio purchase-service intenta registrar una compra", "service-account-purchase-service",
          "perm:purchase:purchases:create", "purchase", "POST", "/companies/{empresa_a}/purchases", 403, PURCHASE_BODY),
    _perm("S-05.confirmar", "La cuenta de servicio purchase-service intenta confirmar la compra P1", "service-account-purchase-service",
          "perm:purchase:purchases:update", "purchase", "POST", "/companies/{empresa_a}/purchases/{compra_1}/confirmation", 403,
          {"version": "{compra_1_version}"}, idempotent=True),
]

# S-06: una lectura y una escritura en cada uno de los 10 servicios, sin token y con token inválido.
UNAUTHENTICATED_ROUTES = {
    "party-identity": (("GET", "/person-identities"), ("POST", "/person-identities")),
    "geography": (("GET", "/global-countries"), ("POST", "/global-countries")),
    "product-catalog": (("GET", "/products"), ("POST", "/categories")),
    "operational-context": (("GET", "/companies"), ("POST", "/companies")),
    "payment-reference": (("GET", "/global-payment-methods"), ("POST", "/global-payment-methods")),
    "commercial-relationship": (("GET", "/companies/{empresa_a}/company-products"), ("POST", "/companies/{empresa_a}/company-customers")),
    "purchase": (("GET", "/companies/{empresa_a}/purchases"), ("POST", "/companies/{empresa_a}/purchases")),
    "sales": (("GET", "/companies/{empresa_a}/sales"), ("POST", "/companies/{empresa_a}/sales")),
    "inventory": (("GET", "/companies/{empresa_a}/branches/{sucursal_a1}/balances"), ("POST", "/companies/{empresa_a}/inventory-adjustments")),
    "audit": (("GET", "/companies/{empresa_a}/audit-events"), ("POST", "/audit-events")),
}
UNAUTHENTICATED = [
    Step(
        f"S-06.{identity}.{service}.{'lectura' if method == 'GET' else 'escritura'}",
        f"{'Sin token' if identity == 'sin-token' else 'Token inválido'}: {method} en {service}", EX7, (21,), identity, "—",
        service, method, path, 401, body={} if method == "POST" else None,
    )
    for identity in ("sin-token", "token-invalido")
    for service, routes in UNAUTHENTICATED_ROUTES.items()
    for method, path in routes
]

SECURITY_STEPS = ISOLATION + PERMISSIONS + UNAUTHENTICATED
