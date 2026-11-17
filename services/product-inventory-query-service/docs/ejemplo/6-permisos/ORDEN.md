# Ejercicio 6: Permisos y bloques visibles

Cada bloque de la respuesta (precios, existencias y mínimos) depende de un permiso propio. Con los grupos de la spec 026, `empleado` y `admin` tienen los tres; un usuario con permisos parciales vería menos bloques (lo verifican las pruebas automáticas del servicio con identidades sintéticas).

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente y solo consulta: no cambia ningún dato.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-empleado-ve-todos-los-bloques.md](01-empleado-ve-todos-los-bloques.md) | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Loratadina` | `ventas.test` | `200` |
| 2 | [02-admin-ve-todos-los-bloques.md](02-admin-ve-todos-los-bloques.md) | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Loratadina` | `supervisor.test` | `200` |
| 3 | [03-filtro-de-minimos.md](03-filtro-de-minimos.md) | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-overviews?minimum_state=BELOW_MINIMUM` | `ventas.test` | `200` |
