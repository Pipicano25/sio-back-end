"""Doble en memoria del almacenamiento de objetos (puerto `AssetStorage`) para las pruebas."""

from __future__ import annotations

from collections.abc import Iterator

from product_catalog_service.application.exceptions import AssetStorageUnavailableError
from product_catalog_service.application.ports import StoredObject

BUCKET = "sio-product-assets"


class FakeAssetStorage:
    def __init__(self) -> None:
        self.bucket = BUCKET
        self.objects: dict[str, tuple[bytes, str, dict[str, str]]] = {}
        self.unavailable = False
        self.calls: list[str] = []

    def _info(self, key: str) -> StoredObject:
        data, content_type, metadata = self.objects[key]
        return StoredObject(key=key, size=len(data), content_type=content_type, etag="s3-etag", metadata=metadata)

    def head(self, key: str) -> StoredObject | None:
        self.calls.append("head")
        if self.unavailable:
            raise AssetStorageUnavailableError("caído")
        return self._info(key) if key in self.objects else None

    def exists(self, key: str) -> bool:
        return self.head(key) is not None

    def get(self, key: str):
        self.calls.append("get")
        if self.unavailable:
            raise AssetStorageUnavailableError("caído")
        if key not in self.objects:
            return None
        data = self.objects[key][0]

        def chunks() -> Iterator[bytes]:
            for start in range(0, len(data), 65536):
                yield data[start:start + 65536]

        return self._info(key), chunks()

    def put(self, key, data, *, content_type, metadata=None):
        self.objects[key] = (data, content_type, metadata or {})
        return self._info(key)

    def put_if_absent(self, key, data, *, content_type, metadata=None) -> bool:
        """Escritura condicional (spec 024): nunca reemplaza; `unavailable` simula la caída."""
        self.calls.append("put_if_absent")
        if self.unavailable:
            raise AssetStorageUnavailableError("caído")
        if key in self.objects:
            return False
        self.objects[key] = (data, content_type, metadata or {})
        return True

    def list_keys(self, prefix: str):
        self.calls.append("list")
        if self.unavailable:
            raise AssetStorageUnavailableError("caído")
        return iter(sorted(key for key in self.objects if key.startswith(prefix)))
