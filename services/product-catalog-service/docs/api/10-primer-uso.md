# Marca de primer uso

Cuando una empresa adopta un producto, su unidad base y la equivalencia física de sus presentaciones
pasan a tener historia en otros servicios (compras, ventas, inventario). La **marca de primer uso**
registra ese momento y desde entonces bloquea esos datos.

Contrato completo: `specs/002-product-catalog-service/contracts/first-use.md`.

| Ruta | Permiso | Quién la usa |
| --- | --- | --- |
| `POST /api/v1/products/{id}/first-use` | `first-use:register` | El servicio que adopta, con su cuenta de servicio |
| `POST /api/v1/products/{id}/first-use/manual` | `first-use:register-manual` | Un administrador (p. ej. productos migrados) |

No existe ninguna ruta para quitar la marca: es **irreversible**.

---

## POST `/api/v1/products/{id}/first-use` — Registrar por adopción

Cuerpo opcional:

```http
POST /api/v1/products/<id>/first-use
{ "global_product_presentation_id": "<id PAQUETE_X_21>" }
```

Respuesta `200`:

```json
{
  "global_product_id": "<id>",
  "product_first_used_at": "2026-09-25T15:04:05Z",
  "product_first_use_source": "ADOPTION",
  "global_product_presentation_id": "<id PAQUETE_X_21>",
  "presentation_first_used_at": "2026-09-25T15:04:05Z",
  "presentation_first_use_source": "ADOPTION"
}
```

Lógica:

| Situación | Resultado |
| --- | --- |
| Producto (y presentación) sin marca y elegibles | Se marcan; `200` |
| Se marca una presentación | También se marca su producto |
| Ya estaban marcados | `200` con la fecha original, sin cambios (idempotente) |
| Sin marca y el producto está incompleto o inactivo | `422 NOT_ELIGIBLE_FOR_FIRST_USE`, no se marca nada |
| La presentación es de otro producto | `422 PRESENTATION_OF_OTHER_PRODUCT` |

Se guarda la fecha, el `sub` de quien notificó y el origen (`ADOPTION`). No se guarda ningún dato de
la empresa que adopta.

## POST `/api/v1/products/{id}/first-use/manual` — Registro manual

Igual cuerpo y respuesta, con origen `MANUAL`. **No exige elegibilidad**: sirve para proteger
productos que ya se usaban antes de existir el catálogo.

## Qué bloquea la marca

| Operación | Sin marca | Con marca |
| --- | --- | --- |
| Cambiar `base_unit_id` del producto | Permitido | `422 BASE_UNIT_LOCKED_BY_FIRST_USE` |
| Cambiar empaque, `base_quantity` o contenido de la presentación | Permitido | `422 PRESENTATION_LOCKED_BY_FIRST_USE` |
| Cambiar nombres, descripción, orden, `is_base` | Permitido | Permitido |

Si un dato bloqueado está mal, la corrección es crear una presentación nueva e inactivar la
anterior. El cambio de unidad base de un producto marcado queda para una operación excepcional
futura.

## Obligación del servicio que adopta

```text
1. Consultar elegibilidad       POST /products/batch-lookup  y  /presentations/batch-lookup
2. Registrar el primer uso      POST /products/{id}/first-use
3. Solo si 2 respondió 200  →   confirmar la adopción en el servicio propio
```

Si el paso 2 falla (error, `5xx` o tiempo agotado), la adopción **se rechaza**. No se confirma sin
marca ni se deja la notificación para después. Reintentar es seguro porque la operación es
idempotente.
