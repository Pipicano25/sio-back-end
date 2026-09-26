"""Registro de los routers funcionales bajo `/api/v1` (D4)."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI
from sio_auth import SIOAuth

API_PREFIX = "/api/v1"


def include_domain_routers(app: FastAPI, auth: SIOAuth) -> None:
    """Incluye todos los routers de dominio con el prefijo de versión."""
    from product_catalog_service.api import (
        assets,
        attribute_definitions,
        brands,
        categories,
        first_use,
        group_types,
        identifiers,
        packaging_types,
        presentations,
        product_attribute_values,
        product_categories,
        product_group_assignments,
        products,
        units_of_measure,
    )

    builders = [
        units_of_measure.build_router,
        packaging_types.build_router,
        brands.build_router,
        categories.build_router,
        attribute_definitions.build_router,
        products.build_router,
        product_categories.build_router,
        product_attribute_values.build_router,
        presentations.build_router,
        identifiers.build_router,
        group_types.build_router,
        product_group_assignments.build_router,
        assets.build_router,
        first_use.build_router,
    ]

    api = APIRouter(prefix=API_PREFIX)
    for build in builders:
        api.include_router(build(auth))

    app.include_router(api)
