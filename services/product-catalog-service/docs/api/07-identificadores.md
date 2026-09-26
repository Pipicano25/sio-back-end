# Identificadores (códigos de barras)

Un identificador es un código externo del producto o de una de sus presentaciones. Un producto puede
tener varios.

| Tipo | Qué es | Unicidad |
| --- | --- | --- |
| `GTIN`, `EAN`, `UPC` | Familia GS1: numéricos de 8, 12, 13 o 14 dígitos con dígito de control | Única en **todo** el catálogo, entre los tres tipos y contando los inactivos |
| `BARCODE` | Código escaneable genérico que **no** es GS1 | Único en todo el catálogo, contando los inactivos |
| `OTHER` | Cualquier otra referencia | Única dentro del producto |

Recurso de permiso: `products`.

| Ruta | Permiso |
| --- | --- |
| `GET /api/v1/products/{id}/identifiers` (filtro `status`) | `read` |
| `POST /api/v1/products/{id}/identifiers` | `update` |
| `POST /api/v1/products/{id}/identifiers/{identifier_id}/set-primary` | `update` |
| `POST /api/v1/products/{id}/identifiers/{identifier_id}/deactivate` · `/reactivate` | `deactivate` |

No existe `PUT`: un identificador no se modifica. Para corregirlo se inactiva y se registra otro.
Para buscar por código, ver `GET /products/by-identifier/{value}` en [04-productos.md](04-productos.md).

---

## Cómo se normaliza y compara un código

1. Se quitan espacios y guiones: `"0-36000-29145-2"` → `"036000291452"`. Nunca se convierte a
   número, así que los ceros iniciales se conservan.
2. Para la familia GTIN se calcula la **forma canónica** rellenando con ceros hasta 14 dígitos:

| Registrado como | `value` | `canonical_value` |
| --- | --- | --- |
| `UPC` | `036000291452` | `00036000291452` |
| `EAN` | `0036000291452` | `00036000291452` |
| `GTIN` | `00036000291452` | `00036000291452` |

Los tres son **el mismo código** y solo puede existir uno.

---

## POST `/api/v1/products/{id}/identifiers` — Registrar

| Campo | Obligatorio | Regla |
| --- | --- | --- |
| `identifier_type` | Sí | `GTIN`, `EAN`, `UPC`, `BARCODE`, `OTHER` |
| `value` | Sí | Máx. 100 tras normalizar |
| `global_product_presentation_id` | No | Presentación **del mismo producto** |
| `is_primary` | No (`false`) | Principal de su tipo en su contexto |

```http
POST /api/v1/products/<id>/identifiers
{
  "identifier_type": "EAN",
  "value": "7702057781194",
  "global_product_presentation_id": "<id CAJA_X_100>",
  "is_primary": true
}
```

```json
{
  "id": "i1…",
  "global_product_id": "<id>",
  "global_product_presentation_id": "<id CAJA_X_100>",
  "identifier_type": "EAN",
  "value": "7702057781194",
  "canonical_value": "07702057781194",
  "is_primary": true,
  "status": "ACTIVE",
  "version": 1,
  "…": "…"
}
```

| Error | Cuándo |
| --- | --- |
| `422 INVALID_GTIN_FORMAT` | `GTIN`/`EAN`/`UPC` no numérico o de longitud distinta de 8, 12, 13 o 14 |
| `422 INVALID_CHECK_DIGIT` | Dígito de control GS1 incorrecto |
| `422 BARCODE_IS_GTIN` | Se envió como `BARCODE` un código que cumple el estándar GS1: regístrelo como `EAN`/`UPC`/`GTIN` |
| `422 PRESENTATION_OF_OTHER_PRODUCT` | La presentación es de otro producto |
| `409 IDENTIFIER_COLLISION` | El código ya existe (ver abajo) |

### Colisión

```json
{
  "status": 409,
  "code": "PRODUCT_CATALOG.IDENTIFIER_COLLISION",
  "detail": "El código 7707270363844 ya identifica otro registro del catálogo; revise la inconsistencia.",
  "conflict": {
    "global_product_id": "<producto que ya lo tiene>",
    "global_product_presentation_id": null,
    "identifier_id": "i7…",
    "identifier_type": "EAN",
    "status": "ACTIVE"
  },
  "…": "…"
}
```

El servicio **no resuelve** la colisión (no cambia el tipo, no inactiva el otro, no reasigna): la
revisa una persona con los datos de `conflict`.

## POST `…/set-primary`

```http
POST /api/v1/products/<id>/identifiers/i2…/set-primary
{ "version": 1 }
```

Hay como máximo un principal por tipo y por **contexto**: el producto (sin presentación) y cada
presentación son contextos distintos. Marcar uno desmarca el anterior del mismo tipo y contexto.

## POST `…/deactivate` · `/reactivate`

Cuerpo `{ "version": n }`. Inactivar **no libera** el código: sigue sin poder usarse en otro producto.
