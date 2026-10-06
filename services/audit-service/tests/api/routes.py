"""Rutas protegidas de `contracts/rest-api.md` con su permiso (pruebas de acceso)."""

from __future__ import annotations

from uuid import UUID

COMPANY = UUID("7c1e0000-0000-4000-8000-0000000000aa")
AUDIT_ID = UUID("0b8e0000-0000-4000-8000-0000000000bb")
ENTITY = UUID("e9a00000-0000-4000-8000-0000000000cc")

ROUTES: list[tuple[str, str, str]] = [
    ("POST", "/api/v1/audit-events", "perm:audit:audit-events:create"),
    ("POST", "/api/v1/audit-events/batch", "perm:audit:audit-events:create"),
    ("GET", f"/api/v1/companies/{COMPANY}/audit-events", "perm:audit:audit-events:read"),
    ("GET", f"/api/v1/companies/{COMPANY}/audit-events/{AUDIT_ID}", "perm:audit:audit-events:read"),
    (
        "GET",
        f"/api/v1/companies/{COMPANY}/entity-history/PriceListItem/{ENTITY}",
        "perm:audit:audit-events:read",
    ),
    ("GET", "/api/v1/platform-audit-events", "perm:audit:platform-events:read"),
    ("GET", f"/api/v1/platform-audit-events/{AUDIT_ID}", "perm:audit:platform-events:read"),
    ("GET", f"/api/v1/platform-entity-history/GlobalProduct/{ENTITY}", "perm:audit:platform-events:read"),
]
