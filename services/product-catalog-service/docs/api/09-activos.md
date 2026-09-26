# Activos digitales

Un activo es una **referencia** a un archivo del producto guardado fuera de este servicio: una
imagen, una ficha técnica, un manual o un certificado. El servicio guarda solo la URI y los
metadatos; nunca recibe ni almacena el archivo.

Recurso de permiso: `products`.

| Ruta | Permiso |
| --- | --- |
| `GET /api/v1/products/{id}/assets` (filtros `status`, `asset_type`) | `read` |
| `POST /api/v1/products/{id}/assets` | `update` |
| `PUT /api/v1/products/{id}/assets/{asset_id}` | `update` |
| `POST /api/v1/products/{id}/assets/{asset_id}/set-primary` | `update` |
| `POST /api/v1/products/{id}/assets/{asset_id}/deactivate` · `/reactivate` | `deactivate` |

---

## POST — Registrar un activo

| Campo | Obligatorio | Regla |
| --- | --- | --- |
| `asset_type` | Sí | `IMAGE`, `TECHNICAL_SHEET`, `MANUAL`, `CERTIFICATE`, `OTHER` |
| `file_name` | Sí | Máx. 255 |
| `storage_uri` | Sí | URI absoluto (`s3://…`, `https://…`); con esquemas de red debe incluir el servidor |
| `mime_type` | No | Formato `tipo/subtipo` (`image/png`) |
| `is_primary` | No (`false`) | Principal de su tipo |

```http
POST /api/v1/products/<id>/assets
{
  "asset_type": "TECHNICAL_SHEET",
  "file_name": "ficha-fluorouracilo.pdf",
  "storage_uri": "s3://sio-assets/productos/fluorouracilo/ficha.pdf",
  "mime_type": "application/pdf",
  "is_primary": true
}
```

```json
{
  "id": "a1…",
  "global_product_id": "<id>",
  "asset_type": "TECHNICAL_SHEET",
  "file_name": "ficha-fluorouracilo.pdf",
  "storage_uri": "s3://sio-assets/productos/fluorouracilo/ficha.pdf",
  "mime_type": "application/pdf",
  "is_primary": true,
  "status": "ACTIVE",
  "version": 1,
  "…": "…"
}
```

| Error | Cuándo |
| --- | --- |
| `422 INVALID_STORAGE_URI` | Ruta relativa (`productos/a.png`) o sin servidor (`https:///a.png`) |
| `422 VALIDATION_ERROR` | `mime_type` mal formado, tipo desconocido o contenido del archivo en el cuerpo |

## PUT — Modificar metadatos

```json
{ "file_name": "ficha-v2.pdf", "storage_uri": "s3://sio-assets/productos/fluorouracilo/ficha-v2.pdf", "mime_type": "application/pdf", "version": 1 }
```

`asset_type` e `is_primary` no se cambian aquí (el principal se cambia con `set-primary`).

## POST `…/set-primary`

Cuerpo `{ "version": n }`. Hay como máximo un principal activo **por tipo**: una imagen principal y un
manual principal pueden coexistir.

## POST `…/deactivate` · `/reactivate`

Cuerpo `{ "version": n }`. Inactivar oculta el activo del detalle vigente del producto, pero **no
borra el archivo** del almacenamiento externo.
