# Parámetro `sequence_id`

[← Parámetros](README.md) · [← Índice](../index.md) · Servicios propietarios: [Sales](../servicios/sales.md) (ventas) y [Purchase](../servicios/purchase.md) (compras)

| Propiedad | Valor |
|---|---|
| Qué representa | Una **secuencia de numeración** de documentos comerciales de la empresa: define el prefijo, el separador, el consecutivo y la política de reinicio con los que se numeran las ventas (Sales) o las compras (Purchase) al confirmarse. Puede ser de una sucursal (`branch_id`) o de toda la empresa (`branch_id: null`) |
| Nombre en las rutas | `sequence_id` (`/companies/{company_id}/sale-sequences/{sequence_id}` y `/companies/{company_id}/purchase-sequences/{sequence_id}`) |
| Tipo | UUID (texto) |
| Obligatorio | Sí para consultar, modificar, desactivar o reactivar una secuencia |
| Ejemplo (ficticio) | `d9cd7378-6b8f-4e54-8171-39db2f8ebfe1` |
| Quién lo genera | Sales o Purchase, al crear la secuencia (`id` de la respuesta `201`) |
| Alcance | Empresa: exige membresía `ACTIVE`; una secuencia de ventas no sirve para compras ni al revés |

## Cómo obtenerlo

**¿Qué hace?** Cada lista devuelve todas las secuencias de numeración de la empresa en ese servicio (activas e inactivas, de sucursal y de empresa), sin paginación, con su formato, su estado y sus contadores por período. Es la pantalla de configuración de numeración y el primer paso para diagnosticar un `409 SEQUENCE_NOT_CONFIGURED` al confirmar. Descrita paso a paso en [Administración empresarial, API 18](../principales/administracion-empresarial.md#18-consultar-las-secuencias-de-numeración).

| | Ventas | Compras |
|---|---|---|
| Método y ruta | `GET /api/v1/companies/{company_id}/sale-sequences` | `GET /api/v1/companies/{company_id}/purchase-sequences` |
| URL completa | `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sale-sequences` | `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchase-sequences` |
| Parámetros de ruta | `company_id` (UUID) — [cómo obtenerlo](company-id.md) | igual |
| Parámetros de consulta | Ninguno | Ninguno |
| Permiso | `perm:sales:sale_sequences:read` | `perm:purchase:purchase_sequences:read` |
| Clasificación | `READ` | `READ` |

```bash
curl -X GET \
  'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sale-sequences' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

```bash
curl -X GET \
  'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchase-sequences' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Respuesta `200` (modelo `SequenceList`; en Purchase el objeto es idéntico con `document_kind: "PURCHASE"`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "d9cd7378-6b8f-4e54-8171-39db2f8ebfe1",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "document_kind": "SALE",
      "series_code": "POS-01",
      "prefix": "V",
      "separator": "-",
      "initial_number": 1,
      "maximum_number": 999999,
      "number_length": 6,
      "reset_policy": "NEVER",
      "is_active": true,
      "version": 1,
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "counters": [
        {
          "period_key": "",
          "current_number": 123,
          "next_number_preview": "V-000124"
        }
      ]
    }
  ]
}
```

**Campo exacto:** `items[].id`. Elige el elemento por `branch_id` (la sucursal buscada, o `null` para la secuencia de la empresa) y comprueba `is_active`. Guarda también `items[].version`: lo piden las operaciones de modificación y de cambio de estado.

**Posibles errores de la lista de ventas** (en compras, los mismos con prefijo `PURCHASE.` y permiso `perm:purchase:purchase_sequences:read`):

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `SALES.FORBIDDEN` | Falta `perm:sales:sale_sequences:read` o el token es de una cuenta de servicio | Mostrar que faltan permisos y el `trace_id` |
| `404` | `SALES.NOT_FOUND` | El usuario no tiene membresía `ACTIVE` en la empresa o la empresa no existe | Volver a leer el contexto operativo |
| `422` | `SALES.VALIDATION_ERROR` | `company_id` no es un UUID | Corregir el identificador |
| `503` | `SALES.DEPENDENCY_UNAVAILABLE` | Base de datos u Operational Context no disponibles | Reintentar más tarde |

## Si la secuencia no existe todavía (operación `WRITE`)

**¿Qué hace la API de creación?** `POST https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sale-sequences` (permiso `perm:sales:sale_sequences:create`) y `POST https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchase-sequences` (permiso `perm:purchase:purchase_sequences:create`) crean una secuencia y la dejan activa para una sucursal (`branch_id`) o para toda la empresa (`branch_id: null`), con su prefijo, separador, número inicial, longitud, tope y política de reinicio. Devuelven `201` con la secuencia; el `sequence_id` es su campo `id`. Sin una secuencia activa aplicable, confirmar una venta o una compra responde `409 SEQUENCE_NOT_CONFIGURED`. Cuerpo completo en [Administración empresarial, API 19](../principales/administracion-empresarial.md#19-crear-una-secuencia-de-numeración).

**Posibles errores al crear:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `SALES.FORBIDDEN` / `PURCHASE.FORBIDDEN` | Falta el permiso `…sequences:create` | Mostrar que faltan permisos |
| `404` | `SALES.NOT_FOUND` / `PURCHASE.NOT_FOUND` | Sin membresía `ACTIVE` en la empresa | Volver a leer el contexto operativo |
| `409` | `…SEQUENCE_ALREADY_ACTIVE` | Ya hay una secuencia activa para esa empresa y sucursal (o de empresa) | Desactivar la existente o modificarla |
| `409` | `…SEQUENCE_IN_USE` (`field: series_code`) | Ya existe una secuencia con ese `series_code` en el mismo alcance | Elegir otro código de serie |
| `409` | `…REFERENCES_NOT_ELIGIBLE` (`errors[].code: BRANCH_INACTIVE`) | La sucursal está `INACTIVE` | Reactivarla o elegir otra |
| `422` | `…VALIDATION_ERROR` | `branch_id` ajeno a la empresa (`BRANCH_NOT_FOUND`), `series_code` o `prefix` fuera de patrón, separador no permitido, `maximum_number` < `initial_number`, número > 80 caracteres, campo desconocido | Corregir el formulario |


## Cómo usarlo después

- En [Administración empresarial](../principales/administracion-empresarial.md): `{sequence_id}` de la ruta de la [API 20](../principales/administracion-empresarial.md#20-desactivar-o-reactivar-una-secuencia), que desactiva una secuencia (las confirmaciones de ese alcance pasan a fallar con `409 SEQUENCE_NOT_CONFIGURED`, salvo respaldo de empresa) o la reactiva (`409 SEQUENCE_ALREADY_ACTIVE` si hay otra activa), y de la [API 21](../principales/administracion-empresarial.md#21-consultar-y-modificar-una-secuencia), que consulta una secuencia o modifica su configuración (`409 SEQUENCE_IN_USE` si ya numeró y se cambia el formato; `422 MAXIMUM_NUMBER_BELOW_CURRENT` si el tope queda por debajo del último número). Ambas exigen la `version` actual en el cuerpo (`409 VERSION_CONFLICT` si está desactualizada); sus tablas de errores completas están en esas secciones.
- Fichas técnicas: [Sales 18–21](../servicios/sales.md#18-get-companiescompany_idsale-sequencessequence_id) y [Purchase 20–23](../servicios/purchase.md#20-get-companiescompany_idpurchase-sequencessequence_id).
- No se envía al crear ni confirmar ventas o compras: el servicio elige solo la secuencia activa de la sucursal del documento o, en su defecto, la de la empresa.

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `404 SALES.NOT_FOUND` / `PURCHASE.NOT_FOUND` | La secuencia no es de esa empresa, no existe, o el usuario no tiene membresía `ACTIVE` en la empresa |
| `409 …VERSION_CONFLICT` | La `version` enviada no es la actual: volver a listar y repetir |
| `409 …SEQUENCE_ALREADY_ACTIVE` | Ya hay otra secuencia activa para la misma empresa, sucursal y tipo de documento |
| `409 …SEQUENCE_IN_USE` | La secuencia ya asignó números y se intentó cambiar su formato |
