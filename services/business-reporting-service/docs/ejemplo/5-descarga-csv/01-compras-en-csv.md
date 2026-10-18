# Paso 1. Compras del período en CSV

Ejercicio 5: Descarga en CSV.

## Llamada

`GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/purchases?date_from=2026-10-01&date_to=2026-10-15&format=csv`

Ejecuta: `compras.test`.

### Por qué

- `format=csv`: mismos filtros, permisos y datos que el JSON, en UTF-8 con BOM.
- Las filas `TOTAL …` van al final; la última fila `TOTAL FILAS` solo aparece si el archivo está completo.
- El texto que empieza por `=`, `+`, `-` o `@` se escribe con `'` delante (protección de fórmulas).

## Permisos

La URL exige `perm:business-reporting:purchases:read`.

Como el servicio consulta a los propietarios **con el token del usuario**, el usuario también necesita: `perm:purchase:purchases:read`, `perm:operational-context:application_users:read`, `perm:operational-context:branches:read`. Además debe ser miembro `ACTIVE` de la empresa (no se exige asignación a la sucursal).

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` y los permisos de lectura del propietario |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` y los permisos de lectura del propietario |
| `compras.test` | Sí | `200` | tiene `perm:business-reporting:purchases:read` y los permisos de lectura del propietario |
| `ventas.test` | No | `403` | no tiene `perm:business-reporting:purchases:read` |
| `inventario.test` | No | `403` | no tiene `perm:business-reporting:purchases:read` |
| `reportes.test` | Sí | `200` | tiene `perm:business-reporting:purchases:read` y los permisos de lectura del propietario |
| `consulta.test` | No | `403` | no tiene `perm:business-reporting:purchases:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/business-reporting/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/purchases",
  "code": "BUSINESS_REPORTING.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta

`200`

Cabeceras: `Content-Type: text/csv; charset=utf-8` y `Content-Disposition: attachment; filename="purchases-d23a0000-0000-4000-8000-000000000001-2026-10-01-2026-10-15.csv"`.

Contenido (el archivo empieza con el BOM UTF-8, invisible):

```csv
Fecha,Recepción,Sucursal,Proveedor,Identificación del proveedor,Número,Documento del proveedor,Estado,Categoría,Moneda,Total,ID compra
2026-10-03,2026-10-04T15:20:00+00:00,Principal,Distribuidora Ficticia del Cauca,Dato ficticio,OC-000101,FV-3301,CONFIRMED,RECEIVED,COP,1450000.00,d2390000-0000-4000-8000-000000000001
2026-10-09,,Norte,Laboratorio Ficticio S.A.S.,Dato ficticio,OC-000102,,CONFIRMED,PENDING_RECEIPT,COP,620000.00,d2390000-0000-4000-8000-000000000002
2026-10-12,,Principal,Distribuidora Ficticia del Cauca,Dato ficticio,OC-000103,,CANCELLED,CANCELLED,COP,300000.00,d2390000-0000-4000-8000-000000000003
TOTAL RECIBIDAS,,,,,,,,,COP,1450000.00,
TOTAL PENDIENTES DE RECEPCIÓN,,,,,,,,,COP,620000.00,
TOTAL ANULADAS (no suma),,,,,,,,,COP,300000.00,
TOTAL EFECTIVO,,,,,,,,,COP,2070000.00,
TOTAL FILAS,3
```
