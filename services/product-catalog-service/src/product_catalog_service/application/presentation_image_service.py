"""Imágenes de una presentación global (spec 024, FR-024-07 a FR-024-30).

Las imágenes pertenecen **exclusivamente** a una presentación (D-024-1). Cada presentación tiene como máximo una
principal `ACTIVE`, garantizado por `uq_product_assets_presentation_primary`.

Toda modificación se serializa por presentación: bloquea el producto y la fila de la presentación
(`SELECT … FOR UPDATE`) y repite dentro de la transacción las validaciones previas (FR-024-09, FR-024-26).

Product Catalog **nunca** borra objetos del almacenamiento (FR-024-28). Si la base falla después de escribir un
objeto, el objeto queda sin referencia y lo informa la reconciliación de solo lectura (FR-024-29, FR-024-30).
"""

from __future__ import annotations

import logging
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from product_catalog_service.application import audit_events as audit
from product_catalog_service.application import lifecycle
from product_catalog_service.application.exceptions import (
    AssetStorageUnavailableError,
    DependencyUnavailableError,
    DuplicateAssetContentError,
    NotFoundError,
    PresentationInactiveError,
    PresentationOfOtherProductError,
    ReferenceInactiveError,
    ValidationError,
)
from product_catalog_service.application.ports import AssetStorage
from product_catalog_service.application.product_service import ensure_product_active_for_dependents
from product_catalog_service.domain.image_upload import EXTENSIONS, ValidatedImage, sanitize_file_name
from product_catalog_service.infrastructure.locks import lock_product, lock_row
from product_catalog_service.infrastructure.models import (
    GlobalProductModel,
    GlobalProductPresentationModel,
    ProductAssetModel,
)

ACTIVE = lifecycle.ACTIVE
INACTIVE = lifecycle.INACTIVE
IMAGE = "IMAGE"
ENTITY = "ProductAsset"
_REFERENCE_EXTENSIONS = {"image/jpeg": {"jpg", "jpeg"}, "image/png": {"png"}, "image/webp": {"webp"}}

logger = logging.getLogger("product_catalog_service")


def storage_unavailable() -> DependencyUnavailableError:
    return DependencyUnavailableError(
        "El almacenamiento de objetos de los activos no está disponible.", extra={"dependency": "asset-storage"}
    )


class PresentationImageService:
    """Casos de uso de las imágenes de una presentación."""

    def __init__(self, session: Session, *, bucket: str, storage: AssetStorage | None = None) -> None:
        self.session = session
        self.bucket = bucket
        self.storage = storage

    # ------------------------------------------------------------------ lecturas

    def list(self, product_id: UUID, presentation_id: UUID, status: str | None = None) -> list[ProductAssetModel]:
        """Imágenes de la presentación: por defecto `ACTIVE`; principal primero, `created_at` e `id` desc (FR-024-21)."""
        self._context(product_id, presentation_id)
        asset = ProductAssetModel
        return list(
            self.session.scalars(
                select(asset)
                .where(
                    asset.global_product_presentation_id == presentation_id,
                    asset.asset_type == IMAGE,
                    asset.status == (status or ACTIVE),
                )
                .order_by(asset.is_primary.desc(), asset.created_at.desc(), asset.id.desc())
            )
        )

    def content_key(self, product_id: UUID, presentation_id: UUID, asset_id: UUID) -> tuple[ProductAssetModel, str]:
        """Imagen `ACTIVE` de la presentación y la clave de su objeto (FR-024-21b); `404` en cualquier otro caso."""
        self._context(product_id, presentation_id)
        asset = self._image(presentation_id, asset_id)
        if asset.status != ACTIVE:
            raise NotFoundError(f"La imagen {asset_id} no está vigente.")
        return asset, self._key_of(asset.storage_uri)

    # ------------------------------------------------------------------ carga directa

    def upload(
        self, product_id: UUID, presentation_id: UUID, image: ValidatedImage, *, file_name: str | None, actor: str
    ) -> tuple[ProductAssetModel, bool]:
        """Carga una imagen ya validada. Devuelve el activo y si es nuevo (`201`) o reutilizado (`200`, caso C)."""
        storage_uri = f"s3://{self.bucket}/{image.key}"

        # Validaciones previas, sin bloqueo y sin tocar el almacenamiento (FR-024-09, FR-024-18).
        self._context(product_id, presentation_id, require_active=True)
        existing = self._duplicate(presentation_id, storage_uri)
        if existing is not None and existing.status == ACTIVE:
            self._log("upload", product_id, presentation_id, existing.id, image, "duplicado-activo")
            raise self._duplicate_error(existing)
        self.session.rollback()  # libera la lectura antes de escribir el objeto

        written = self._ensure_object(image)

        # Registro, solo después de que el almacenamiento confirmó el objeto (FR-024-15).
        self._context(product_id, presentation_id, require_active=True, lock=True)
        existing = self._duplicate(presentation_id, storage_uri)
        content = {"sha256": image.sha256, "size_bytes": image.size, "object_written": written}
        if existing is not None and existing.status == ACTIVE:
            self.session.rollback()
            self._log("upload", product_id, presentation_id, existing.id, image, "duplicado-activo")
            raise self._duplicate_error(existing)

        if existing is not None:  # caso C: mismo contenido INACTIVE, se reutiliza el mismo activo
            audit.remember(self.session, existing)
            existing.status = ACTIVE
            lifecycle.stamp_update(existing, actor)
            previous = self._make_primary(existing, actor)
            audit.track_update(self.session, existing, action=audit.REACTIVATE_PRODUCT_ASSET, entity_type=ENTITY,
                               extra_new=content)
            self._track_primary(existing, previous)
            self.session.commit()
            self._log("upload", product_id, presentation_id, existing.id, image, "reactivada")
            return existing, False

        asset = ProductAssetModel(
            global_product_id=product_id,
            global_product_presentation_id=presentation_id,
            asset_type=IMAGE,
            file_name=sanitize_file_name(file_name, image.extension),
            storage_uri=storage_uri,
            mime_type=image.mime_type,
            is_primary=False,
            status=ACTIVE,
        )
        lifecycle.stamp_create(asset, actor)
        self.session.add(asset)
        self.session.flush()
        previous = self._make_primary(asset, actor)
        audit.track_create(self.session, asset, action=audit.CREATE_PRODUCT_ASSET, entity_type=ENTITY, extra_new=content)
        self._track_primary(asset, previous)
        self.session.commit()
        self._log("upload", product_id, presentation_id, asset.id, image, "creada")
        return asset, True

    def _ensure_object(self, image: ValidatedImage) -> bool:
        """Escribe el objeto si no existe; nunca reemplaza uno con contenido distinto (FR-024-16). `True` si escribió."""
        if self.storage is None:
            raise storage_unavailable()
        try:
            info = self.storage.head(image.key)
            written = False
            if info is None:
                written = self.storage.put_if_absent(
                    image.key, image.content, content_type=image.mime_type, metadata={"sha256": image.sha256}
                )
                if not written:  # otra carga lo escribió entre la consulta y la escritura
                    info = self.storage.head(image.key)
            if not written and (info is None or info.metadata.get("sha256") != image.sha256):
                logger.error("Objeto con integridad distinta a su clave sha256=%s", image.sha256)
                raise storage_unavailable()
        except AssetStorageUnavailableError as exc:
            logger.warning("Almacenamiento no disponible en la carga sha256=%s", image.sha256)
            raise storage_unavailable() from exc
        return written

    # ------------------------------------------------------------------ registro por referencia

    def register(
        self,
        product_id: UUID,
        presentation_id: UUID,
        *,
        file_name: str,
        storage_uri: str,
        mime_type: str,
        is_primary: bool,
        actor: str,
    ) -> ProductAssetModel:
        """Registra una imagen ya almacenada en SIO (DD-024-6, FR-024-22). Un duplicado, activo o no, responde `409`."""
        uri, sha = self._reference(storage_uri, mime_type)
        self._context(product_id, presentation_id, require_active=True)
        existing = self._duplicate(presentation_id, uri)
        if existing is not None:
            raise self._duplicate_error(existing)
        self.session.rollback()

        if self.storage is None:
            raise storage_unavailable()
        try:
            info = self.storage.head(self._key_of(uri))
        except AssetStorageUnavailableError as exc:
            raise storage_unavailable() from exc
        if info is None or info.metadata.get("sha256") != sha:
            raise ValidationError(
                "storage_uri no corresponde a un objeto almacenado en SIO con la integridad de su clave.",
                field="storage_uri",
            )

        self._context(product_id, presentation_id, require_active=True, lock=True)
        existing = self._duplicate(presentation_id, uri)
        if existing is not None:
            self.session.rollback()
            raise self._duplicate_error(existing)
        name = (file_name or "").strip()
        if not name or len(name) > 255:
            raise ValidationError("file_name es obligatorio y no puede superar 255 caracteres.", field="file_name")
        asset = ProductAssetModel(
            global_product_id=product_id,
            global_product_presentation_id=presentation_id,
            asset_type=IMAGE,
            file_name=name,
            storage_uri=uri,
            mime_type=mime_type,
            is_primary=False,
            status=ACTIVE,
        )
        lifecycle.stamp_create(asset, actor)
        self.session.add(asset)
        self.session.flush()
        previous = self._make_primary(asset, actor) if is_primary else None
        audit.track_create(self.session, asset, action=audit.CREATE_PRODUCT_ASSET, entity_type=ENTITY,
                           extra_new={"sha256": sha, "size_bytes": info.size})
        if is_primary:
            self._track_primary(asset, previous)
        self.session.commit()
        logger.info("Imagen registrada por referencia producto=%s presentacion=%s activo=%s sha256=%s",
                    product_id, presentation_id, asset.id, sha)
        return asset

    def _reference(self, storage_uri: str, mime_type: str) -> tuple[str, str]:
        uri = (storage_uri or "").strip()
        match = re.fullmatch(rf"s3://{re.escape(self.bucket)}/assets/([0-9a-f]{{64}})\.([a-z]+)", uri)
        if match is None:
            raise ValidationError(
                "storage_uri debe ser una imagen del almacenamiento de SIO: s3://<bucket>/assets/<sha256>.<ext>.",
                field="storage_uri",
            )
        if mime_type not in EXTENSIONS:
            raise ValidationError("mime_type debe ser image/jpeg, image/png o image/webp.", field="mime_type")
        if match.group(2) not in _REFERENCE_EXTENSIONS[mime_type]:
            raise ValidationError("La extensión de storage_uri no coincide con mime_type.", field="storage_uri")
        return uri, match.group(1)

    # ------------------------------------------------------------------ gestión

    def rename(self, product_id: UUID, presentation_id: UUID, asset_id: UUID, *, version: int, file_name: str,
               actor: str) -> ProductAssetModel:
        """Solo cambia `file_name` (FR-024-21c, DD-024-8)."""
        self._context(product_id, presentation_id, require_active=True, lock=True)
        asset = self._image(presentation_id, asset_id)
        lifecycle.check_version(asset, version)
        extension = EXTENSIONS.get(asset.mime_type or "", "img")
        asset.file_name = sanitize_file_name(file_name, extension)
        lifecycle.stamp_update(asset, actor)
        audit.track_update(self.session, asset, action=audit.UPDATE_PRODUCT_ASSET, entity_type=ENTITY)
        self.session.commit()
        return asset

    def set_primary(self, product_id: UUID, presentation_id: UUID, asset_id: UUID, *, version: int,
                    actor: str) -> ProductAssetModel:
        """Marca como principal una imagen `ACTIVE` de esta presentación (FR-024-23); no toca el almacenamiento."""
        self._context(product_id, presentation_id, require_active=True, lock=True)
        asset = self._image(presentation_id, asset_id)
        lifecycle.check_version(asset, version)
        if asset.status != ACTIVE:
            raise ReferenceInactiveError("Solo una imagen vigente puede ser principal.")
        audit.remember(self.session, asset)
        previous = self._make_primary(asset, actor)
        audit.track_update(self.session, asset, action=audit.SET_PRIMARY_PRODUCT_ASSET, entity_type=ENTITY,
                           extra_previous={"previous_primary_id": previous})
        self.session.commit()
        return asset

    def deactivate(self, product_id: UUID, presentation_id: UUID, asset_id: UUID, *, version: int,
                   actor: str) -> ProductAssetModel:
        """Inactiva la imagen y, si era la principal, asigna sucesor determinista (FR-024-24). Nunca borra el objeto."""
        self._context(product_id, presentation_id, lock=True)
        asset = self._image(presentation_id, asset_id)
        audit.remember(self.session, asset)
        was_primary = asset.is_primary
        if not lifecycle.deactivate(asset, version, actor):
            return asset
        audit.track_update(self.session, asset, action=audit.DEACTIVATE_PRODUCT_ASSET, entity_type=ENTITY)
        self.session.flush()
        if was_primary:
            successor = self.session.scalars(
                select(ProductAssetModel)
                .where(
                    ProductAssetModel.global_product_presentation_id == presentation_id,
                    ProductAssetModel.asset_type == IMAGE,
                    ProductAssetModel.status == ACTIVE,
                    ProductAssetModel.id != asset.id,
                )
                .order_by(ProductAssetModel.created_at.desc(), ProductAssetModel.id.desc())
                .limit(1)
            ).first()
            if successor is not None:
                audit.remember(self.session, successor)
                successor.is_primary = True
                lifecycle.stamp_update(successor, actor)
                audit.track_update(self.session, successor, action=audit.SET_PRIMARY_PRODUCT_ASSET, entity_type=ENTITY,
                                   extra_previous={"previous_primary_id": asset.id})
        self.session.commit()
        return asset

    def reactivate(self, product_id: UUID, presentation_id: UUID, asset_id: UUID, *, version: int,
                   actor: str) -> ProductAssetModel:
        """Reactiva la imagen **sin** marcarla como principal (D-024-7, FR-024-25)."""
        self._context(product_id, presentation_id, require_active=True, lock=True)
        asset = self._image(presentation_id, asset_id)
        if lifecycle.reactivate(asset, version, actor):
            audit.track_update(self.session, asset, action=audit.REACTIVATE_PRODUCT_ASSET, entity_type=ENTITY)
        self.session.commit()
        return asset

    # ------------------------------------------------------------------ utilidades

    def _context(
        self, product_id: UUID, presentation_id: UUID, *, require_active: bool = False, lock: bool = False
    ) -> tuple[GlobalProductModel, GlobalProductPresentationModel]:
        """Producto y presentación de la ruta (FR-024-09): `404`, presentación de otro producto e inactivos."""
        if lock:
            product = lock_product(self.session, product_id)
            presentation = lock_row(self.session, GlobalProductPresentationModel, presentation_id, label="La presentación")
        else:
            product = self.session.get(GlobalProductModel, product_id)
            if product is None:
                raise NotFoundError(f"El producto {product_id} no existe.")
            presentation = self.session.get(GlobalProductPresentationModel, presentation_id)
            if presentation is None:
                raise NotFoundError(f"La presentación {presentation_id} no existe.")
        if presentation.global_product_id != product_id:
            raise PresentationOfOtherProductError("La presentación no pertenece al producto indicado.")
        if require_active:
            ensure_product_active_for_dependents(product)
            if presentation.status != ACTIVE:
                raise PresentationInactiveError("La presentación está inactiva: no admite cambios en sus imágenes.")
        return product, presentation

    def _image(self, presentation_id: UUID, asset_id: UUID) -> ProductAssetModel:
        asset = self.session.get(ProductAssetModel, asset_id)
        if asset is None or asset.asset_type != IMAGE or asset.global_product_presentation_id != presentation_id:
            raise NotFoundError(f"La imagen {asset_id} no existe en la presentación.")
        return asset

    def _duplicate(self, presentation_id: UUID, storage_uri: str) -> ProductAssetModel | None:
        """Imagen con el mismo contenido (misma clave por SHA-256) en la presentación; la `ACTIVE` primero."""
        return self.session.scalars(
            select(ProductAssetModel)
            .where(
                ProductAssetModel.global_product_presentation_id == presentation_id,
                ProductAssetModel.asset_type == IMAGE,
                ProductAssetModel.storage_uri == storage_uri,
            )
            .order_by((ProductAssetModel.status == ACTIVE).desc(), ProductAssetModel.created_at.desc())
            .limit(1)
        ).first()

    @staticmethod
    def _duplicate_error(existing: ProductAssetModel) -> DuplicateAssetContentError:
        return DuplicateAssetContentError(
            "La presentación ya tiene una imagen con el mismo contenido.",
            extra={"existing_asset_id": str(existing.id)},
        )

    def _make_primary(self, asset: ProductAssetModel, actor: str) -> UUID | None:
        """Marca la imagen como principal de su presentación; devuelve el id del principal anterior."""
        if asset.is_primary:
            return None
        current = self.session.scalars(
            select(ProductAssetModel).where(
                ProductAssetModel.global_product_presentation_id == asset.global_product_presentation_id,
                ProductAssetModel.asset_type == IMAGE,
                ProductAssetModel.is_primary.is_(True),
                ProductAssetModel.status == ACTIVE,
                ProductAssetModel.id != asset.id,
            )
        ).first()
        if current is not None:
            current.is_primary = False
            lifecycle.stamp_update(current, actor)
            self.session.flush()
        asset.is_primary = True
        lifecycle.stamp_update(asset, actor)
        return current.id if current is not None else None

    def _track_primary(self, asset: ProductAssetModel, previous: UUID | None) -> None:
        """`SET_PRIMARY_PRODUCT_ASSET` cuando la carga reemplaza a otra principal (FR-024-27)."""
        if previous is not None:
            audit.track_update(self.session, asset, action=audit.SET_PRIMARY_PRODUCT_ASSET, entity_type=ENTITY,
                               extra_previous={"previous_primary_id": previous})

    def _key_of(self, storage_uri: str) -> str:
        prefix = f"s3://{self.bucket}/"
        if not storage_uri.startswith(prefix):
            raise NotFoundError("El contenido de la imagen no está en el almacenamiento de SIO.")
        return storage_uri[len(prefix):]

    @staticmethod
    def _log(operation: str, product_id: UUID, presentation_id: UUID, asset_id: UUID, image: ValidatedImage,
             result: str) -> None:
        logger.info(
            "Imagen de presentacion operacion=%s producto=%s presentacion=%s activo=%s sha256=%s bytes=%s resultado=%s",
            operation, product_id, presentation_id, asset_id, image.sha256, image.size, result,
        )
