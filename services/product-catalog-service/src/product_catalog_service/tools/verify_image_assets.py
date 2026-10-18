"""Verificación de solo lectura de las imágenes registradas antes de habilitar la ruta pública (spec 022, FR-022-99).

Para cada activo `IMAGE` `ACTIVE` comprueba, sin modificar nada:

- que sea apto para URL (tipo JPEG, PNG o WebP, almacenamiento de SIO y clave derivada del SHA-256);
- que el objeto exista, que su tamaño sea mayor que cero y que el SHA-256 de sus metadatos (si lo tiene)
  coincida con el de la clave;
- que sus primeros bytes correspondan al tipo declarado.

El informe solo contiene ids de activos y de productos, el resultado y los totales: nunca bucket, claves,
`storage_uri` ni credenciales. La base se abre en modo de solo lectura (`default_transaction_read_only`).

**No se ejecuta sobre el entorno persistente sin autorización.** Uso:

    python -m product_catalog_service.tools.verify_image_assets --confirm-read-only > informe.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any

from product_catalog_service.application.exceptions import AssetStorageUnavailableError
from product_catalog_service.application.ports import AssetStorage
from product_catalog_service.domain.image_content import SNIFF_BYTES, matches_declared_type
from product_catalog_service.domain.image_ref import eligible_image_sha

OK = "OK"
NOT_ELIGIBLE = "NOT_ELIGIBLE"
OBJECT_MISSING = "OBJECT_MISSING"
EMPTY_OBJECT = "EMPTY_OBJECT"
SHA_MISMATCH = "SHA_MISMATCH"
CONTENT_MISMATCH = "CONTENT_MISMATCH"
STORAGE_UNAVAILABLE = "STORAGE_UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class AssetResult:
    asset_id: str
    global_product_id: str
    is_primary: bool
    result: str


def _first_bytes(chunks: Iterable[bytes]) -> bytes:
    head = b""
    for chunk in chunks:
        head += chunk
        if len(head) >= SNIFF_BYTES:
            break
    return head


def verify_asset(asset: Any, storage: AssetStorage, bucket: str) -> str:
    """Resultado de un activo (solo lecturas del almacenamiento)."""
    sha = eligible_image_sha(asset, bucket, require_primary=False)
    if sha is None:
        return NOT_ELIGIBLE
    key = asset.storage_uri.split("/", 3)[3]
    try:
        found = storage.get(key)
    except AssetStorageUnavailableError:
        return STORAGE_UNAVAILABLE
    if found is None:
        return OBJECT_MISSING
    info, chunks = found
    if info.size <= 0:
        return EMPTY_OBJECT
    stored = info.metadata.get("sha256")
    if stored is not None and stored != sha:
        return SHA_MISMATCH
    if not matches_declared_type(_first_bytes(chunks), asset.mime_type):
        return CONTENT_MISMATCH
    return OK


def verify(assets: Iterable[Any], storage: AssetStorage, bucket: str) -> dict:
    """Informe completo: un resultado por activo y los totales por resultado."""
    results = [
        AssetResult(str(asset.id), str(asset.global_product_id), bool(asset.is_primary), verify_asset(asset, storage, bucket))
        for asset in assets
    ]
    return {
        "totals": dict(sorted(Counter(item.result for item in results).items())),
        "primary_totals": dict(sorted(Counter(item.result for item in results if item.is_primary).items())),
        "assets": [asdict(item) for item in results],
    }


def _load_assets(database_url: str) -> list[Any]:  # pragma: no cover - solo en ejecución real autorizada
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from product_catalog_service.infrastructure.models import ProductAssetModel

    engine = create_engine(database_url, connect_args={"options": "-c default_transaction_read_only=on"})
    try:
        with Session(engine) as session:
            rows = session.scalars(
                select(ProductAssetModel)
                .where(ProductAssetModel.asset_type == "IMAGE", ProductAssetModel.status == "ACTIVE")
                .order_by(ProductAssetModel.global_product_id, ProductAssetModel.id)
            ).all()
            for row in rows:
                session.expunge(row)
            return list(rows)
    finally:
        engine.dispose()


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - solo en ejecución real autorizada
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--confirm-read-only", action="store_true", help="Confirma que la ejecución está autorizada.")
    args = parser.parse_args(argv)
    if not args.confirm_read_only:
        print("Se requiere --confirm-read-only y autorización previa (FR-022-99).", file=sys.stderr)
        return 2

    from product_catalog_service.config import load_settings
    from product_catalog_service.infrastructure.s3_asset_storage import S3AssetStorage

    settings = load_settings()
    storage = S3AssetStorage.from_settings(settings)
    if storage is None:
        print("El almacenamiento de objetos no está configurado.", file=sys.stderr)
        return 2
    report = verify(_load_assets(settings.database_url), storage, settings.asset_storage_bucket)
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
