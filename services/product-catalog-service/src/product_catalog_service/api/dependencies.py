"""Dependencias FastAPI compartidas por los routers."""

from fastapi import Request

from product_catalog_service.application.ports import ManufacturerDirectory


def get_manufacturer_directory(request: Request) -> ManufacturerDirectory:
    """Adaptador de Party Identity para la solicitud actual (sustituible en pruebas)."""
    return request.app.state.manufacturer_directory_factory(request)
