# Ejemplos de business-reporting-service

Ejercicios paso a paso, ejecutados y validados por `tests/examples/` (Principio XXII). Todos los datos son
**ficticios**; las dependencias se simulan con las agregaciones que devolverían los propietarios.

| Ejercicio | Qué muestra |
|---|---|
| [1-productos-mas-vendidos](1-productos-mas-vendidos/ORDEN.md) | Ranking por cantidad (por defecto) e importe, unidades base y presentaciones |
| [2-ventas-por-sucursal](2-ventas-por-sucursal/ORDEN.md) | Comparación de sucursales y participación |
| [3-compras-del-periodo](3-compras-del-periodo/ORDEN.md) | Recibidas, pendientes y anuladas; totales efectivos |
| [4-evolucion-de-existencias](4-evolucion-de-existencias/ORDEN.md) | Existencias de la sucursal principal y consolidadas de la empresa, sin costos |
| [5-descarga-csv](5-descarga-csv/ORDEN.md) | El mismo reporte en CSV |
| [6-reportes-por-sucursal](6-reportes-por-sucursal/ORDEN.md) | Rutas `/branches/{branch_id}/reports/…`: ventas y compras de una sola sucursal |

Requisitos para repetirlos con servicios reales: los propietarios con las ampliaciones de la spec 023, el token de
un usuario de prueba (`usuarios-y-permisos.md`) y `KEYCLOAK_TEST_USER_PASSWORD` en el entorno (nunca en el texto).

Convenciones: cada carpeta tiene `ORDEN.md`, los datos (`00-datos-ficticios.md`), un archivo por paso y
`USUARIOS.md`. `<asignado por el servicio>` marca los valores que cambian en cada ejecución.

Regenerar tras cambiar un ejercicio, un contrato o el realm:

```bash
BUSINESS_REPORTING_EXAMPLES_WRITE=1 .venv/bin/pytest tests/examples
```
