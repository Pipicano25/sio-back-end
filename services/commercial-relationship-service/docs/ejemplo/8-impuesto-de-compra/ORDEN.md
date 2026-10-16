# Ejercicio 8 — Tasa de impuesto de compra del producto

[← Todos los ejercicios](../README.md)

**Qué enseña:** Configurar la **tasa de impuesto de compra** predeterminada de los productos de la empresa: un producto nuevo queda **sin configurar** (distinto de 0 %), se configura uno por uno o en **lote** (todo o nada) y una tasa configurada no vuelve a quedar sin configurar. Compras la usa para calcular el impuesto de cada línea y no deja confirmar una compra con productos sin tasa (spec 021).

**Datos:** **reales** del sistema anterior (`docs/CAMPOS PRODUCTOS.xlsx`) — detalle y decisiones en [00-datos-del-excel.md](00-datos-del-excel.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-del-excel.md](00-datos-del-excel.md) | Leer: las filas del Excel y cómo se interpretan | — | — |
| 01 | [01-consultar-datos.md](01-consultar-datos.md) | Obtener `<EMPRESA>` y los productos globales. | 3 | — |
| 02 | [02-adoptar-productos.md](02-adoptar-productos.md) | Productos sin tasa configurada. | 2 | 01 |
| 03 | [03-configurar-tasas.md](03-configurar-tasas.md) | Una tasa individual, un rechazo y un lote. | 3 | 01, 02 |

## Por qué este orden

1. **Adoptar antes de configurar.** La tasa es un atributo del producto de la empresa.

## Lista de `id` que debe ir guardando

| Variable | Se obtiene en | Se usa en |
| --- | --- | --- |
| `<EMPRESA>` | 01 | 02, 03 |
| `<GP_ACETAMINOFEN>` | 01 | 02 |
| `<GP_IRBESARTAN>` | 01 | 02 |
| `<ACETAMINOFEN>` | 02 | 03 |
| `<IRBESARTAN>` | 02 | 03 |

[Empezar → paso 01](01-consultar-datos.md)
