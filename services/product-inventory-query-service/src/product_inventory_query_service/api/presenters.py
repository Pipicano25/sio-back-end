"""Traducción de las vistas de aplicación a los esquemas de respuesta (contrato §3 y §4).

Los bloques no visibles no se asignan, así que `exclude_unset` los omite (FR-022-14). Las cantidades se
formatean con 4 decimales (FR-022-41).
"""

from __future__ import annotations

from product_inventory_query_service.api.schemas.inventory_overview import InventoryOverview
from product_inventory_query_service.api.schemas.low_stock import LowStockPair
from product_inventory_query_service.api.schemas.pagination import CursorPage
from product_inventory_query_service.api.schemas.product_overview import (
    BranchStockOut,
    CategoryOut,
    EquivalenceOut,
    IdentifierOut,
    PresentationOut,
    PriceOut,
    ProductOverview,
    ProductPresentationOut,
    ReferenceOut,
    StockOut,
)
from product_inventory_query_service.application.enrichment import PresentationView, ProductView
from product_inventory_query_service.application.listing import ListingResult
from product_inventory_query_service.application.low_stock_service import PairView
from product_inventory_query_service.application.ports import Reference
from product_inventory_query_service.domain.stock import fmt


def reference(value: Reference | None) -> ReferenceOut | None:
    return None if value is None else ReferenceOut(id=value.id, code=value.code, name=value.name)


def identity(view: ProductView) -> dict:
    product, summary = view.product, view.summary
    return {
        "company_product_id": product.id,
        "global_product_id": product.global_product_id,
        "display_name": product.display_name,
        "canonical_name": summary.canonical_name if summary else None,
        "internal_code": product.internal_code,
        "reference_code": product.reference_code,
        "status": product.status,
        "global_status": summary.status if summary else None,
        "product_type": summary.product_type if summary else None,
        "brand": reference(summary.brand) if summary else None,
        "categories": [CategoryOut(id=c.id, code=c.code, name=c.name, is_primary=c.is_primary)
                       for c in (summary.categories if summary else ())],
        "identifiers": [IdentifierOut(type=i.type, value=i.value, is_primary=i.is_primary,
                                      global_product_presentation_id=i.global_product_presentation_id)
                        for i in (summary.identifiers if summary else ())],
        "base_unit": reference(summary.base_unit) if summary else None,
        "has_image": bool(summary and summary.has_image),
        "asset_id": summary.image_asset_id if summary and summary.has_image else None,
        "image_url": summary.image_url if summary and summary.has_image else None,
    }


def presentation_fields(view: PresentationView) -> dict:
    company, info = view.company, view.info
    return {
        "company_product_presentation_id": company.id,
        "global_product_presentation_id": company.global_product_presentation_id,
        "code": info.code if info else None,
        "name": info.name if info else None,
        "sku": company.sku,
        "internal_code": company.internal_code,
        "status": company.status,
        "is_sellable": company.is_sellable,
        "base_quantity_factor": fmt(info.base_quantity) if info and info.base_quantity is not None else None,
    }


def stock(view: ProductView, *, with_minimums: bool) -> StockOut | None:
    if view.stock is None:
        return None
    branches = []
    for branch in view.stock.branches:
        fields = {"branch_id": branch.branch_id, "base_quantity": fmt(branch.base_quantity),
                  "balance_state": branch.balance_state}
        if with_minimums:
            fields["minimum_stock"] = fmt(branch.minimum_stock) if branch.minimum_stock is not None else None
            fields["minimum_state"] = branch.minimum_state
        branches.append(BranchStockOut(**fields))
    return StockOut(
        base_unit=reference(view.summary.base_unit) if view.summary else None,
        total_base_quantity=fmt(view.stock.total),
        branches=branches,
        equivalences=[
            EquivalenceOut(company_product_presentation_id=e.company_product_presentation_id,
                           whole_units=e.whole_units, remainder_base_quantity=fmt(e.remainder_base_quantity))
            for e in view.stock.equivalences
        ],
    )


def product_overview(view: ProductView, *, with_prices: bool, with_minimums: bool) -> ProductOverview:
    presentations = []
    for item in view.presentations:
        fields = presentation_fields(item)
        if with_prices:
            price = item.price
            fields["price"] = PriceOut(price_list_id=price.price_list_id, price_list_item_id=price.price_list_item_id,
                                       unit_price=price.unit_price, currency_code=price.currency_code,
                                       resolution=price.resolution)
        presentations.append(ProductPresentationOut(**fields))
    fields = identity(view) | {"presentations": presentations}
    if view.stock is not None:
        fields["stock"] = stock(view, with_minimums=with_minimums)
    return ProductOverview(**fields)


def inventory_overview(view: ProductView, *, with_minimums: bool) -> InventoryOverview:
    fields = identity(view) | {"presentations": [PresentationOut(**presentation_fields(p)) for p in view.presentations]}
    if view.stock is not None:
        fields["stock"] = stock(view, with_minimums=with_minimums)
    return InventoryOverview(**fields)


def low_stock_pair(view: PairView) -> LowStockPair:
    summary = view.summary
    return LowStockPair(
        company_product_id=view.product.id,
        display_name=view.product.display_name,
        internal_code=view.product.internal_code,
        base_unit=reference(summary.base_unit) if summary else None,
        branch_id=view.pair.branch_id,
        base_quantity=fmt(view.pair.base_quantity),
        minimum_stock=fmt(view.pair.minimum_stock),
        shortfall=fmt(view.pair.shortfall),
        policy_status="ACTIVE",
        has_image=bool(summary and summary.has_image),
        asset_id=summary.image_asset_id if summary and summary.has_image else None,
        image_url=summary.image_url if summary and summary.has_image else None,
    )


def cursor_page(result: ListingResult, items: list) -> CursorPage:
    page = result.page
    return CursorPage(
        items=items,
        page_size=result.listing.spec.page_size,
        has_next=page.has_next,
        next_cursor=result.next_cursor,
        pagination_reset=result.reset_reason is not None,
        pagination_reset_reason=result.reset_reason,
        partial=page.partial,
        partial_reason=page.partial_reason,
        sort_applied=result.sort_applied,
        resolved_at=result.resolved_at,
    )
