"""Asignación de grupos a productos (FR-065, FR-066, RC-08, R-10)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from product_catalog_service.application import audit_events as audit
from product_catalog_service.application import lifecycle
from product_catalog_service.application.exceptions import (
    DuplicateAssociationError,
    GroupTypeSingleValueError,
    NotFoundError,
    ReferenceInactiveError,
    ReferenceNotFoundError,
)
from product_catalog_service.application.product_service import ensure_product_active_for_dependents
from product_catalog_service.infrastructure.locks import lock_product
from product_catalog_service.infrastructure.models import (
    GlobalProductGroupAssignmentModel,
    GlobalProductGroupModel,
    GlobalProductGroupTypeModel,
    GlobalProductModel,
)

ACTIVE = lifecycle.ACTIVE


class GroupAssignmentService:
    """Todas las escrituras bloquean primero la fila del producto (R-10)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, product_id: UUID, status: str | None = None) -> list[GlobalProductGroupAssignmentModel]:
        if self.session.get(GlobalProductModel, product_id) is None:
            raise NotFoundError(f"El producto {product_id} no existe.")
        statement = select(GlobalProductGroupAssignmentModel).where(
            GlobalProductGroupAssignmentModel.global_product_id == product_id
        )
        if status is not None:
            statement = statement.where(GlobalProductGroupAssignmentModel.status == status)
        return list(self.session.execute(statement.order_by(GlobalProductGroupAssignmentModel.created_at)).scalars())

    def assign(self, product_id: UUID, group_id: UUID, actor: str) -> tuple[GlobalProductGroupAssignmentModel, bool]:
        product = lock_product(self.session, product_id)
        ensure_product_active_for_dependents(product)
        group, group_type = self._active_group(group_id)

        assignment = self.session.execute(
            select(GlobalProductGroupAssignmentModel).where(
                GlobalProductGroupAssignmentModel.global_product_id == product_id,
                GlobalProductGroupAssignmentModel.global_product_group_id == group_id,
            )
        ).scalar_one_or_none()

        if assignment is not None and assignment.status == ACTIVE:
            raise DuplicateAssociationError("El grupo ya está asignado al producto.")

        self._check_single_value(product_id, group_type, exclude_id=assignment.id if assignment else None)

        created = assignment is None
        if created:
            assignment = GlobalProductGroupAssignmentModel(
                global_product_id=product_id,
                global_product_group_id=group_id,
                group_type_id=group.group_type_id,
                status=ACTIVE,
            )
            lifecycle.stamp_create(assignment, actor)
            self.session.add(assignment)
        else:
            assignment.status = ACTIVE
            lifecycle.stamp_update(assignment, actor)

        if created:
            audit.track_create(self.session, assignment, action=audit.CREATE_PRODUCT_GROUP_ASSIGNMENT, entity_type="ProductGroupAssignment")
        else:
            audit.track_update(self.session, assignment, action=audit.CREATE_PRODUCT_GROUP_ASSIGNMENT, entity_type="ProductGroupAssignment")
        self.session.commit()
        return assignment, created

    def deactivate(self, product_id: UUID, assignment_id: UUID, *, version: int, actor: str):
        lock_product(self.session, product_id)
        assignment = self._assignment(product_id, assignment_id)
        lifecycle.deactivate(assignment, version, actor)
        audit.track_update(self.session, assignment, action=audit.DEACTIVATE_PRODUCT_GROUP_ASSIGNMENT, entity_type="ProductGroupAssignment")
        self.session.commit()
        return assignment

    def reactivate(self, product_id: UUID, assignment_id: UUID, *, version: int, actor: str):
        product = lock_product(self.session, product_id)
        ensure_product_active_for_dependents(product)
        assignment = self._assignment(product_id, assignment_id)
        lifecycle.check_version(assignment, version)
        if assignment.status != ACTIVE:
            _, group_type = self._active_group(assignment.global_product_group_id)
            self._check_single_value(product_id, group_type, exclude_id=assignment.id)
        lifecycle.reactivate(assignment, version, actor)
        audit.track_update(self.session, assignment, action=audit.REACTIVATE_PRODUCT_GROUP_ASSIGNMENT, entity_type="ProductGroupAssignment")
        self.session.commit()
        return assignment

    # ---------------------------------------------------------------- utilidades

    def _active_group(self, group_id: UUID) -> tuple[GlobalProductGroupModel, GlobalProductGroupTypeModel]:
        group = self.session.get(GlobalProductGroupModel, group_id)
        if group is None:
            raise ReferenceNotFoundError(f"El grupo {group_id} no existe.")
        if group.status != ACTIVE:
            raise ReferenceInactiveError("El grupo está inactivo.")
        group_type = self.session.get(GlobalProductGroupTypeModel, group.group_type_id)
        if group_type.status != ACTIVE:
            raise ReferenceInactiveError("El tipo de grupo está inactivo.")
        return group, group_type

    def _check_single_value(
        self,
        product_id: UUID,
        group_type: GlobalProductGroupTypeModel,
        *,
        exclude_id: UUID | None,
    ) -> None:
        if group_type.allows_multiple:
            return

        statement = select(GlobalProductGroupAssignmentModel.id).where(
            GlobalProductGroupAssignmentModel.global_product_id == product_id,
            GlobalProductGroupAssignmentModel.group_type_id == group_type.id,
            GlobalProductGroupAssignmentModel.status == ACTIVE,
        )
        if exclude_id is not None:
            statement = statement.where(GlobalProductGroupAssignmentModel.id != exclude_id)

        if self.session.execute(statement).first() is not None:
            raise GroupTypeSingleValueError(
                f"El tipo {group_type.code} no admite varios grupos vigentes por producto."
            )

    def _assignment(self, product_id: UUID, assignment_id: UUID) -> GlobalProductGroupAssignmentModel:
        assignment = self.session.get(GlobalProductGroupAssignmentModel, assignment_id)
        if assignment is None or assignment.global_product_id != product_id:
            raise NotFoundError(f"La asignación {assignment_id} no existe en el producto.")
        return assignment
