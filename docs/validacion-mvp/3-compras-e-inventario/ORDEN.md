# Ejercicio 3 — Compras e inventario: secuencias, compras, confirmación, entradas, saldos, kardex y capas

[← Recorrido completo](../README.md)

**Datos:** ficticios, con el `RUN_ID` de la corrida en nombres y códigos (`<RUN_ID>`).

## Orden de ejecución

Ejecute los archivos en este orden; cada paso usa los `id` guardados en los anteriores (y en los ejercicios previos).

| Paso | Archivo | Qué hace | Llamadas | Deja guardado |
| --- | --- | --- | --- | --- |
| 01 | [01-crear-las-secuencias-de-numeracion.md](01-crear-las-secuencias-de-numeracion.md) | Crear las secuencias de numeración | 2 | `<SECUENCIA_COMPRAS>`, `<SECUENCIA_VENTAS>` |
| 02 | [02-registrar-las-compras.md](02-registrar-las-compras.md) | Registrar las compras | 4 | `<COMPRA_1>`, `<COMPRA_1_VERSION>`, `<COMPRA_2>`, `<COMPRA_2_VERSION>`, `<COMPRA_3>`, `<COMPRA_3_VERSION>`, `<COMPRA_4>`, `<COMPRA_4_VERSION>` |
| 03 | [03-confirmar-las-compras.md](03-confirmar-las-compras.md) | Confirmar las compras | 3 | `<COMPRA_1_NUMERO>`, `<COMPRA_1_OPERACION>`, `<COMPRA_1_VERSION>`, `<COMPRA_2_NUMERO>`, `<COMPRA_2_OPERACION>`, `<COMPRA_2_VERSION>`, `<COMPRA_3_NUMERO>`, `<COMPRA_3_OPERACION>`, `<COMPRA_3_VERSION>` |
| 04 | [04-consultar-el-inventario-tras-las-compras.md](04-consultar-el-inventario-tras-las-compras.md) | Consultar el inventario tras las compras | 5 | — |

Usuarios y permisos de este ejercicio: [USUARIOS.md](USUARIOS.md).
