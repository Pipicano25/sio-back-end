"""Identificadores del producto (FR-055 a FR-060, DS-05, DS-17, R-13; IUM: spec 018)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from product_catalog_service.application import audit_events as audit
from product_catalog_service.application import lifecycle
from product_catalog_service.application.exceptions import (
    BarcodeIsGtinError,
    IdentifierCollisionError,
    InvalidCheckDigitError,
    InvalidGtinFormatError,
    InvalidIumFormatError,
    IumRequiresPresentationError,
    NotFoundError,
    PresentationOfOtherProductError,
    ReferenceInactiveError,
)
from product_catalog_service.application.normalization import normalize_identifier_value
from product_catalog_service.application.product_service import ensure_product_active_for_dependents
from product_catalog_service.domain.gtin import (
    GTIN_FAMILY,
    canonical_value,
    has_gtin_shape,
    has_valid_check_digit,
    is_valid_gtin_format,
)
from product_catalog_service.domain.ium import IUM_TYPE, is_valid_ium
from product_catalog_service.infrastructure.locks import lock_product
from product_catalog_service.infrastructure.models import (
    GlobalProductIdentifierModel,
    GlobalProductModel,
    GlobalProductPresentationModel,
)

ACTIVE = lifecycle.ACTIVE


class IdentifierService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, product_id: UUID, status: str | None = None) -> list[GlobalProductIdentifierModel]:
        if self.session.get(GlobalProductModel, product_id) is None:
            raise NotFoundError(f"El producto {product_id} no existe.")
        statement = select(GlobalProductIdentifierModel).where(
            GlobalProductIdentifierModel.global_product_id == product_id
        )
        if status is not None:
            statement = statement.where(GlobalProductIdentifierModel.status == status)
        return list(
            self.session.execute(
                statement.order_by(GlobalProductIdentifierModel.identifier_type, GlobalProductIdentifierModel.value)
            ).scalars()
        )

    def create(
        self,
        product_id: UUID,
        *,
        identifier_type: str,
        value: str,
        global_product_presentation_id: UUID | None,
        is_primary: bool,
        actor: str,
    ) -> GlobalProductIdentifierModel:
        product = lock_product(self.session, product_id)
        ensure_product_active_for_dependents(product)

        normalized = normalize_identifier_value(value)
        self._validate_format(identifier_type, normalized)

        if identifier_type == IUM_TYPE and global_product_presentation_id is None:
            raise IumRequiresPresentationError(
                "El IUM identifica una presentación comercial: indique global_product_presentation_id."
            )

        if global_product_presentation_id is not None:
            presentation = self.session.get(GlobalProductPresentationModel, global_product_presentation_id)
            if presentation is None or presentation.global_product_id != product_id:
                raise PresentationOfOtherProductError("La presentación no pertenece al producto.")

        canonical = canonical_value(identifier_type, normalized)
        self._raise_if_collision(product_id, identifier_type, normalized, canonical)

        identifier = GlobalProductIdentifierModel(
            global_product_id=product_id,
            global_product_presentation_id=global_product_presentation_id,
            identifier_type=identifier_type,
            value=normalized,
            canonical_value=canonical,
            is_primary=False,
            status=ACTIVE,
        )
        lifecycle.stamp_create(identifier, actor)
        self.session.add(identifier)
        self.session.flush()

        if is_primary:
            self._make_primary(identifier, actor)

        audit.track_create(self.session, identifier, action=audit.CREATE_PRODUCT_IDENTIFIER, entity_type="ProductIdentifier")
        try:
            self.session.commit()
        except IntegrityError:
            # Red de seguridad ante una carrera: la unicidad la garantiza la base de datos.
            self.session.rollback()
            self._raise_if_collision(product_id, identifier_type, normalized, canonical)
            raise
        return identifier

    def set_primary(self, product_id: UUID, identifier_id: UUID, *, version: int, actor: str):
        product = lock_product(self.session, product_id)
        ensure_product_active_for_dependents(product)
        identifier = self._identifier(product_id, identifier_id)
        lifecycle.check_version(identifier, version)
        if identifier.status != ACTIVE:
            raise ReferenceInactiveError("Solo un identificador vigente puede ser principal.")
        self._make_primary(identifier, actor)
        audit.track_update(self.session, identifier, action=audit.SET_PRIMARY_PRODUCT_IDENTIFIER, entity_type="ProductIdentifier", extra_previous={"previous_primary_id": getattr(self, "_audit_previous_primary_id", None)})
        self.session.commit()
        return identifier

    def deactivate(self, product_id: UUID, identifier_id: UUID, *, version: int, actor: str):
        lock_product(self.session, product_id)
        identifier = self._identifier(product_id, identifier_id)
        lifecycle.deactivate(identifier, version, actor)
        audit.track_update(self.session, identifier, action=audit.DEACTIVATE_PRODUCT_IDENTIFIER, entity_type="ProductIdentifier")
        self.session.commit()
        return identifier

    def reactivate(self, product_id: UUID, identifier_id: UUID, *, version: int, actor: str):
        product = lock_product(self.session, product_id)
        ensure_product_active_for_dependents(product)
        identifier = self._identifier(product_id, identifier_id)
        lifecycle.reactivate(identifier, version, actor)
        audit.track_update(self.session, identifier, action=audit.REACTIVATE_PRODUCT_IDENTIFIER, entity_type="ProductIdentifier")
        self.session.commit()
        return identifier

    # ---------------------------------------------------------------- utilidades

    @staticmethod
    def _validate_format(identifier_type: str, value: str) -> None:
        if identifier_type in GTIN_FAMILY:
            if not has_gtin_shape(value):
                raise InvalidGtinFormatError(
                    "GTIN, EAN y UPC deben ser numéricos de 8, 12, 13 o 14 dígitos."
                )
            if not has_valid_check_digit(value):
                raise InvalidCheckDigitError("El dígito de control GS1 no es válido.")
            return

        if identifier_type == IUM_TYPE:
            if not is_valid_ium(value):
                raise InvalidIumFormatError(
                    "El IUM debe tener 15 caracteres: un dígito, una letra mayúscula y 13 dígitos."
                )
            return

        if identifier_type == "BARCODE" and is_valid_gtin_format(value):
            raise BarcodeIsGtinError(
                "El código cumple el estándar GTIN/EAN/UPC: regístrelo con su tipo específico."
            )

    def _raise_if_collision(self, product_id: UUID, identifier_type: str, value: str, canonical: str) -> None:
        if identifier_type in GTIN_FAMILY:
            condition = and_(
                GlobalProductIdentifierModel.identifier_type.in_(sorted(GTIN_FAMILY)),
                GlobalProductIdentifierModel.canonical_value == canonical,
            )
        elif identifier_type in ("BARCODE", IUM_TYPE):
            # Únicos en todo el catálogo, incluidos los inactivos (DS-17; IUM: FR-057c).
            condition = and_(
                GlobalProductIdentifierModel.identifier_type == identifier_type,
                GlobalProductIdentifierModel.value == value,
            )
        else:
            condition = and_(
                GlobalProductIdentifierModel.identifier_type == "OTHER",
                GlobalProductIdentifierModel.global_product_id == product_id,
                GlobalProductIdentifierModel.value == value,
            )

        existing = self.session.execute(
            select(GlobalProductIdentifierModel).where(condition).limit(1)
        ).scalar_one_or_none()

        if existing is not None:
            raise IdentifierCollisionError(
                f"El código {value} ya identifica otro registro del catálogo; revise la inconsistencia.",
                extra={
                    "conflict": {
                        "global_product_id": str(existing.global_product_id),
                        "global_product_presentation_id": (
                            str(existing.global_product_presentation_id)
                            if existing.global_product_presentation_id
                            else None
                        ),
                        "identifier_id": str(existing.id),
                        "identifier_type": existing.identifier_type,
                        "status": existing.status,
                    }
                },
            )

    def _make_primary(self, identifier: GlobalProductIdentifierModel, actor: str) -> None:
        if identifier.is_primary:
            return

        current = self.session.execute(
            select(GlobalProductIdentifierModel).where(
                GlobalProductIdentifierModel.global_product_id == identifier.global_product_id,
                GlobalProductIdentifierModel.identifier_type == identifier.identifier_type,
                GlobalProductIdentifierModel.is_primary.is_(True),
                GlobalProductIdentifierModel.status == ACTIVE,
                GlobalProductIdentifierModel.global_product_presentation_id.is_(None)
                if identifier.global_product_presentation_id is None
                else GlobalProductIdentifierModel.global_product_presentation_id
                == identifier.global_product_presentation_id,
            )
        ).scalar_one_or_none()

        self._audit_previous_primary_id = current.id if current is not None and current.id != identifier.id else None
        if current is not None and current.id != identifier.id:
            current.is_primary = False
            lifecycle.stamp_update(current, actor)
            self.session.flush()

        identifier.is_primary = True
        lifecycle.stamp_update(identifier, actor)

    def _identifier(self, product_id: UUID, identifier_id: UUID) -> GlobalProductIdentifierModel:
        identifier = self.session.get(GlobalProductIdentifierModel, identifier_id)
        if identifier is None or identifier.global_product_id != product_id:
            raise NotFoundError(f"El identificador {identifier_id} no existe en el producto.")
        return identifier
