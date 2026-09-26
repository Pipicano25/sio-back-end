"""Router de marcas (`contracts/rest-api.md` §3)."""

from fastapi import APIRouter
from sio_auth import SIOAuth

from product_catalog_service.api.schemas.product import BrandCreate, BrandResponse, BrandUpdate
from product_catalog_service.api.simple_catalog_router import build_simple_catalog_router
from product_catalog_service.application.brand_service import BrandService


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de marcas."""
    return build_simple_catalog_router(
        auth=auth,
        prefix="/brands",
        resource="brands",
        tag="Marcas",
        service_class=BrandService,
        create_schema=BrandCreate,
        update_schema=BrandUpdate,
        response_schema=BrandResponse,
    )
