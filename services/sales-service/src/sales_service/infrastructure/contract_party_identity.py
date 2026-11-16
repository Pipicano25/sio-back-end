"""Party Identity leído de sus vistas de contrato (spec 025, T044; D27).

Mismo puerto que `HTTPPartyDirectory`:

- `get_person` y `get_organization` leen `v1_person_identities` y `v1_organization_identities` por id (sin fila →
  `None`, el `404` de hoy). El nombre se arma igual que hoy (`_info`).
- `search` reproduce `GET /person-identities` y `GET /organization-identities` con `status=ACTIVE`: el texto se
  recorta y, si queda vacío, no filtra; `ILIKE '%texto%'` sobre los mismos campos; el mismo orden
  (personas: `last_name, first_name, id`; organizaciones: `legal_name, id`), `OFFSET/LIMIT` por página y el mismo
  `total_records`.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Engine

from sales_service.application.exceptions import PARTY_IDENTITY
from sales_service.application.ports import ORGANIZATION, IdentityInfo, IdentityPage
from sales_service.infrastructure.contract_support import ContractReader

_PERSON_COLUMNS = (
    "id, identification_type, identification_number, first_name, middle_name, last_name, second_last_name, status"
)
_ORGANIZATION_COLUMNS = "id, identification_type, identification_number, legal_name, trade_name, status"
_PERSON = f"SELECT {_PERSON_COLUMNS} FROM contract.v1_person_identities WHERE id = :id"
_ORGANIZATION = f"SELECT {_ORGANIZATION_COLUMNS} FROM contract.v1_organization_identities WHERE id = :id"

_SEARCH = {
    # tipo: (vista, columnas, campos de búsqueda, orden)
    "PERSON": (
        "contract.v1_person_identities",
        _PERSON_COLUMNS,
        ("identification_number", "first_name", "middle_name", "last_name", "second_last_name"),
        "last_name, first_name, id",
    ),
    ORGANIZATION: (
        "contract.v1_organization_identities",
        _ORGANIZATION_COLUMNS,
        ("identification_number", "legal_name", "trade_name"),
        "legal_name, id",
    ),
}


def _text(value: Any) -> str | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    return str(value)


def _info(row: dict[str, Any]) -> IdentityInfo:
    """Igual que `party_identity_directory._info`: organización → nombre comercial o razón social; persona →
    nombres y apellidos."""
    if "legal_name" in row:
        name = _text(row.get("trade_name")) or _text(row.get("legal_name"))
    else:
        parts = [_text(row.get(key)) for key in ("first_name", "middle_name", "last_name", "second_last_name")]
        name = " ".join(part.strip() for part in parts if part) or None
    return IdentityInfo(
        id=row["id"],
        identification_type=_text(row.get("identification_type")),
        identification_number=_text(row.get("identification_number")),
        name=name,
        status=_text(row.get("status")),
    )


class ContractPartyDirectory:
    def __init__(self, *, engine: Engine) -> None:
        self._reader = ContractReader(engine, PARTY_IDENTITY)

    def get_person(self, person_id: UUID) -> IdentityInfo | None:
        row = self._reader.one("person_identity", _PERSON, {"id": person_id})
        return None if row is None else _info(row)

    def get_organization(self, organization_id: UUID) -> IdentityInfo | None:
        row = self._reader.one("organization_identity", _ORGANIZATION, {"id": organization_id})
        return None if row is None else _info(row)

    def search(self, customer_kind: str, search: str | None, page: int, page_size: int) -> IdentityPage:
        operation = "identities_search"
        view, columns, fields, order = _SEARCH[ORGANIZATION if customer_kind == ORGANIZATION else "PERSON"]
        where = "status = 'ACTIVE'"
        params: dict[str, Any] = {"limit": page_size, "offset": (page - 1) * page_size}
        text = search.strip() if search and search.strip() else None
        if text:
            where += " AND (" + " OR ".join(f"{field} ILIKE :pattern" for field in fields) + ")"
            params["pattern"] = f"%{text}%"
        total = self._reader.one(operation, f"SELECT count(*) AS total FROM {view} WHERE {where}", params)
        rows = self._reader.rows(
            operation, f"SELECT {columns} FROM {view} WHERE {where} ORDER BY {order} LIMIT :limit OFFSET :offset", params
        )
        return IdentityPage(items=[_info(row) for row in rows], total_records=int(total["total"]) if total else 0)
