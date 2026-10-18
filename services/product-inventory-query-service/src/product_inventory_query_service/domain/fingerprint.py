"""Huella de los filtros normalizados (FR-022-148; `contracts/cursor.md` §2; research R-09).

SHA-256 (truncado a 16 bytes, en base64url) de un JSON canónico con claves ordenadas. Incluye el endpoint, la
empresa, el alcance y todos los filtros con sus valores por defecto ya aplicados; **no** incluye `sort`,
`page_size` ni `cursor`, que el cursor guarda aparte para informar el motivo exacto de un reinicio.

Normalización sin cambiar la semántica de la búsqueda:

- `search`: NFC, sin espacios al inicio ni al final, espacios internos colapsados y `casefold`, porque CR
  compara sin distinguir mayúsculas (`ILIKE`); los acentos **no** se eliminan porque CR sí los distingue.
- `internal_code` y `sku`: recortados y en minúsculas (CR los compara sin distinguir mayúsculas).
- `barcode` e `identifier`: recortados (PC los compara exactos).
- Listas sin duplicados y ordenadas; UUID en minúsculas; `scope = COMPANY` se guarda como tal.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import unicodedata

from product_inventory_query_service.domain.query_spec import QuerySpec

_SPACES = re.compile(r"\s+")


def normalize_search(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _SPACES.sub(" ", unicodedata.normalize("NFC", value)).strip().casefold()
    return normalized or None


def _lower(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip().lower() or None


def _strip(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


def _ids(values) -> list[str]:
    return sorted({str(value).lower() for value in values})


def canonical(spec: QuerySpec) -> dict:
    return {
        "ep": spec.endpoint.value,
        "cid": str(spec.company_id).lower(),
        "scope": "COMPANY" if spec.branch_ids is None else _ids(spec.branch_ids),
        "search": normalize_search(spec.search),
        "internal_code": _lower(spec.internal_code),
        "sku": _lower(spec.sku),
        "barcode": _strip(spec.barcode),
        "identifier": _strip(spec.identifier),
        "brand_ids": _ids(spec.brand_ids),
        "category_ids": _ids(spec.category_ids),
        "include_descendants": bool(spec.include_descendants),
        "status": spec.status,
        "product_type": _strip(spec.product_type),
        "has_image": spec.has_image,
        "stock_state": spec.stock_state,
        "minimum_state": spec.minimum_state,
        "price_list_id": str(spec.price_list_id).lower() if spec.price_list_id else None,
    }


def fingerprint(spec: QuerySpec) -> str:
    text = json.dumps(canonical(spec), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(text.encode("utf-8")).digest()[:16]
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
