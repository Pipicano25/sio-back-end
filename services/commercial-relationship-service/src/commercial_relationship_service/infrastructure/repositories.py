"""Repositorios SQLAlchemy de productos empresariales, clientes y proveedores."""

from __future__ import annotations

from functools import partial
from uuid import UUID

from commercial_relationship_service.application.exceptions import (
    DuplicateAdoptionError,
    DuplicateCustomerError,
    DuplicateInternalCodeError,
    DuplicateSupplierError,
)
from commercial_relationship_service.infrastructure.models import (
    CompanyCustomerModel,
    CompanyProductModel,
    CompanySupplierModel,
)
from commercial_relationship_service.infrastructure.repository_base import (
    SQLAlchemyRepositoryBase,
)


def _code_duplicate(table: str) -> dict:
    return {
        f"uq_{table}_company_id_internal_code_ci": partial(DuplicateInternalCodeError, field="internal_code"),
    }


class CompanyProductRepository(SQLAlchemyRepositoryBase[CompanyProductModel]):
    """`company_products`."""

    model = CompanyProductModel
    search_columns = ("internal_code", "reference_code", "display_name")

    duplicates = {
        "uq_company_products_company_id_global_product_id": partial(DuplicateAdoptionError, field="global_product_id"),
        **_code_duplicate("company_products"),
    }

    def adoption_exists(self, company_id: UUID, global_product_id: UUID) -> bool:
        return self.exists_where(
            CompanyProductModel.company_id == company_id,
            CompanyProductModel.global_product_id == global_product_id,
        )


class CompanyCustomerRepository(SQLAlchemyRepositoryBase[CompanyCustomerModel]):
    """`company_customers`."""

    model = CompanyCustomerModel
    search_columns = ("internal_code", "display_name")

    duplicates = {
        "uq_company_customers_company_id_person_identity_id": partial(DuplicateCustomerError, field="person_identity_id"),
        "uq_company_customers_company_id_organization_identity_id": partial(DuplicateCustomerError, field="organization_identity_id"),
        **_code_duplicate("company_customers"),
    }

    def identity_exists(
        self,
        company_id: UUID,
        *,
        person_identity_id: UUID | None,
        organization_identity_id: UUID | None,
    ) -> bool:
        if person_identity_id is not None:
            return self.exists_where(
                CompanyCustomerModel.company_id == company_id,
                CompanyCustomerModel.person_identity_id == person_identity_id,
            )

        return self.exists_where(
            CompanyCustomerModel.company_id == company_id,
            CompanyCustomerModel.organization_identity_id == organization_identity_id,
        )


class CompanySupplierRepository(SQLAlchemyRepositoryBase[CompanySupplierModel]):
    """`company_suppliers`."""

    model = CompanySupplierModel
    search_columns = ("internal_code", "display_name")

    duplicates = {
        "uq_company_suppliers_company_id_organization_identity_id": partial(DuplicateSupplierError, field="organization_identity_id"),
        **_code_duplicate("company_suppliers"),
    }

    def organization_exists(self, company_id: UUID, organization_identity_id: UUID) -> bool:
        return self.exists_where(
            CompanySupplierModel.company_id == company_id,
            CompanySupplierModel.organization_identity_id == organization_identity_id,
        )
