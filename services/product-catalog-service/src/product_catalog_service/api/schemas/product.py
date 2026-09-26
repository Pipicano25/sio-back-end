"""Esquemas de marcas, productos y clasificación (`contracts/rest-api.md` §3, §6.1, §6.2)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from product_catalog_service.api.schemas.dependents import (
    AssetResponse,
    AttributeValueResponse,
    GroupAssignmentResponse,
    IdentifierResponse,
    PresentationResponse,
)
from product_catalog_service.api.schemas.base import (
    RequestModel,
    StatusResourceResponse,
    UpdateModel,
    VersionRequest,
)
from product_catalog_service.domain.completeness import ProductCompleteness, is_eligible

FIRST_USE_FIELDS = frozenset({"first_used_at", "first_used_by", "first_use_source"})


# ------------------------------------------------------------------------ marcas


class BrandCreate(RequestModel):
    code: str = Field(max_length=100)
    name: str = Field(max_length=240)
    description: str | None = None


class BrandUpdate(UpdateModel):
    immutable_fields = frozenset({"code", "status"})

    name: str = Field(max_length=240)
    description: str | None = None


class BrandResponse(StatusResourceResponse):
    code: str
    name: str
    description: str | None


# --------------------------------------------------------------------- productos


class ProductCreate(RequestModel):
    product_type: Literal["GOOD"]
    canonical_name: str = Field(max_length=400)
    description: str | None = None
    global_brand_id: UUID | None = None
    manufacturer_organization_id: UUID | None = None
    base_unit_id: UUID


class ProductUpdate(UpdateModel):
    immutable_fields = frozenset({"product_type", "status"}) | FIRST_USE_FIELDS

    canonical_name: str = Field(max_length=400)
    description: str | None = None
    global_brand_id: UUID | None = None
    manufacturer_organization_id: UUID | None = None
    base_unit_id: UUID


class CompletenessResponse(BaseModel):
    is_complete: bool
    issues: list[str]
    missing_attribute_definition_ids: list[UUID]
    out_of_classification_value_ids: list[UUID]

    @classmethod
    def from_domain(cls, completeness: ProductCompleteness) -> "CompletenessResponse":
        return cls(
            is_complete=completeness.is_complete,
            issues=list(completeness.issues),
            missing_attribute_definition_ids=list(completeness.missing_attribute_definition_ids),
            out_of_classification_value_ids=list(completeness.out_of_classification_value_ids),
        )


class WarningResponse(BaseModel):
    code: str
    message: str
    matching_product_ids: list[UUID]


class ProductCategoryResponse(StatusResourceResponse):
    global_product_id: UUID
    global_category_id: UUID
    is_primary: bool


class ProductDetailSections(BaseModel):
    """Elementos vigentes del producto (`expand=detail`, FR-033)."""

    categories: list[ProductCategoryResponse]
    presentations: list[PresentationResponse]
    identifiers: list[IdentifierResponse]
    attribute_values: list[AttributeValueResponse]
    group_assignments: list[GroupAssignmentResponse]
    assets: list[AssetResponse]


class ProductResponse(StatusResourceResponse):
    product_type: str
    canonical_name: str
    description: str | None
    global_brand_id: UUID | None
    manufacturer_organization_id: UUID | None
    base_unit_id: UUID
    first_used_at: datetime | None
    first_use_source: str | None
    completeness: CompletenessResponse
    eligible_for_adoption: bool
    warnings: list[WarningResponse] = []
    detail: ProductDetailSections | None = None

    @classmethod
    def build(
        cls,
        product,
        completeness: ProductCompleteness,
        warnings=(),
        detail: ProductDetailSections | None = None,
    ) -> "ProductResponse":
        return cls(
            id=product.id,
            version=product.version,
            created_at=product.created_at,
            updated_at=product.updated_at,
            created_by=product.created_by,
            updated_by=product.updated_by,
            status=product.status,
            product_type=product.product_type,
            canonical_name=product.canonical_name,
            description=product.description,
            global_brand_id=product.global_brand_id,
            manufacturer_organization_id=product.manufacturer_organization_id,
            base_unit_id=product.base_unit_id,
            first_used_at=product.first_used_at,
            first_use_source=product.first_use_source,
            completeness=CompletenessResponse.from_domain(completeness),
            eligible_for_adoption=is_eligible(product.status, completeness),
            warnings=[
                WarningResponse(
                    code=warning.code,
                    message=warning.message,
                    matching_product_ids=list(warning.matching_product_ids),
                )
                for warning in warnings
            ],
            detail=detail,
        )


# ----------------------------------------------------------- clasificación


class ProductCategoryAssign(RequestModel):
    global_category_id: UUID


class ProductCategoryDeactivate(VersionRequest):
    new_primary_association_id: UUID | None = None
