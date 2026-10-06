"""Rutas protegidas de `contracts/rest-api.md` con su permiso (pruebas de acceso)."""

from __future__ import annotations

from uuid import UUID

COMPANY = UUID("7c1e0000-0000-4000-8000-0000000000aa")
BRANCH = UUID("b2a00000-0000-4000-8000-0000000000bb")
PRODUCT = UUID("e9a00000-0000-4000-8000-0000000000cc")
OPERATION = UUID("0b8e0000-0000-4000-8000-0000000000dd")
KEY = UUID("6f1c0000-0000-4000-8000-0000000000ee")

ROUTES: list[tuple[str, str, str]] = [
    ("POST", "/api/v1/inventory-entries", "perm:inventory:entries:create"),
    ("POST", "/api/v1/inventory-outputs", "perm:inventory:outputs:create"),
    ("POST", f"/api/v1/inventory-entries/{OPERATION}/reversal", "perm:inventory:entries:create"),
    ("POST", f"/api/v1/inventory-outputs/{OPERATION}/reversal", "perm:inventory:outputs:create"),
    ("GET", f"/api/v1/companies/{COMPANY}/branches/{BRANCH}/balances", "perm:inventory:balances:read"),
    ("GET", f"/api/v1/companies/{COMPANY}/branches/{BRANCH}/balances/{PRODUCT}", "perm:inventory:balances:read"),
    ("POST", f"/api/v1/companies/{COMPANY}/branches/{BRANCH}/balances/lookup", "perm:inventory:balances:read"),
    ("GET", f"/api/v1/companies/{COMPANY}/branches/{BRANCH}/kardex/{PRODUCT}", "perm:inventory:movements:read"),
    ("GET", f"/api/v1/companies/{COMPANY}/inventory-operations/{OPERATION}", "perm:inventory:movements:read"),
    ("GET", f"/api/v1/companies/{COMPANY}/inventory-operations/by-key/{KEY}", "perm:inventory:movements:read"),
]
