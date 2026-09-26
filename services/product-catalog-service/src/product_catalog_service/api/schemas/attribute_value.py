"""Esquema de registro de valores de atributo (`contracts/rest-api.md` §6.3)."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from product_catalog_service.api.schemas.base import RequestModel


class AttributeValuePut(RequestModel):
    """Exactamente uno de los datos tipados; `version` solo al reemplazar."""

    option_id: UUID | None = None
    text_value: str | None = None
    integer_value: int | None = None
    decimal_value: Decimal | None = None
    boolean_value: bool | None = None
    date_value: date | None = None
    version: int | None = Field(default=None, ge=1)
