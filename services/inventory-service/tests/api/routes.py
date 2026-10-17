"""Rutas protegidas de `contracts/rest-api.md` (012 y 013) con su permiso (pruebas de acceso)."""

from __future__ import annotations

from uuid import UUID

COMPANY = UUID("7c1e0000-0000-4000-8000-0000000000aa")
BRANCH = UUID("b2a00000-0000-4000-8000-0000000000bb")
PRODUCT = UUID("e9a00000-0000-4000-8000-0000000000cc")
OPERATION = UUID("0b8e0000-0000-4000-8000-0000000000dd")
KEY = UUID("6f1c0000-0000-4000-8000-0000000000ee")
ADJUSTMENT = UUID("a0a00000-0000-4000-8000-0000000000a1")
COUNT = UUID("c0c00000-0000-4000-8000-0000000000c1")
POLICY = UUID("90100000-0000-4000-8000-0000000000f1")
MOVEMENT = UUID("3e3e0000-0000-4000-8000-0000000000e1")

_C = f"/api/v1/companies/{COMPANY}"

ROUTES: list[tuple[str, str, str]] = [
    # Fase A (012), rutas 1–10.
    ("POST", "/api/v1/inventory-entries", "perm:inventory:entries:create"),
    ("POST", "/api/v1/inventory-outputs", "perm:inventory:outputs:create"),
    ("POST", f"/api/v1/inventory-entries/{OPERATION}/reversal", "perm:inventory:entries:create"),
    ("POST", f"/api/v1/inventory-outputs/{OPERATION}/reversal", "perm:inventory:outputs:create"),
    ("GET", f"{_C}/branches/{BRANCH}/balances", "perm:inventory:balances:read"),
    ("GET", f"{_C}/branches/{BRANCH}/balances/{PRODUCT}", "perm:inventory:balances:read"),
    ("POST", f"{_C}/branches/{BRANCH}/balances/lookup", "perm:inventory:balances:read"),
    ("GET", f"{_C}/branches/{BRANCH}/kardex/{PRODUCT}", "perm:inventory:movements:read"),
    ("GET", f"{_C}/inventory-operations/{OPERATION}", "perm:inventory:movements:read"),
    ("GET", f"{_C}/inventory-operations/by-key/{KEY}", "perm:inventory:movements:read"),
    # Fase B (013), rutas 11–31.
    ("POST", f"{_C}/inventory-adjustments", "perm:inventory:adjustments:create"),
    ("GET", f"{_C}/inventory-adjustments", "perm:inventory:adjustments:read"),
    ("GET", f"{_C}/inventory-adjustments/{ADJUSTMENT}", "perm:inventory:adjustments:read"),
    ("POST", f"{_C}/inventory-counts", "perm:inventory:counts:create"),
    ("POST", f"{_C}/inventory-counts/{COUNT}/start", "perm:inventory:counts:create"),
    ("PUT", f"{_C}/inventory-counts/{COUNT}/details/{PRODUCT}", "perm:inventory:counts:create"),
    ("POST", f"{_C}/inventory-counts/{COUNT}/complete", "perm:inventory:counts:create"),
    ("POST", f"{_C}/inventory-counts/{COUNT}/cancel", "perm:inventory:counts:create"),
    ("GET", f"{_C}/inventory-counts", "perm:inventory:counts:read"),
    ("GET", f"{_C}/inventory-counts/{COUNT}", "perm:inventory:counts:read"),
    ("GET", f"{_C}/inventory-policy", "perm:inventory:company-policies:read"),
    ("POST", f"{_C}/inventory-policy", "perm:inventory:company-policies:update"),
    ("PUT", f"{_C}/inventory-policy", "perm:inventory:company-policies:update"),
    ("GET", f"{_C}/inventory-policies", "perm:inventory:product-policies:read"),
    ("GET", f"{_C}/inventory-policies/{POLICY}", "perm:inventory:product-policies:read"),
    ("POST", f"{_C}/inventory-policies", "perm:inventory:product-policies:update"),
    ("PUT", f"{_C}/inventory-policies/{POLICY}", "perm:inventory:product-policies:update"),
    ("POST", f"{_C}/inventory-policies/{POLICY}/deactivate", "perm:inventory:product-policies:update"),
    ("GET", f"{_C}/branches/{BRANCH}/valuation", "perm:inventory:valuation:read"),
    ("GET", f"{_C}/branches/{BRANCH}/valuation/{PRODUCT}/layers", "perm:inventory:valuation:read"),
    ("GET", f"{_C}/inventory-movements/{MOVEMENT}/cost-consumptions", "perm:inventory:valuation:read"),
    # Spec 022: INV-1, INV-2 e INV-3 (INV-2 e INV-3 exigen además `product-policies:read`; se rechaza el primero).
    ("POST", f"{_C}/branches/{BRANCH}/inventory-policies/lookup", "perm:inventory:product-policies:read"),
    ("POST", f"{_C}/inventory-product-sets", "perm:inventory:balances:read"),
    ("POST", f"{_C}/inventory-summary", "perm:inventory:balances:read"),
]

HUMAN_ONLY: set[tuple[str, str]] = {
    (method, path)
    for method, path, permission in ROUTES
    if permission.endswith((":adjustments:create", ":counts:create", ":company-policies:update", ":product-policies:update"))
}
"""Rutas 11, 14–18, 22–23 y 26–28: una cuenta de servicio recibe `403` aunque tenga el permiso."""


def declared_methods(path: str) -> set[str]:
    """Métodos publicados para una ruta (los demás responden `405`)."""
    return {method for method, candidate, _ in ROUTES if candidate == path}
