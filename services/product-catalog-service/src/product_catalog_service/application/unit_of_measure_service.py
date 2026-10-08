"""Servicio de unidades de medida (FR-013 a FR-015, FR-017)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from product_catalog_service.application.base_code_guard import ensure_base_code_available
from product_catalog_service.application.exceptions import ValidationError
from product_catalog_service.application.simple_catalog import SimpleCatalogService
from product_catalog_service.infrastructure.models import GlobalUnitOfMeasureModel


class UnitOfMeasureService(SimpleCatalogService[GlobalUnitOfMeasureModel]):
    audit_entity = "UnitOfMeasure"  # feature 016
    audit_suffix = "UNIT_OF_MEASURE"
    model = GlobalUnitOfMeasureModel
    label = "La unidad de medida"
    code_max_length = 20
    name_max_length = 80

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def prepare_fields(self, fields: dict) -> dict:
        prepared = dict(fields)
        if "symbol" in prepared:
            symbol = (prepared["symbol"] or "").strip()
            if not symbol:
                raise ValidationError("El símbolo no puede estar vacío.", field="symbol")
            if len(symbol) > 16:
                raise ValidationError("El símbolo no puede superar 16 caracteres.", field="symbol")
            prepared["symbol"] = symbol
        return prepared

    def before_create(self, code: str) -> None:
        ensure_base_code_available(self.session, code, "unit")
