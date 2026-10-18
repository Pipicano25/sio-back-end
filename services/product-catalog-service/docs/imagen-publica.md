# Imagen pública por URL directa (spec 022)

Guía de uso de `GET /api/v1/public/product-images?ref=<ref>`. Su comportamiento lo validan
`tests/api/test_public_product_images.py`, `tests/unit/test_image_ref.py` y `tests/unit/test_image_magic_bytes.py`.

> Esta ruta no exige token, así que no aparece en la matriz de usuarios y permisos de `docs/ejemplo/`: la
> controla la referencia firmada, no un permiso.

## Cómo la obtiene el frontend

1. Consulta los productos con un servicio autorizado (el servicio de consultas consolidadas o
   `POST /api/v1/products/summaries/batch-lookup`, que exige `perm:product-catalog:products:read`).
2. Cada producto trae `has_image` e `image_url`. Si `has_image` es `false`, `image_url` es `null`.
3. Muestra la imagen con `<img src={image_url}>`: el navegador la pide **sin** token.

## Qué responde

| Situación | Respuesta |
|---|---|
| Referencia válida de una imagen `ACTIVE` y apta | `200` con la imagen, `Content-Type` (JPEG, PNG o WebP), `Content-Length`, `ETag` (SHA-256 del contenido), `Cache-Control: public, max-age=31536000, immutable`, `X-Content-Type-Options: nosniff`, `Content-Disposition: inline` y `Cross-Origin-Resource-Policy: cross-origin` |
| La misma petición con `If-None-Match` igual al `ETag` | `304` sin cuerpo, sin leer el almacenamiento |
| Referencia alterada, vencida por rotación, de otro tipo de activo, de un activo inactivo, sin `ref`, con otros parámetros, objeto inexistente o contenido que no corresponde a su tipo | El **mismo** `404` vacío |
| Almacenamiento de objetos no disponible | `503` vacío |

No hay redirecciones, listado ni búsqueda, y la respuesta nunca incluye bucket, clave, `storage_uri`, empresa ni
datos de auditoría. Cualquier otra ruta bajo `/api/v1/public/` exige token.

El log de acceso nunca registra la referencia: el filtro de `api/tracing.py` reemplaza el valor de `ref=` por
`[REDACTADO]` (FR-022-77; lo detectó la prueba de seguridad de la pila aislada y lo cubre
`tests/unit/test_access_log_redaction.py`).

## Qué es una imagen apta

Imagen `asset_type = IMAGE`, `status = ACTIVE`, de tipo JPEG, PNG o WebP, guardada en el almacenamiento de SIO
(`s3://<ASSET_STORAGE_BUCKET>/…`) con una clave que incluye el SHA-256 de su contenido. `has_image` exige además
que sea la imagen principal. SVG y referencias externas (`https://…`) nunca son aptas.

## La referencia

`ref` identifica **un** activo y **una** versión de su contenido: el id del activo y el prefijo del SHA-256,
firmados con HMAC-SHA256 (128 bits). No se puede adivinar ni derivar la de otro activo. Si la imagen cambia,
cambia la URL; si el activo se inactiva, la URL deja de servir.

## Configuración y rotación

| Variable | Uso |
|---|---|
| `PRODUCT_CATALOG_PUBLIC_BASE_URL` | URL pública base con la que se construye `image_url`; debe ser alcanzable por el navegador |
| `PRODUCT_IMAGE_REF_SECRET` | Secreto HMAC (al menos 32 bytes). Sin él, o sin la URL base, la ruta no existe y `image_url` es `null` |
| `PRODUCT_IMAGE_REF_SECRET_PREVIOUS` | Secreto saliente durante una rotación: las URL firmadas con él siguen sirviendo hasta que se retire |

Para rotar el secreto:

1. Copiar el actual a `PRODUCT_IMAGE_REF_SECRET_PREVIOUS` y poner el nuevo en `PRODUCT_IMAGE_REF_SECRET`.
2. Reiniciar el servicio. Las URL nuevas se firman con el secreto nuevo.
3. Retirar el anterior cuando ya no haga falta. Las URL firmadas con él dejan de servir, y los clientes obtienen
   las nuevas al consultar de nuevo.

## Verificación previa (obligatoria antes de habilitarla)

Antes de configurar el secreto en un entorno con datos reales, con autorización:

```bash
python -m product_catalog_service.tools.verify_image_assets --confirm-read-only > informe.json
```

La herramienta abre la base en solo lectura y, para cada imagen `ACTIVE`, comprueba que sea apta, que el objeto
exista y no esté vacío, que el SHA-256 de sus metadatos coincida y que sus primeros bytes correspondan a su tipo.
El informe solo tiene ids y resultados, nunca claves ni rutas internas. No modifica nada: las imágenes no aptas
quedan con `has_image = false`.
