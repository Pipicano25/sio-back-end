"""Cobertura del catálogo de auditoría frente al OpenAPI (feature 016; FR-003; T034).

`specs/016-existing-services-audit/contracts/audit-actions.md`, sección Commercial Relationship:
cada escritura tiene exactamente una acción (35) y las 3 lecturas por `POST` quedan excluidas.
"""

from __future__ import annotations

from commercial_relationship_service.application import audit_events as audit

C = "/api/v1/companies/{company_id}"
CATALOG = {
    ("POST", f"{C}/company-products"): ("ADOPT_COMPANY_PRODUCT", "CompanyProduct"),
    ("PUT", "/api/v1/company-products/{company_product_id}"): ("UPDATE_COMPANY_PRODUCT", "CompanyProduct"),
    ("POST", "/api/v1/company-products/{company_product_id}/deactivate"): ("DEACTIVATE_COMPANY_PRODUCT", "CompanyProduct"),
    ("POST", "/api/v1/company-products/{company_product_id}/reactivate"): ("REACTIVATE_COMPANY_PRODUCT", "CompanyProduct"),
    ("POST", f"{C}/company-customers"): ("CREATE_COMPANY_CUSTOMER", "CompanyCustomer"),
    ("PUT", "/api/v1/company-customers/{company_customer_id}"): ("UPDATE_COMPANY_CUSTOMER", "CompanyCustomer"),
    ("POST", "/api/v1/company-customers/{company_customer_id}/deactivate"): ("DEACTIVATE_COMPANY_CUSTOMER", "CompanyCustomer"),
    ("POST", "/api/v1/company-customers/{company_customer_id}/reactivate"): ("REACTIVATE_COMPANY_CUSTOMER", "CompanyCustomer"),
    ("POST", f"{C}/company-suppliers"): ("CREATE_COMPANY_SUPPLIER", "CompanySupplier"),
    ("PUT", "/api/v1/company-suppliers/{company_supplier_id}"): ("UPDATE_COMPANY_SUPPLIER", "CompanySupplier"),
    ("POST", "/api/v1/company-suppliers/{company_supplier_id}/deactivate"): ("DEACTIVATE_COMPANY_SUPPLIER", "CompanySupplier"),
    ("POST", "/api/v1/company-suppliers/{company_supplier_id}/reactivate"): ("REACTIVATE_COMPANY_SUPPLIER", "CompanySupplier"),
    ("POST", "/api/v1/company-suppliers/{company_supplier_id}/block"): ("BLOCK_COMPANY_SUPPLIER", "CompanySupplier"),
    ("POST", "/api/v1/company-suppliers/{company_supplier_id}/unblock"): ("UNBLOCK_COMPANY_SUPPLIER", "CompanySupplier"),
    ("POST", f"{C}/company-product-presentations"): ("CREATE_COMPANY_PRODUCT_PRESENTATION", "CompanyProductPresentation"),
    ("PUT", "/api/v1/company-product-presentations/{presentation_id}"): ("UPDATE_COMPANY_PRODUCT_PRESENTATION", "CompanyProductPresentation"),
    ("POST", "/api/v1/company-product-presentations/{presentation_id}/deactivate"): ("DEACTIVATE_COMPANY_PRODUCT_PRESENTATION", "CompanyProductPresentation"),
    ("POST", "/api/v1/company-product-presentations/{presentation_id}/reactivate"): ("REACTIVATE_COMPANY_PRODUCT_PRESENTATION", "CompanyProductPresentation"),
    ("POST", f"{C}/supplier-products"): ("CREATE_SUPPLIER_PRODUCT", "SupplierProduct"),
    ("PUT", "/api/v1/supplier-products/{supplier_product_id}"): ("UPDATE_SUPPLIER_PRODUCT", "SupplierProduct"),
    ("POST", "/api/v1/supplier-products/{supplier_product_id}/deactivate"): ("DEACTIVATE_SUPPLIER_PRODUCT", "SupplierProduct"),
    ("POST", "/api/v1/supplier-products/{supplier_product_id}/reactivate"): ("REACTIVATE_SUPPLIER_PRODUCT", "SupplierProduct"),
    ("POST", f"{C}/supplier-payment-conditions"): ("CREATE_SUPPLIER_PAYMENT_CONDITION", "SupplierPaymentCondition"),
    ("PUT", "/api/v1/supplier-payment-conditions/{condition_id}"): ("UPDATE_SUPPLIER_PAYMENT_CONDITION", "SupplierPaymentCondition"),
    ("POST", "/api/v1/supplier-payment-conditions/{condition_id}/deactivate"): ("DEACTIVATE_SUPPLIER_PAYMENT_CONDITION", "SupplierPaymentCondition"),
    ("POST", "/api/v1/supplier-payment-conditions/{condition_id}/reactivate"): ("REACTIVATE_SUPPLIER_PAYMENT_CONDITION", "SupplierPaymentCondition"),
    ("POST", f"{C}/price-lists"): ("CREATE_PRICE_LIST", "PriceList"),
    ("PUT", "/api/v1/price-lists/{price_list_id}"): ("UPDATE_PRICE_LIST", "PriceList"),
    ("POST", "/api/v1/price-lists/{price_list_id}/deactivate"): ("DEACTIVATE_PRICE_LIST", "PriceList"),
    ("POST", "/api/v1/price-lists/{price_list_id}/reactivate"): ("REACTIVATE_PRICE_LIST", "PriceList"),
    ("POST", f"{C}/price-list-items"): ("CREATE_PRICE_LIST_ITEM", "PriceListItem"),
    ("PUT", "/api/v1/price-list-items/{price_list_item_id}"): ("UPDATE_PRICE_LIST_ITEM", "PriceListItem"),
    ("POST", "/api/v1/price-list-items/{price_list_item_id}/change-price"): ("CHANGE_PRICE_LIST_ITEM_PRICE", "PriceListItem"),
    ("POST", "/api/v1/price-list-items/{price_list_item_id}/deactivate"): ("DEACTIVATE_PRICE_LIST_ITEM", "PriceListItem"),
    ("POST", "/api/v1/price-list-items/{price_list_item_id}/reactivate"): ("REACTIVATE_PRICE_LIST_ITEM", "PriceListItem"),
    # Spec 021: tasa de impuesto de compra del producto
    ("PUT", "/api/v1/company-products/{company_product_id}/purchase-tax"): ("UPDATE_COMPANY_PRODUCT_PURCHASE_TAX", "CompanyProduct"),
    ("POST", f"{C}/company-products/purchase-taxes/batch"): ("UPDATE_COMPANY_PRODUCT_PURCHASE_TAX", "CompanyProduct"),
    # Spec 021: solicitudes técnicas de Purchase
    ("POST", f"{C}/automatic-price-update-requests"): ("RECEIVE_AUTOMATIC_PRICE_REQUEST", "AutomaticPriceUpdateRequest"),
    ("POST", f"{C}/automatic-price-applications/{{application_id}}/resolution"): ("RESOLVE_AUTOMATIC_PRICE", "AutomaticPriceApplication"),
    # Spec 021: políticas de precios
    ("POST", f"{C}/price-lists/{{price_list_id}}/pricing-policies"): ("CREATE_PRICING_POLICY", "PricingPolicy"),
    ("PUT", "/api/v1/pricing-policies/{policy_id}"): ("UPDATE_PRICING_POLICY", "PricingPolicy"),
    ("POST", "/api/v1/pricing-policies/{policy_id}/percentage"): ("CHANGE_PRICING_POLICY_PERCENTAGE", "PricingPolicy"),
    ("POST", "/api/v1/pricing-policies/{policy_id}/presentations"): ("ASSIGN_PRICING_POLICY_PRESENTATION", "PricingPolicy"),
    ("POST", "/api/v1/pricing-policies/{policy_id}/presentations/remove"): ("UNASSIGN_PRICING_POLICY_PRESENTATION", "PricingPolicy"),
    ("POST", "/api/v1/pricing-policies/{policy_id}/deactivate"): ("DEACTIVATE_PRICING_POLICY", "PricingPolicy"),
}
READS_BY_POST = {
    ("POST", "/api/v1/company-products/batch-lookup"),
    ("POST", "/api/v1/company-product-presentations/batch-lookup"),
    ("POST", f"{C}/applicable-prices/resolve"),
    ("POST", f"{C}/pricing-policies/coverage"),  # spec 021 (FR-021-35): consulta de cobertura, sin efectos
}


def _writes(app) -> set[tuple[str, str]]:
    return {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if method in {"post", "put", "patch", "delete"}
    }


def test_every_write_has_exactly_one_action(app) -> None:
    writes = _writes(app)
    assert READS_BY_POST <= writes
    assert writes - READS_BY_POST == set(CATALOG)
    assert len(CATALOG) == 45  # 35 de la 016 + 10 de la spec 021


def test_catalog_matches_the_service_constants() -> None:
    assert {action for action, _ in CATALOG.values()} == set(audit.ACTIONS)
    assert {entity for _, entity in CATALOG.values()} == set(audit.ENTITY_TYPES)
