"""Tipos de grupo y grupos (FR-061 a FR-064, RC-02, RC-08)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from product_catalog_service.application import audit_events as audit
from product_catalog_service.application import lifecycle
from product_catalog_service.application.exceptions import (
    DuplicateCodeError,
    HasActiveChildrenError,
    HierarchyCycleError,
    MultipleAssignmentsExistError,
    NotFoundError,
    ParentInactiveError,
    ParentOfOtherTypeError,
    ReferenceInactiveError,
    ReferenceNotFoundError,
)
from product_catalog_service.application.normalization import (
    normalize_code,
    normalize_name,
    normalize_optional_text,
)
from product_catalog_service.application.pagination import PageResult, paginate
from product_catalog_service.application.simple_catalog import SimpleCatalogService
from product_catalog_service.domain.hierarchy import would_create_cycle
from product_catalog_service.infrastructure.hierarchy_repository import HierarchyRepository
from product_catalog_service.infrastructure.locks import lock_row
from product_catalog_service.infrastructure.models import (
    GlobalProductGroupAssignmentModel,
    GlobalProductGroupModel,
    GlobalProductGroupTypeModel,
)
from product_catalog_service.infrastructure.query_helpers import apply_common_filters

ACTIVE = lifecycle.ACTIVE


class GroupTypeService(SimpleCatalogService[GlobalProductGroupTypeModel]):
    audit_entity = "ProductGroupType"  # feature 016
    audit_suffix = "PRODUCT_GROUP_TYPE"
    model = GlobalProductGroupTypeModel
    label = "El tipo de grupo"
    code_max_length = 50
    name_max_length = 120

    def default_order(self) -> tuple:
        return (GlobalProductGroupTypeModel.display_order, GlobalProductGroupTypeModel.code)

    def before_update(self, entity: GlobalProductGroupTypeModel) -> None:
        if entity.allows_multiple:
            return

        offending = self.session.execute(
            select(GlobalProductGroupAssignmentModel.global_product_id)
            .where(
                GlobalProductGroupAssignmentModel.group_type_id == entity.id,
                GlobalProductGroupAssignmentModel.status == ACTIVE,
            )
            .group_by(GlobalProductGroupAssignmentModel.global_product_id)
            .having(func.count() > 1)
            .limit(1)
        ).first()

        if offending is not None:
            raise MultipleAssignmentsExistError(
                "Hay productos con varias asignaciones vigentes de este tipo; retírelas antes."
            )


class GroupService:
    """Grupos dentro de un tipo, con jerarquía opcional del mismo tipo."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.tree = HierarchyRepository(session, GlobalProductGroupModel, "parent_group_id")

    # ------------------------------------------------------------------ lectura

    def list(
        self,
        group_type_id: UUID,
        *,
        page: int,
        page_size: int,
        status: str | None = None,
        code: str | None = None,
        search: str | None = None,
        parent_group_id: UUID | None = None,
        root_only: bool = False,
    ) -> PageResult:
        self._type(group_type_id)
        statement = apply_common_filters(
            select(GlobalProductGroupModel).where(GlobalProductGroupModel.group_type_id == group_type_id),
            GlobalProductGroupModel,
            status=status,
            code=code,
            search=search,
        )
        if parent_group_id is not None:
            statement = statement.where(GlobalProductGroupModel.parent_group_id == parent_group_id)
        if root_only:
            statement = statement.where(GlobalProductGroupModel.parent_group_id.is_(None))
        return paginate(
            self.session,
            statement.order_by(GlobalProductGroupModel.code),
            page=page,
            page_size=page_size,
        )

    def get(self, group_id: UUID) -> GlobalProductGroupModel:
        group = self.session.get(GlobalProductGroupModel, group_id)
        if group is None:
            raise NotFoundError(f"El grupo {group_id} no existe.")
        return group

    def children(self, group_id: UUID) -> list[GlobalProductGroupModel]:
        self.get(group_id)
        return list(
            self.session.execute(
                select(GlobalProductGroupModel)
                .where(GlobalProductGroupModel.parent_group_id == group_id)
                .order_by(GlobalProductGroupModel.code)
            ).scalars()
        )

    def ancestors(self, group_id: UUID) -> list[GlobalProductGroupModel]:
        self.get(group_id)
        return self.tree.ancestors(group_id)

    # ---------------------------------------------------------------- escritura

    def create(
        self,
        group_type_id: UUID,
        *,
        code: str,
        name: str,
        description: str | None,
        parent_group_id: UUID | None,
        actor: str,
    ) -> GlobalProductGroupModel:
        group_type = lock_row(self.session, GlobalProductGroupTypeModel, group_type_id, label="El tipo de grupo")
        if group_type.status != ACTIVE:
            raise ReferenceInactiveError("El tipo de grupo está inactivo.")

        self._require_parent(group_type_id, parent_group_id)
        normalized_code = normalize_code(code, max_length=50)

        group = GlobalProductGroupModel(
            group_type_id=group_type_id,
            parent_group_id=parent_group_id,
            code=normalized_code,
            name=normalize_name(name, max_length=160),
            description=normalize_optional_text(description),
            status=ACTIVE,
        )
        lifecycle.stamp_create(group, actor)
        self.session.add(group)

        audit.track_create(self.session, group, action=audit.CREATE_PRODUCT_GROUP, entity_type="ProductGroup")
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise DuplicateCodeError(
                f"El tipo de grupo ya tiene un grupo con el código {normalized_code}."
            ) from None
        return group

    def update(
        self,
        group_id: UUID,
        *,
        version: int,
        name: str,
        description: str | None,
        parent_group_id: UUID | None,
        actor: str,
    ) -> GlobalProductGroupModel:
        group = lock_row(self.session, GlobalProductGroupModel, group_id, label="El grupo")
        lifecycle.check_version(group, version)

        if parent_group_id != group.parent_group_id:
            self._require_parent(group.group_type_id, parent_group_id)

            def parent_of(node_id: UUID) -> UUID | None:
                return parent_group_id if node_id == group.id else self.tree.parent_of(node_id)

            if would_create_cycle(group.id, parent_group_id, parent_of):
                raise HierarchyCycleError("El grupo no puede quedar bajo sí mismo ni bajo un descendiente.")

        group.name = normalize_name(name, max_length=160)
        group.description = normalize_optional_text(description)
        group.parent_group_id = parent_group_id
        lifecycle.stamp_update(group, actor)
        audit.track_update(self.session, group, action=audit.UPDATE_PRODUCT_GROUP, entity_type="ProductGroup")
        self.session.commit()
        return group

    def deactivate(self, group_id: UUID, *, version: int, actor: str) -> GlobalProductGroupModel:
        group = lock_row(self.session, GlobalProductGroupModel, group_id, label="El grupo")
        if group.status == ACTIVE and self.tree.has_active_children(group.id):
            raise HasActiveChildrenError("Primero deben inactivarse o moverse los grupos hijos activos.")
        lifecycle.deactivate(group, version, actor)
        audit.track_update(self.session, group, action=audit.DEACTIVATE_PRODUCT_GROUP, entity_type="ProductGroup")
        self.session.commit()
        return group

    def reactivate(self, group_id: UUID, *, version: int, actor: str) -> GlobalProductGroupModel:
        group = lock_row(self.session, GlobalProductGroupModel, group_id, label="El grupo")
        if self._type(group.group_type_id).status != ACTIVE:
            raise ReferenceInactiveError("El tipo de grupo está inactivo.")
        if group.parent_group_id is not None and self.get(group.parent_group_id).status != ACTIVE:
            raise ParentInactiveError("El grupo padre está inactivo.")
        lifecycle.reactivate(group, version, actor)
        audit.track_update(self.session, group, action=audit.REACTIVATE_PRODUCT_GROUP, entity_type="ProductGroup")
        self.session.commit()
        return group

    # ---------------------------------------------------------------- utilidades

    def _type(self, group_type_id: UUID) -> GlobalProductGroupTypeModel:
        group_type = self.session.get(GlobalProductGroupTypeModel, group_type_id)
        if group_type is None:
            raise NotFoundError(f"El tipo de grupo {group_type_id} no existe.")
        return group_type

    def _require_parent(self, group_type_id: UUID, parent_group_id: UUID | None) -> None:
        if parent_group_id is None:
            return
        parent = self.session.get(GlobalProductGroupModel, parent_group_id)
        if parent is None:
            raise ReferenceNotFoundError(f"El grupo padre {parent_group_id} no existe.")
        if parent.group_type_id != group_type_id:
            raise ParentOfOtherTypeError("El grupo padre debe pertenecer al mismo tipo de grupo.")
        if parent.status != ACTIVE:
            raise ReferenceInactiveError("El grupo padre está inactivo.")
