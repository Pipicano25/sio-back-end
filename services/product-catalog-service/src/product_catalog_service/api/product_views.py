"""Construcción de las representaciones de productos y dependientes."""

from __future__ import annotations

from product_catalog_service.api.schemas.dependents import (
    AssetResponse,
    AttributeValueResponse,
    GroupAssignmentResponse,
    IdentifierResponse,
    PresentationResponse,
)
from product_catalog_service.api.schemas.product import (
    ProductCategoryResponse,
    ProductDetailSections,
    ProductResponse,
)
from product_catalog_service.application.catalog_query_service import CatalogQueryService
from product_catalog_service.domain.completeness import (
    ProductCompleteness,
    is_presentation_eligible,
)


def presentation_view(presentation, product_status: str, completeness: ProductCompleteness) -> PresentationResponse:
    view = PresentationResponse.model_validate(presentation)
    view.eligible_for_adoption = is_presentation_eligible(presentation.status, product_status, completeness)
    return view


def attribute_value_view(value, out_of_classification_ids: set) -> AttributeValueResponse:
    view = AttributeValueResponse.model_validate(value)
    view.out_of_classification = value.id in out_of_classification_ids
    return view


def product_view(
    product,
    completeness: ProductCompleteness,
    *,
    warnings=(),
    queries: CatalogQueryService | None = None,
    expand_detail: bool = False,
) -> ProductResponse:
    detail = None

    if expand_detail and queries is not None:
        sections = queries.detail(product.id, completeness)
        out_of_classification = sections["out_of_classification_value_ids"]
        detail = ProductDetailSections(
            categories=[ProductCategoryResponse.model_validate(item) for item in sections["categories"]],
            presentations=[
                presentation_view(item, product.status, completeness) for item in sections["presentations"]
            ],
            identifiers=[IdentifierResponse.model_validate(item) for item in sections["identifiers"]],
            attribute_values=[
                attribute_value_view(item, out_of_classification) for item in sections["attribute_values"]
            ],
            group_assignments=[
                GroupAssignmentResponse.model_validate(item) for item in sections["group_assignments"]
            ],
            assets=[AssetResponse.model_validate(item) for item in sections["assets"]],
        )

    return ProductResponse.build(product, completeness, warnings, detail)
