"""Router de tipos de empaque (`contracts/rest-api.md` §2)."""

from __future__ import annotations

from fastapi import APIRouter
from sio_auth import SIOAuth

from product_catalog_service.api.schemas.catalog_base import (
    PackagingTypeCreate,
    PackagingTypeResponse,
    PackagingTypeUpdate,
)
from product_catalog_service.api.simple_catalog_router import build_simple_catalog_router
from product_catalog_service.application.packaging_type_service import PackagingTypeService


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de tipos de empaque."""
    return build_simple_catalog_router(
        auth=auth,
        prefix="/packaging-types",
        resource="packaging-types",
        tag="Tipos de empaque",
        service_class=PackagingTypeService,
        create_schema=PackagingTypeCreate,
        update_schema=PackagingTypeUpdate,
        response_schema=PackagingTypeResponse,
    )
