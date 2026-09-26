"""Representaciones de lectura de los elementos dependientes del producto.

Las usan el detalle del producto (`expand=detail`) y los routers de US5 a US9.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from product_catalog_service.api.schemas.base import ResourceResponse, StatusResourceResponse


class PresentationResponse(StatusResourceResponse):
    global_product_id: UUID
    code: str
    name: str
    packaging_type_id: UUID | None
    base_quantity: Decimal
    content_quantity: Decimal | None
    content_unit_id: UUID | None
    display_order: int
    is_base: bool
    first_used_at: datetime | None
    first_use_source: str | None
    eligible_for_adoption: bool = False


class IdentifierResponse(StatusResourceResponse):
    global_product_id: UUID
    global_product_presentation_id: UUID | None
    identifier_type: str
    value: str
    canonical_value: str
    is_primary: bool


class AttributeValueResponse(ResourceResponse):
    global_product_id: UUID
    attribute_definition_id: UUID
    option_id: UUID | None
    text_value: str | None
    integer_value: int | None
    decimal_value: Decimal | None
    boolean_value: bool | None
    date_value: date | None
    out_of_classification: bool = False


class GroupAssignmentResponse(StatusResourceResponse):
    global_product_id: UUID
    global_product_group_id: UUID
    group_type_id: UUID


class AssetResponse(StatusResourceResponse):
    global_product_id: UUID
    asset_type: str
    file_name: str
    storage_uri: str
    mime_type: str | None
    is_primary: bool
