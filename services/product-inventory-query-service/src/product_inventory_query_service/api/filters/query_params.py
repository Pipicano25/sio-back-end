"""Análisis estricto de los parámetros de los listados (FR-022-34, FR-022-61, FR-022-148; T085).

Recibe los pares `(nombre, valor)` de la URL (los filtros repetibles pueden venir varias veces) y devuelve una
`QuerySpec`. Un parámetro desconocido, un valor inválido o un filtro que no corresponde al endpoint responde `422`:
nada se ignora en silencio.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from product_inventory_query_service.application.exceptions import ValidationFailedError
from product_inventory_query_service.domain.query_spec import (
    MAX_CURSOR_LENGTH,
    MAX_PAGE_SIZE,
    SORT_KEYS,
    Endpoint,
    QuerySpec,
    Sort,
)

REPEATABLE = {"branch_id", "brand_id", "category_id"}
SCOPE_PARAMETERS = ("branch_id", "scope")
"""Alcance de sucursales por consulta; en las rutas `/branches/{branch_id}/…` la sucursal viene en la ruta."""
ENDPOINT_ONLY = {
    "price_list_id": {Endpoint.PRODUCT_OVERVIEWS},
    "minimum_state": {Endpoint.INVENTORY_OVERVIEWS},
    "stock_state": {Endpoint.PRODUCT_OVERVIEWS, Endpoint.INVENTORY_OVERVIEWS},
}


def _blank(value):
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return value


class ListingParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    branch_id: list[UUID] = Field(default_factory=list, max_length=100)
    scope: Literal["COMPANY"] | None = None
    search: str | None = Field(default=None, max_length=200)
    internal_code: str | None = Field(default=None, max_length=60)
    sku: str | None = Field(default=None, max_length=80)
    barcode: str | None = Field(default=None, max_length=120)
    identifier: str | None = Field(default=None, max_length=120)
    brand_id: list[UUID] = Field(default_factory=list, max_length=100)
    category_id: list[UUID] = Field(default_factory=list, max_length=100)
    include_descendants: bool = False
    status: Literal["ACTIVE", "INACTIVE", "ALL"] = "ACTIVE"
    product_type: str | None = Field(default=None, max_length=20)
    has_image: bool | None = None
    stock_state: Literal["IN_STOCK", "OUT_OF_STOCK"] | None = None
    minimum_state: Literal["NO_POLICY", "BELOW_MINIMUM", "AT_MINIMUM", "ABOVE_MINIMUM"] | None = None
    price_list_id: UUID | None = None
    sort: str | None = None
    page_size: int = Field(default=20, ge=1, le=MAX_PAGE_SIZE)
    cursor: str | None = Field(default=None, max_length=MAX_CURSOR_LENGTH)

    @field_validator("search", "internal_code", "sku", "barcode", "identifier", "product_type", "sort", "cursor",
                     mode="before")
    @classmethod
    def _strip(cls, value):
        return _blank(value)

    @field_validator("sort")
    @classmethod
    def _sort(cls, value: str | None) -> str | None:
        if value is None:
            return None
        key, _, direction = value.partition(":")
        if key not in SORT_KEYS or direction not in ("", "asc", "desc"):
            raise ValueError("`sort` admite display_name, internal_code o created_at, con :asc o :desc.")
        return value

    @model_validator(mode="after")
    def _scope(self) -> "ListingParams":
        if self.scope is not None and self.branch_id:
            raise ValueError("Use `branch_id` o `scope=COMPANY`, no ambos.")
        return self


def _reject_scope_parameters(pairs: list[tuple[str, str]]) -> None:
    """Con la sucursal en la ruta, `branch_id` y `scope` por consulta son ambiguos: `422`, nunca se combinan."""
    errors = [
        {"field": name, "message": "La sucursal ya está en la ruta: este parámetro no se admite.",
         "code": "UNKNOWN_FIELD"}
        for name in dict.fromkeys(name for name, _ in pairs if name in SCOPE_PARAMETERS)
    ]
    if errors:
        raise ValidationFailedError("La solicitud contiene parámetros inválidos.", errors=errors)


def parse_query(endpoint: Endpoint, company_id: UUID, pairs: Iterable[tuple[str, str]], *,
                branch_id: UUID | None = None) -> QuerySpec:
    """`branch_id` = sucursal de la ruta `/branches/{branch_id}/…`: equivale a un único `branch_id` por consulta."""
    pairs = list(pairs)
    if branch_id is not None:
        _reject_scope_parameters(pairs)
        pairs.append(("branch_id", str(branch_id)))
    values: dict[str, object] = {}
    for name, value in pairs:
        if name in REPEATABLE:
            values.setdefault(name, []).append(value)
        elif name in values:
            raise ValidationFailedError(
                "La solicitud contiene parámetros inválidos.",
                errors=[{"field": name, "message": "El parámetro no se puede repetir.", "code": "INVALID_FORMAT"}],
            )
        else:
            values[name] = value

    errors = [
        {"field": name, "message": "El parámetro no corresponde a este endpoint.", "code": "UNKNOWN_FIELD"}
        for name, endpoints in ENDPOINT_ONLY.items()
        if name in values and endpoint not in endpoints
    ]
    if errors:
        raise ValidationFailedError("La solicitud contiene parámetros inválidos.", errors=errors)

    try:
        params = ListingParams.model_validate(values)
    except ValidationError as exc:
        raise ValidationFailedError(
            "La solicitud contiene parámetros inválidos.",
            errors=[
                {
                    "field": ".".join(str(part) for part in error.get("loc", ())) or "query",
                    "message": str(error.get("msg", "")).removeprefix("Value error, "),
                    "code": "UNKNOWN_FIELD" if error.get("type") == "extra_forbidden" else "INVALID_FORMAT",
                }
                for error in exc.errors()
            ],
        ) from None

    sort = None
    if params.sort is not None:
        key, _, direction = params.sort.partition(":")
        sort = Sort(key, direction == "desc")

    return QuerySpec(
        endpoint=endpoint,
        company_id=company_id,
        branch_ids=tuple(dict.fromkeys(params.branch_id)) or None,
        search=params.search,
        internal_code=params.internal_code,
        sku=params.sku,
        barcode=params.barcode,
        identifier=params.identifier,
        brand_ids=tuple(sorted(set(params.brand_id), key=str)),
        category_ids=tuple(sorted(set(params.category_id), key=str)),
        include_descendants=params.include_descendants,
        status=params.status,
        product_type=params.product_type,
        has_image=params.has_image,
        stock_state=params.stock_state,
        minimum_state=params.minimum_state,
        price_list_id=params.price_list_id,
        sort=sort,
        page_size=params.page_size,
        cursor=params.cursor,
    )


# --------------------------------------------------------------------------- inventory-summary

SUMMARY_PARAMETERS = {"branch_id", "scope"}


class SummaryParams(BaseModel):
    """`inventory-summary` solo admite el alcance de sucursales: ni filtros de producto ni `cursor` (contrato §4.4)."""

    model_config = ConfigDict(extra="forbid")

    branch_id: list[UUID] = Field(default_factory=list, max_length=100)
    scope: Literal["COMPANY"] | None = None

    @model_validator(mode="after")
    def _scope(self) -> "SummaryParams":
        if self.scope is not None and self.branch_id:
            raise ValueError("Use `branch_id` o `scope=COMPANY`, no ambos.")
        return self


def parse_summary_query(pairs: Iterable[tuple[str, str]], *, branch_id: UUID | None = None) -> list[UUID] | None:
    """Devuelve los `branch_id` pedidos, o `None` para `scope = COMPANY` (por defecto).

    `branch_id` = sucursal de la ruta `/branches/{branch_id}/inventory-summary`.
    """
    pairs = list(pairs)
    if branch_id is not None:
        _reject_scope_parameters(pairs)
        pairs.append(("branch_id", str(branch_id)))
    values: dict[str, object] = {}
    for name, value in pairs:
        if name == "branch_id":
            values.setdefault(name, []).append(value)
        elif name in values:
            raise ValidationFailedError(
                "La solicitud contiene parámetros inválidos.",
                errors=[{"field": name, "message": "El parámetro no se puede repetir.", "code": "INVALID_FORMAT"}],
            )
        else:
            values[name] = value
    try:
        params = SummaryParams.model_validate(values)
    except ValidationError as exc:
        raise ValidationFailedError(
            "La solicitud contiene parámetros inválidos.",
            errors=[
                {
                    "field": ".".join(str(part) for part in error.get("loc", ())) or "query",
                    "message": str(error.get("msg", "")).removeprefix("Value error, "),
                    "code": "UNKNOWN_FIELD" if error.get("type") == "extra_forbidden" else "INVALID_FORMAT",
                }
                for error in exc.errors()
            ],
        ) from None
    return list(dict.fromkeys(params.branch_id)) or None


# --------------------------------------------------------------------------- OpenAPI

PARAMETER_DESCRIPTIONS = {
    "branch_id": "Sucursal de la empresa (repetible). Excluyente con `scope`.",
    "scope": "`COMPANY`: todas las sucursales activas de la empresa (por defecto).",
    "search": "Texto en el nombre, `internal_code`, `reference_code` o SKU de presentación (lo evalúa CR).",
    "internal_code": "Código interno exacto (sin distinguir mayúsculas).",
    "sku": "SKU de presentación exacto.",
    "barcode": "Código de barras exacto (Product Catalog).",
    "identifier": "Identificador global exacto (Product Catalog).",
    "brand_id": "Marca (repetible, con O).",
    "category_id": "Categoría (repetible, con O).",
    "include_descendants": "Incluye las subcategorías de `category_id`.",
    "status": "Estado del producto empresarial; por defecto `ACTIVE`.",
    "product_type": "Tipo de producto de Product Catalog.",
    "has_image": "Con o sin imagen principal apta.",
    "stock_state": "`IN_STOCK` u `OUT_OF_STOCK`; exige `perm:product-inventory-query:stock:read`.",
    "minimum_state": "Estado frente al mínimo en al menos una sucursal; exige `perm:inventory:product-policies:read`.",
    "price_list_id": "Lista de precios; sin ella, la predeterminada que aplique Commercial Relationship.",
    "sort": "`display_name`, `internal_code` o `created_at`, con `:asc` o `:desc`. Si es explícito, conduce CR.",
    "page_size": "De 1 a 20; por defecto 20.",
    "cursor": "Cursor opaco de la respuesta anterior (`next_cursor`).",
}


def _parameter(name: str, schema: dict) -> dict:
    schema = {key: value for key, value in schema.items() if key not in {"title", "default"}}
    parameter = {"name": name, "in": "query", "required": False, "schema": schema,
                 "description": PARAMETER_DESCRIPTIONS[name]}
    if name in REPEATABLE:
        parameter.update({"style": "form", "explode": True})
    return parameter


def openapi_parameters(endpoint: Endpoint | None, *, branch_in_path: bool = False) -> list[dict]:
    """Parámetros de consulta de un endpoint para OpenAPI (`None` = `inventory-summary`).

    Con `branch_in_path`, sin `branch_id` ni `scope`: la sucursal es el parámetro de ruta.
    """
    if endpoint is None:
        properties = SummaryParams.model_json_schema()["properties"]
        return [] if branch_in_path else [_parameter(name, properties[name]) for name in SCOPE_PARAMETERS]
    properties = ListingParams.model_json_schema()["properties"]
    return [
        _parameter(name, schema)
        for name, schema in properties.items()
        if (name not in ENDPOINT_ONLY or endpoint in ENDPOINT_ONLY[name])
        and not (branch_in_path and name in SCOPE_PARAMETERS)
    ]
