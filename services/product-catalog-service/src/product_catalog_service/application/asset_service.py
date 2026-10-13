"""Activos digitales del producto (FR-067 a FR-069, DS-15).

Solo se guarda la referencia al recurso externo; nunca el binario.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from product_catalog_service.application import audit_events as audit
from product_catalog_service.application import lifecycle
from product_catalog_service.application.exceptions import (
    AssetContentNotStoredError,
    InvalidStorageUriError,
    NotFoundError,
    ReferenceInactiveError,
    ValidationError,
)
from product_catalog_service.application.product_service import ensure_product_active_for_dependents
from product_catalog_service.infrastructure.locks import lock_product
from product_catalog_service.infrastructure.models import GlobalProductModel, ProductAssetModel

ACTIVE = lifecycle.ACTIVE
_MIME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]*/[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]*$")


def validate_storage_uri(value: str) -> str:
    """URI absoluto: esquema y ubicación (o ruta, para esquemas como `urn:`)."""
    uri = (value or "").strip()
    parsed = urlparse(uri)
    if not parsed.scheme or not (parsed.netloc or parsed.path) or " " in uri:
        raise InvalidStorageUriError("storage_uri debe ser un URI absoluto (p. ej. s3://bucket/ruta).")
    if parsed.scheme in {"http", "https", "s3", "gs", "ftp"} and not parsed.netloc:
        raise InvalidStorageUriError("storage_uri debe incluir la ubicación del recurso.")
    return uri


def validate_file_name(value: str) -> str:
    name = (value or "").strip()
    if not name:
        raise ValidationError("file_name es obligatorio.", field="file_name")
    if len(name) > 255:
        raise ValidationError("file_name no puede superar 255 caracteres.", field="file_name")
    return name


def validate_mime_type(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    mime = value.strip()
    if len(mime) > 120 or not _MIME.match(mime):
        raise ValidationError("mime_type debe tener el formato tipo/subtipo.", field="mime_type")
    return mime


class AssetService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, product_id: UUID, status: str | None = None, asset_type: str | None = None):
        if self.session.get(GlobalProductModel, product_id) is None:
            raise NotFoundError(f"El producto {product_id} no existe.")
        statement = select(ProductAssetModel).where(ProductAssetModel.global_product_id == product_id)
        if status is not None:
            statement = statement.where(ProductAssetModel.status == status)
        if asset_type is not None:
            statement = statement.where(ProductAssetModel.asset_type == asset_type)
        return list(
            self.session.execute(statement.order_by(ProductAssetModel.asset_type, ProductAssetModel.created_at)).scalars()
        )

    def create(
        self,
        product_id: UUID,
        *,
        asset_type: str,
        file_name: str,
        storage_uri: str,
        mime_type: str | None,
        is_primary: bool,
        actor: str,
    ) -> ProductAssetModel:
        product = lock_product(self.session, product_id)
        ensure_product_active_for_dependents(product)

        asset = ProductAssetModel(
            global_product_id=product_id,
            asset_type=asset_type,
            file_name=validate_file_name(file_name),
            storage_uri=validate_storage_uri(storage_uri),
            mime_type=validate_mime_type(mime_type),
            is_primary=False,
            status=ACTIVE,
        )
        lifecycle.stamp_create(asset, actor)
        self.session.add(asset)
        self.session.flush()

        if is_primary:
            self._make_primary(asset, actor)

        audit.track_create(self.session, asset, action=audit.CREATE_PRODUCT_ASSET, entity_type="ProductAsset")
        self.session.commit()
        return asset

    def update(
        self,
        product_id: UUID,
        asset_id: UUID,
        *,
        version: int,
        file_name: str,
        storage_uri: str,
        mime_type: str | None,
        actor: str,
    ) -> ProductAssetModel:
        product = lock_product(self.session, product_id)
        ensure_product_active_for_dependents(product)
        asset = self._asset(product_id, asset_id)
        lifecycle.check_version(asset, version)
        asset.file_name = validate_file_name(file_name)
        asset.storage_uri = validate_storage_uri(storage_uri)
        asset.mime_type = validate_mime_type(mime_type)
        lifecycle.stamp_update(asset, actor)
        audit.track_update(self.session, asset, action=audit.UPDATE_PRODUCT_ASSET, entity_type="ProductAsset")
        self.session.commit()
        return asset

    def set_primary(self, product_id: UUID, asset_id: UUID, *, version: int, actor: str) -> ProductAssetModel:
        product = lock_product(self.session, product_id)
        ensure_product_active_for_dependents(product)
        asset = self._asset(product_id, asset_id)
        lifecycle.check_version(asset, version)
        if asset.status != ACTIVE:
            raise ReferenceInactiveError("Solo un activo vigente puede ser principal.")
        self._make_primary(asset, actor)
        audit.track_update(self.session, asset, action=audit.SET_PRIMARY_PRODUCT_ASSET, entity_type="ProductAsset", extra_previous={"previous_primary_id": getattr(self, "_audit_previous_primary_id", None)})
        self.session.commit()
        return asset

    def deactivate(self, product_id: UUID, asset_id: UUID, *, version: int, actor: str) -> ProductAssetModel:
        lock_product(self.session, product_id)
        asset = self._asset(product_id, asset_id)
        lifecycle.deactivate(asset, version, actor)
        audit.track_update(self.session, asset, action=audit.DEACTIVATE_PRODUCT_ASSET, entity_type="ProductAsset")
        self.session.commit()
        return asset

    def reactivate(self, product_id: UUID, asset_id: UUID, *, version: int, actor: str) -> ProductAssetModel:
        product = lock_product(self.session, product_id)
        ensure_product_active_for_dependents(product)
        asset = self._asset(product_id, asset_id)
        lifecycle.reactivate(asset, version, actor)
        audit.track_update(self.session, asset, action=audit.REACTIVATE_PRODUCT_ASSET, entity_type="ProductAsset")
        self.session.commit()
        return asset

    # ---------------------------------------------------------------- utilidades

    def _make_primary(self, asset: ProductAssetModel, actor: str) -> None:
        if asset.is_primary:
            return
        current = self.session.execute(
            select(ProductAssetModel).where(
                ProductAssetModel.global_product_id == asset.global_product_id,
                ProductAssetModel.asset_type == asset.asset_type,
                ProductAssetModel.is_primary.is_(True),
                ProductAssetModel.status == ACTIVE,
            )
        ).scalar_one_or_none()
        self._audit_previous_primary_id = current.id if current is not None and current.id != asset.id else None
        if current is not None and current.id != asset.id:
            current.is_primary = False
            lifecycle.stamp_update(current, actor)
            self.session.flush()
        asset.is_primary = True
        lifecycle.stamp_update(asset, actor)

    def content_key(self, product_id: UUID, asset_id: UUID, bucket: str) -> tuple[ProductAssetModel, str]:
        """Activo vigente y clave del objeto en el almacenamiento de SIO (`s3://<bucket>/<clave>`).

        Un activo con referencia externa (p. ej. `https://…` histórico) sigue siendo válido como
        recurso, pero su contenido no lo entrega SIO: `409 ASSET_CONTENT_NOT_STORED`.
        """
        if self.session.get(GlobalProductModel, product_id) is None:
            raise NotFoundError(f"El producto {product_id} no existe.")
        asset = self._asset(product_id, asset_id)
        if asset.status != ACTIVE:
            raise NotFoundError(f"El activo {asset_id} no está vigente.")
        parsed = urlparse(asset.storage_uri)
        if parsed.scheme != "s3" or parsed.netloc != bucket or not parsed.path.strip("/"):
            raise AssetContentNotStoredError(
                "El activo referencia un recurso externo; su contenido no está en el almacenamiento de SIO."
            )
        return asset, parsed.path.lstrip("/")

    def _asset(self, product_id: UUID, asset_id: UUID) -> ProductAssetModel:
        asset = self.session.get(ProductAssetModel, asset_id)
        if asset is None or asset.global_product_id != product_id:
            raise NotFoundError(f"El activo {asset_id} no existe en el producto.")
        return asset
