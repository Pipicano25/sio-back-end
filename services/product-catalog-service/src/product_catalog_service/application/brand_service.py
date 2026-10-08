"""Servicio de marcas globales (FR-018, FR-019).

Inactivar una marca no modifica los productos que ya la usan.
"""

from product_catalog_service.application.simple_catalog import SimpleCatalogService
from product_catalog_service.infrastructure.models import GlobalBrandModel


class BrandService(SimpleCatalogService[GlobalBrandModel]):
    audit_entity = "Brand"  # feature 016
    audit_suffix = "BRAND"
    model = GlobalBrandModel
    label = "La marca"
    code_max_length = 50
    name_max_length = 120
