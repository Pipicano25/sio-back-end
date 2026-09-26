"""Servicio de tipos de empaque (FR-016, FR-017)."""

from __future__ import annotations

from product_catalog_service.application.base_code_guard import ensure_base_code_available
from product_catalog_service.application.simple_catalog import SimpleCatalogService
from product_catalog_service.infrastructure.models import GlobalPackagingTypeModel


class PackagingTypeService(SimpleCatalogService[GlobalPackagingTypeModel]):
    model = GlobalPackagingTypeModel
    label = "El tipo de empaque"
    code_max_length = 50
    name_max_length = 120

    def before_create(self, code: str) -> None:
        ensure_base_code_available(self.session, code, "packaging")
