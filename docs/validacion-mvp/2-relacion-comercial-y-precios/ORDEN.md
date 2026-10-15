# Ejercicio 2 — Relación comercial y precios: proveedor, cliente, productos, adopción, presentaciones y listas

[← Recorrido completo](../README.md)

**Datos:** ficticios, con el `RUN_ID` de la corrida en nombres y códigos (`<RUN_ID>`).

## Orden de ejecución

Ejecute los archivos en este orden; cada paso usa los `id` guardados en los anteriores (y en los ejercicios previos).

| Paso | Archivo | Qué hace | Llamadas | Deja guardado |
| --- | --- | --- | --- | --- |
| 01 | [01-consultar-los-datos-de-referencia.md](01-consultar-los-datos-de-referencia.md) | Consultar los datos de referencia | 3 | `<METODO_EFECTIVO>`, `<TIPO_CREDITO>`, `<UNIDAD_UND>` |
| 02 | [02-seleccionar-el-proveedor-y-su-condicion-de-pago.md](02-seleccionar-el-proveedor-y-su-condicion-de-pago.md) | Seleccionar el proveedor y su condición de pago | 2 | `<CONDICION_CREDITO>`, `<PROVEEDOR>` |
| 03 | [03-incorporar-el-cliente.md](03-incorporar-el-cliente.md) | Incorporar el cliente | 1 | `<CLIENTE>` |
| 04 | [04-crear-los-productos-globales.md](04-crear-los-productos-globales.md) | Crear los productos globales | 8 | `<CATEGORIA>`, `<CATEGORIA_PRODUCTO_A>`, `<CATEGORIA_PRODUCTO_B>`, `<PRESENTACION_BASE_A>`, `<PRESENTACION_BASE_B>`, `<PRESENTACION_CAJA_A>`, `<PRODUCTO_A>`, `<PRODUCTO_B>` |
| 05 | [05-adoptar-productos-y-presentacion.md](05-adoptar-productos-y-presentacion.md) | Adoptar productos y presentación | 5 | `<PRESENTACION_BASE_EMPRESA_A>`, `<PRESENTACION_BASE_EMPRESA_B>`, `<PRESENTACION_CAJA_EMPRESA_A>`, `<PRODUCTO_EMPRESA_A>`, `<PRODUCTO_EMPRESA_A_VERSION>`, `<PRODUCTO_EMPRESA_B>`, `<PRODUCTO_EMPRESA_B_VERSION>` |
| 06 | [06-crear-las-listas-de-precios.md](06-crear-las-listas-de-precios.md) | Crear las listas de precios | 5 | `<ITEM_B>`, `<ITEM_GENERAL>`, `<ITEM_GENERAL_VERSION>`, `<ITEM_MAYORISTA>`, `<LISTA_GENERAL>`, `<LISTA_MAYORISTA>` |

Usuarios y permisos de este ejercicio: [USUARIOS.md](USUARIOS.md).
