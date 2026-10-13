# Ejercicio 4 — Ventas con precio por presentación (lista indicada y predeterminada), rechazos, costo FIFO y margen

[← Recorrido completo](../README.md)

**Datos:** ficticios, con el `RUN_ID` de la corrida en nombres y códigos (`<RUN_ID>`).

## Orden de ejecución

Ejecute los archivos en este orden; cada paso usa los `id` guardados en los anteriores (y en los ejercicios previos).

| Paso | Archivo | Qué hace | Llamadas | Deja guardado |
| --- | --- | --- | --- | --- |
| 01 | [01-registrar-las-ventas.md](01-registrar-las-ventas.md) | Registrar las ventas | 7 | `<VENTA_1>`, `<VENTA_1_VERSION>`, `<VENTA_2>`, `<VENTA_2_VERSION>`, `<VENTA_3>`, `<VENTA_3_VERSION>`, `<VENTA_4>`, `<VENTA_4_VERSION>`, `<VENTA_5>`, `<VENTA_5_VERSION>`, `<VENTA_6>`, `<VENTA_6_VERSION>`, `<VENTA_7>`, `<VENTA_7_VERSION>` |
| 02 | [02-consultar-la-disponibilidad.md](02-consultar-la-disponibilidad.md) | Consultar la disponibilidad | 2 | — |
| 03 | [03-confirmar-las-ventas.md](03-confirmar-las-ventas.md) | Confirmar las ventas | 3 | `<VENTA_1_NUMERO>`, `<VENTA_1_OPERACION>`, `<VENTA_1_VERSION>`, `<VENTA_2_NUMERO>`, `<VENTA_2_OPERACION>`, `<VENTA_2_VERSION>`, `<VENTA_3_NUMERO>`, `<VENTA_3_OPERACION>`, `<VENTA_3_VERSION>` |
| 04 | [04-rechazo-por-existencias-insuficientes.md](04-rechazo-por-existencias-insuficientes.md) | Rechazo por existencias insuficientes | 1 | — |
| 05 | [05-rechazo-por-precio-cambiado.md](05-rechazo-por-precio-cambiado.md) | Rechazo por precio cambiado | 2 | `<ITEM_GENERAL_NUEVO>` |
| 06 | [06-rechazo-por-producto-inactivo.md](06-rechazo-por-producto-inactivo.md) | Rechazo por producto inactivo | 3 | `<PRODUCTO_EMPRESA_B_VERSION>` |
| 07 | [07-costo-y-margen-segun-el-permiso.md](07-costo-y-margen-segun-el-permiso.md) | Costo y margen según el permiso | 2 | — |
| 08 | [08-consultar-el-inventario-tras-las-ventas.md](08-consultar-el-inventario-tras-las-ventas.md) | Consultar el inventario tras las ventas | 9 | — |

Usuarios y permisos de este ejercicio: [USUARIOS.md](USUARIOS.md).
