"""Relleno de la migración de imágenes a presentaciones (spec 024, FR-024-46 a FR-024-53; research R8).

Asocia cada imagen (`asset_type = IMAGE`) a la presentación que indica una fuente verificable, **nunca** por
heurística:

- el Gold de DAO (`product_assets.csv`, columna `product_presentation_ref`) traducido a ids de SIO con el diario
  de cargue (`sio_ids.csv`): referencia del activo → id del activo y referencia de la presentación → id de la
  presentación (FR-024-47.1);
- o un archivo de correspondencia `asset_id,global_product_presentation_id` revisado por una persona
  (FR-024-47.2).

Modos:

- `plan` (por defecto): simulación en **solo lectura** con el mismo reporte;
- `apply`: una transacción, todo o nada e idempotente; exige `--confirm-apply`;
- `verify`: comprobación de solo lectura del resultado.

Con un solo caso ambiguo o inconsistente, el relleno **no aplica nada** (FR-024-48). Cada objeto se comprueba
leyendo solo sus metadatos (`HEAD`); nunca se descarga, sube, copia ni modifica (FR-024-51).

Los principales se fijan **después** de asociar (FR-024-50):

- una presentación con una sola imagen `ACTIVE` la recibe como principal;
- con varias, conserva la que ya era principal;
- si ninguna o más de una lo era, el principal es indeterminable y la migración se detiene.

La evidencia (FR-024-52b) se escribe en `--report-dir`. Incluye un JSON y un CSV por ejecución, con conteos antes
y después, una fila por imagen y las consultas SQL de solo lectura que permiten repetir la verificación. Nunca
incluye bucket, claves, `storage_uri` ni credenciales.

**No se ejecuta sobre un entorno persistente sin autorización humana.** Uso:

    python -m product_catalog_service.tools.migrate_presentation_images plan \
        --gold tools/data-migration/DAO/gold/product_assets.csv \
        --sio-ids tools/data-migration/DAO/reports/cargue/sio_ids.csv \
        --expected-images 378 --report-dir ~/sio-respaldos/<fecha>-spec024/evidencia
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from product_catalog_service.application.exceptions import AssetStorageUnavailableError
from product_catalog_service.application.ports import AssetStorage
from product_catalog_service.domain.image_ref import ALLOWED_IMAGE_TYPES, sha_from_key

ACTOR_SUBJECT = "spec-024-migration"
ACTOR_USERNAME = "migracion-imagenes-spec-024"

# Resultados por imagen.
ASSOCIATE = "ASSOCIATE"
ALREADY_ASSOCIATED = "ALREADY_ASSOCIATED"
# Causas que detienen el relleno (FR-024-48).
NO_MAPPING = "NO_MAPPING"
ASSET_NOT_IN_JOURNAL = "ASSET_NOT_IN_JOURNAL"
PRESENTATION_NOT_IN_JOURNAL = "PRESENTATION_NOT_IN_JOURNAL"
PRESENTATION_MISSING = "PRESENTATION_MISSING"
PRESENTATION_OF_OTHER_PRODUCT = "PRESENTATION_OF_OTHER_PRODUCT"
SOURCES_CONTRADICT = "SOURCES_CONTRADICT"
ASSOCIATED_TO_OTHER = "ASSOCIATED_TO_OTHER_PRESENTATION"
NOT_SHA_KEY = "NOT_ELIGIBLE_SHA_KEY"
OBJECT_MISSING = "OBJECT_MISSING"
SHA_MISMATCH = "SHA_MISMATCH"
STORAGE_UNAVAILABLE = "STORAGE_UNAVAILABLE"
INDETERMINATE_PRIMARY = "INDETERMINATE_PRIMARY"


class MigrationBlocked(RuntimeError):
    """El relleno no puede aplicarse: hay casos ambiguos o inconsistentes (ver el reporte)."""

    def __init__(self, plan: "Plan") -> None:
        super().__init__(f"{len(plan.blocking)} imágenes y {len(plan.source_issues)} filas de la fuente con causa.")
        self.plan = plan


@dataclass(frozen=True, slots=True)
class Mapping:
    """Presentación esperada de cada activo y, si la fuente lo informa, su producto y su `storage_uri`."""

    presentation_by_asset: dict[UUID, UUID]
    product_by_asset: dict[UUID, UUID] = field(default_factory=dict)
    storage_uri_by_asset: dict[UUID, str] = field(default_factory=dict)
    issues: dict[str, str] = field(default_factory=dict)  # referencia de la fuente → causa
    source: str = ""


@dataclass(slots=True)
class ImageRow:
    asset_id: str
    global_product_id: str
    global_product_presentation_id: str | None
    status: str
    is_primary_before: bool
    is_primary_after: bool | None = None
    result: str = ""
    cause: str | None = None
    storage_check: str | None = None


# ------------------------------------------------------------------ fuentes


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def mapping_from_gold(gold_csv: Path, sio_ids_csv: Path) -> Mapping:
    """Correspondencia desde el Gold (`product_presentation_ref`) y el diario de cargue (FR-024-47.1)."""
    journal: dict[tuple[str, str], str] = {}
    for row in _read_csv(sio_ids_csv):
        if row.get("sio_id"):
            journal[(row["csv"], row["ref"])] = row["sio_id"]

    presentation_by_asset: dict[UUID, UUID] = {}
    product_by_asset: dict[UUID, UUID] = {}
    storage_uri_by_asset: dict[UUID, str] = {}
    issues: dict[str, str] = {}
    for row in _read_csv(gold_csv):
        if row.get("asset_type") != "IMAGE":
            continue
        asset_ref = row["product_asset_ref"]
        asset_id = journal.get(("product_assets", asset_ref))
        if asset_id is None:
            issues[asset_ref] = ASSET_NOT_IN_JOURNAL
            continue
        presentation_ref = (row.get("product_presentation_ref") or "").strip()
        presentation_id = journal.get(("product_presentations", presentation_ref)) if presentation_ref else None
        if presentation_id is None:
            issues[asset_ref] = PRESENTATION_NOT_IN_JOURNAL if presentation_ref else NO_MAPPING
            continue
        asset_uuid = UUID(asset_id)
        if asset_uuid in presentation_by_asset and presentation_by_asset[asset_uuid] != UUID(presentation_id):
            issues[asset_ref] = SOURCES_CONTRADICT
            continue
        presentation_by_asset[asset_uuid] = UUID(presentation_id)
        product_id = journal.get(("products", row.get("product_ref", "")))
        if product_id:
            product_by_asset[asset_uuid] = UUID(product_id)
        if row.get("storage_uri"):
            storage_uri_by_asset[asset_uuid] = row["storage_uri"].strip()
    return Mapping(presentation_by_asset, product_by_asset, storage_uri_by_asset, issues, source="gold+sio_ids")


def mapping_from_file(mapping_csv: Path) -> Mapping:
    """Correspondencia revisada por una persona: columnas `asset_id,global_product_presentation_id`."""
    presentation_by_asset: dict[UUID, UUID] = {}
    issues: dict[str, str] = {}
    for row in _read_csv(mapping_csv):
        asset_id, presentation_id = UUID(row["asset_id"]), UUID(row["global_product_presentation_id"])
        if asset_id in presentation_by_asset and presentation_by_asset[asset_id] != presentation_id:
            issues[str(asset_id)] = SOURCES_CONTRADICT
        presentation_by_asset[asset_id] = presentation_id
    return Mapping(presentation_by_asset, issues=issues, source="mapping-file")


# ------------------------------------------------------------------ plan (función pura)


@dataclass(slots=True)
class Plan:
    rows: list[ImageRow]
    blocking: list[ImageRow]
    source_issues: dict[str, str]
    unmatched_mapping: list[str]
    storage_totals: dict[str, int]

    @property
    def ok(self) -> bool:
        return not self.blocking and not self.source_issues


def build_plan(
    images: Iterable[Any],
    presentations: dict[UUID, UUID],
    mapping: Mapping,
    storage: AssetStorage | None,
    bucket: str,
) -> Plan:
    """Plan de asociación y principales. `presentations`: id de presentación → id de su producto.

    No escribe nada: solo lee los metadatos de los objetos de las imágenes que faltan por asociar.
    """
    images = list(images)
    rows: dict[UUID, ImageRow] = {}
    target: dict[UUID, UUID] = {}
    storage_totals: Counter[str] = Counter()

    for image in images:
        row = ImageRow(
            asset_id=str(image.id),
            global_product_id=str(image.global_product_id),
            global_product_presentation_id=None,
            status=image.status,
            is_primary_before=bool(image.is_primary),
        )
        rows[image.id] = row
        expected = mapping.presentation_by_asset.get(image.id)
        current = image.global_product_presentation_id

        if current is not None:
            row.global_product_presentation_id = str(current)
            if expected is not None and expected != current:
                row.result, row.cause = "BLOCKED", ASSOCIATED_TO_OTHER
                continue
            row.result = ALREADY_ASSOCIATED
            target[image.id] = current
            continue

        if expected is None:
            row.result, row.cause = "BLOCKED", NO_MAPPING
            continue
        row.global_product_presentation_id = str(expected)
        owner = presentations.get(expected)
        if owner is None:
            row.result, row.cause = "BLOCKED", PRESENTATION_MISSING
            continue
        if owner != image.global_product_id:
            row.result, row.cause = "BLOCKED", PRESENTATION_OF_OTHER_PRODUCT
            continue
        product_in_source = mapping.product_by_asset.get(image.id)
        uri_in_source = mapping.storage_uri_by_asset.get(image.id)
        if (product_in_source is not None and product_in_source != image.global_product_id) or (
            uri_in_source is not None and uri_in_source != image.storage_uri
        ):
            row.result, row.cause = "BLOCKED", SOURCES_CONTRADICT
            continue
        check = _storage_check(image, storage, bucket)
        row.storage_check = check
        storage_totals[check] += 1
        if check != "OK":
            row.result, row.cause = "BLOCKED", check
            continue
        row.result = ASSOCIATE
        target[image.id] = expected

    # Principales por presentación, después de asociar (FR-024-50).
    by_presentation: dict[UUID, list[Any]] = defaultdict(list)
    for image in images:
        if image.id in target and image.status == "ACTIVE":
            by_presentation[target[image.id]].append(image)
    for image in images:
        if image.id in target and image.status != "ACTIVE":
            rows[image.id].is_primary_after = False
    for members in by_presentation.values():
        primaries = [image for image in members if image.is_primary]
        if len(members) == 1:
            chosen = members[0]
        elif len(primaries) == 1:
            chosen = primaries[0]
        else:
            for image in members:
                rows[image.id].result, rows[image.id].cause = "BLOCKED", INDETERMINATE_PRIMARY
            continue
        for image in members:
            rows[image.id].is_primary_after = image.id == chosen.id

    known = {image.id for image in images}
    unmatched = sorted(str(asset_id) for asset_id in mapping.presentation_by_asset if asset_id not in known)
    ordered = [rows[image.id] for image in images]
    return Plan(
        rows=ordered,
        blocking=[row for row in ordered if row.result == "BLOCKED"],
        source_issues=dict(mapping.issues),
        unmatched_mapping=unmatched,
        storage_totals=dict(sorted(storage_totals.items())),
    )


def _storage_check(image: Any, storage: AssetStorage | None, bucket: str) -> str:
    """Solo metadatos (`HEAD`): el objeto existe y su metadata `sha256` coincide con la clave (FR-024-51).

    Aplica también a las imágenes `INACTIVE`: toda imagen debe tener su objeto en SIO con clave por SHA-256.
    """
    parsed = urlparse(image.storage_uri or "")
    key = parsed.path.lstrip("/")
    in_sio = parsed.scheme == "s3" and parsed.netloc == bucket and key.startswith("assets/")
    sha = sha_from_key(key) if in_sio and image.mime_type in ALLOWED_IMAGE_TYPES else None
    if sha is None:
        return NOT_SHA_KEY
    if storage is None:
        return STORAGE_UNAVAILABLE
    try:
        info = storage.head(key)
    except AssetStorageUnavailableError:
        return STORAGE_UNAVAILABLE
    if info is None:
        return OBJECT_MISSING
    if info.metadata.get("sha256") != sha:
        return SHA_MISMATCH
    return "OK"


# ------------------------------------------------------------------ base de datos


def _images(session) -> list[Any]:
    from sqlalchemy import select

    from product_catalog_service.infrastructure.models import ProductAssetModel

    return list(
        session.scalars(
            select(ProductAssetModel)
            .where(ProductAssetModel.asset_type == "IMAGE")
            .order_by(ProductAssetModel.global_product_id, ProductAssetModel.id)
        )
    )


def _presentations(session, ids: Iterable[UUID]) -> dict[UUID, UUID]:
    from sqlalchemy import select

    from product_catalog_service.infrastructure.models import GlobalProductPresentationModel

    ids = list(set(ids))
    if not ids:
        return {}
    model = GlobalProductPresentationModel
    return dict(session.execute(select(model.id, model.global_product_id).where(model.id.in_(ids))).all())


COUNT_QUERIES = {
    "images_total": "SELECT count(*) FROM product_assets WHERE asset_type = 'IMAGE'",
    "images_active": "SELECT count(*) FROM product_assets WHERE asset_type = 'IMAGE' AND status = 'ACTIVE'",
    "images_primary_active": (
        "SELECT count(*) FROM product_assets WHERE asset_type = 'IMAGE' AND status = 'ACTIVE' AND is_primary"
    ),
    "images_without_presentation": (
        "SELECT count(*) FROM product_assets WHERE asset_type = 'IMAGE' AND global_product_presentation_id IS NULL"
    ),
    "presentations_with_primary_image": (
        "SELECT count(DISTINCT global_product_presentation_id) FROM product_assets "
        "WHERE asset_type = 'IMAGE' AND status = 'ACTIVE' AND is_primary"
    ),
    "presentations_with_two_or_more_primaries": (
        "SELECT count(*) FROM (SELECT global_product_presentation_id FROM product_assets "
        "WHERE asset_type = 'IMAGE' AND status = 'ACTIVE' AND is_primary AND global_product_presentation_id IS NOT NULL "
        "GROUP BY global_product_presentation_id HAVING count(*) > 1) AS duplicated"
    ),
    "images_with_presentation_of_other_product": (
        "SELECT count(*) FROM product_assets a JOIN global_product_presentations p "
        "ON p.id = a.global_product_presentation_id WHERE a.global_product_id <> p.global_product_id"
    ),
    "non_image_assets": "SELECT count(*) FROM product_assets WHERE asset_type <> 'IMAGE'",
}


def counts(session) -> dict[str, int]:
    """Conteos de solo lectura; las mismas consultas van en el reporte para repetirlas (FR-024-52b)."""
    from sqlalchemy import text

    return {name: int(session.execute(text(query)).scalar_one()) for name, query in COUNT_QUERIES.items()}


def apply(session, mapping: Mapping, storage: AssetStorage | None, bucket: str, *, run_id: str) -> Plan:
    """Aplica el relleno en la transacción de `session` (todo o nada). Lanza `MigrationBlocked` sin cambios."""
    from sqlalchemy import select

    from product_catalog_service.application import audit_events as audit
    from product_catalog_service.application import lifecycle
    from product_catalog_service.infrastructure.models import ProductAssetModel

    images = list(
        session.scalars(
            select(ProductAssetModel)
            .where(ProductAssetModel.asset_type == "IMAGE")
            .order_by(ProductAssetModel.global_product_id, ProductAssetModel.id)
            .with_for_update()
        )
    )
    targets = set(mapping.presentation_by_asset.values()) | {
        image.global_product_presentation_id for image in images if image.global_product_presentation_id
    }
    plan = build_plan(images, _presentations(session, targets), mapping, storage, bucket)
    if not plan.ok:
        session.rollback()
        raise MigrationBlocked(plan)

    by_id = {str(image.id): image for image in images}
    changed = []
    for row in plan.rows:
        image = by_id[row.asset_id]
        moves = row.is_primary_after is not None and row.is_primary_after != image.is_primary
        if row.result == ASSOCIATE or moves:
            audit.remember(session, image)
            changed.append((image, row))
    # Orden que respeta los índices únicos parciales en cada `flush`: 1) se desmarcan los principales que dejan
    # de serlo; 2) se asocian; 3) se marcan los nuevos principales (FR-024-50).
    for image, row in changed:
        if row.is_primary_after is False and image.is_primary:
            image.is_primary = False
    session.flush()
    for image, row in changed:
        if row.result == ASSOCIATE:
            image.global_product_presentation_id = UUID(row.global_product_presentation_id)
    session.flush()
    for image, row in changed:
        if row.is_primary_after and not image.is_primary:
            image.is_primary = True
    for image, _row in changed:
        lifecycle.stamp_update(image, ACTOR_SUBJECT)
        audit.track_update(session, image, action=audit.UPDATE_PRODUCT_ASSET, entity_type="ProductAsset",
                           reason=f"Spec 024: imagen asociada a su presentación (ejecución {run_id}).")
    session.commit()
    return plan


def verify_result(session, mapping: Mapping | None, storage: AssetStorage | None, bucket: str) -> dict:
    """Verificación de solo lectura después del relleno (FR-024-50, FR-024-51; historia 5, escenario 4)."""
    images = _images(session)
    errors: list[dict] = []
    storage_totals: Counter[str] = Counter()
    for image in images:
        if image.global_product_presentation_id is None:
            errors.append({"asset_id": str(image.id), "cause": "WITHOUT_PRESENTATION"})
            continue
        expected = mapping.presentation_by_asset.get(image.id) if mapping else None
        if expected is not None and expected != image.global_product_presentation_id:
            errors.append({"asset_id": str(image.id), "cause": ASSOCIATED_TO_OTHER})
        check = _storage_check(image, storage, bucket)
        storage_totals[check] += 1
        if check != "OK":
            errors.append({"asset_id": str(image.id), "cause": check})
    active = [image for image in images if image.status == "ACTIVE"]
    presentations = {image.global_product_presentation_id for image in active}
    primaries = Counter(image.global_product_presentation_id for image in active if image.is_primary)
    without_primary = sorted(str(p) for p in presentations if p is not None and primaries[p] == 0)
    for presentation_id in without_primary:
        errors.append({"presentation_id": presentation_id, "cause": "PRESENTATION_WITHOUT_PRIMARY"})
    db_counts = counts(session)
    for name in ("images_without_presentation", "presentations_with_two_or_more_primaries",
                 "images_with_presentation_of_other_product"):
        if db_counts[name]:
            errors.append({"check": name, "cause": "COUNT_NOT_ZERO", "value": db_counts[name]})
    return {"errors": errors, "storage_totals": dict(sorted(storage_totals.items())), "counts": db_counts}


# ------------------------------------------------------------------ reporte


def report(mode: str, run_id: str, mapping: Mapping, plan: Plan | None, before: dict, after: dict | None,
           verification: dict | None = None) -> dict:
    """Evidencia de la ejecución: solo ids, conteos y causas (FR-024-52b)."""
    rows = [asdict(row) for row in plan.rows] if plan else []
    promoted = [row for row in rows if row["is_primary_after"] and not row["is_primary_before"]]
    return {
        "run_id": run_id,
        "mode": mode,
        "source": mapping.source,
        "ok": (plan.ok if plan else True) and not (verification or {}).get("errors"),
        "counts_before": before,
        "counts_after": after,
        "summary": {
            "images": len(rows),
            "results": dict(sorted(Counter(row["result"] for row in rows).items())),
            "causes": dict(sorted(Counter(row["cause"] for row in rows if row["cause"]).items())),
            "primary_after": sum(1 for row in rows if row["is_primary_after"]),
            "promoted_to_primary": len(promoted),
            "storage_checks": plan.storage_totals if plan else {},
            "source_issues": dict(sorted(Counter(mapping.issues.values()).items())),
            "mapping_rows_without_image": len(plan.unmatched_mapping) if plan else 0,
        },
        "source_issues": mapping.issues,
        "mapping_rows_without_image": plan.unmatched_mapping if plan else [],
        "verification": verification,
        "repeatable_checks_sql": COUNT_QUERIES,
        "images": rows,
    }


def write_report(data: dict, report_dir: Path) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    stem = f"spec024-imagenes-{data['run_id']}-{data['mode']}"
    json_path, csv_path = report_dir / f"{stem}.json", report_dir / f"{stem}.csv"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        fields = list(ImageRow.__dataclass_fields__)
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(data["images"])
    return json_path, csv_path


# ------------------------------------------------------------------ CLI


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - solo en ejecución real autorizada
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", choices=["plan", "apply", "verify"], nargs="?", default="plan")
    parser.add_argument("--gold", type=Path)
    parser.add_argument("--sio-ids", type=Path)
    parser.add_argument("--mapping", type=Path, help="Correspondencia revisada: asset_id,global_product_presentation_id")
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--expected-images", type=int, help="Se detiene si la base tiene otra cantidad de imágenes.")
    parser.add_argument("--confirm-apply", action="store_true", help="Obligatorio en apply (autorización humana).")
    args = parser.parse_args(argv)

    if args.mapping:
        mapping = mapping_from_file(args.mapping)
    elif args.gold and args.sio_ids:
        mapping = mapping_from_gold(args.gold, args.sio_ids)
    else:
        parser.error("Indique --gold y --sio-ids, o --mapping.")
    if args.mode == "apply" and not args.confirm_apply:
        print("apply exige --confirm-apply, un respaldo verificado y una simulación (plan) sin casos.", file=sys.stderr)
        return 2

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from product_catalog_service.audit_context import AuditActor, reset_actor, set_actor
    from product_catalog_service.config import load_settings
    from product_catalog_service.infrastructure.s3_asset_storage import S3AssetStorage

    settings = load_settings()
    storage = S3AssetStorage.from_settings(settings)
    bucket = settings.asset_storage_bucket
    read_only = {"options": "-c default_transaction_read_only=on"} if args.mode != "apply" else {}
    engine = create_engine(settings.database_url, connect_args=read_only)
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    try:
        with Session(engine, expire_on_commit=False) as session:
            before = counts(session)
            if args.expected_images is not None and before["images_total"] != args.expected_images:
                print(f"La base tiene {before['images_total']} imágenes y se esperaban {args.expected_images}: "
                      "no se continúa (FR-024-53).", file=sys.stderr)
                return 3
            if args.mode == "verify":
                verification = verify_result(session, mapping, storage, bucket)
                data = report("verify", run_id, mapping, None, before, None, verification)
            elif args.mode == "plan":
                images = _images(session)
                targets = set(mapping.presentation_by_asset.values()) | {
                    i.global_product_presentation_id for i in images if i.global_product_presentation_id}
                plan = build_plan(images, _presentations(session, targets), mapping, storage, bucket)
                data = report("plan", run_id, mapping, plan, before, None)
            else:
                token = set_actor(AuditActor(ACTOR_SUBJECT, ACTOR_USERNAME))
                try:
                    plan = apply(session, mapping, storage, bucket, run_id=run_id)
                    data = report("apply", run_id, mapping, plan, before, counts(session))
                except MigrationBlocked as blocked:
                    data = report("apply-blocked", run_id, mapping, blocked.plan, before, counts(session))
                finally:
                    reset_actor(token)
    finally:
        engine.dispose()

    json_path, csv_path = write_report(data, args.report_dir)
    print(json.dumps({"ok": data["ok"], "mode": data["mode"], "summary": data["summary"],
                      "verification_errors": len((data.get("verification") or {}).get("errors") or []),
                      "report": [str(json_path), str(csv_path)]}, ensure_ascii=False, indent=2))
    return 0 if data["ok"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
