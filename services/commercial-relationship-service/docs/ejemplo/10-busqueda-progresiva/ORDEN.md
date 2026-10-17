# Ejercicio 10 — Búsqueda progresiva de productos y presentaciones por productos

[← Todos los ejercicios](../README.md)

**Qué enseña:** **Buscar** productos de la empresa por nombre, código o **SKU de una presentación**, **continuar** la búsqueda desde la posición del último producto recibido sin conteos ni páginas numeradas, **evaluar** filtros sobre un lote de ids y pedir en **una sola llamada** las presentaciones de varios productos (spec 022). Son las consultas que usa el servicio de consultas consolidadas.

**Datos:** **reales** del sistema anterior (`docs/CAMPOS PRODUCTOS.xlsx`) — detalle y decisiones en [00-datos-del-excel.md](00-datos-del-excel.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-del-excel.md](00-datos-del-excel.md) | Leer: las filas del Excel y cómo se interpretan | — | — |
| 01 | [01-consultar-datos.md](01-consultar-datos.md) | Obtener `<EMPRESA>`, los productos globales y las presentaciones del acetaminofén. | 6 | — |
| 02 | [02-adoptar-productos.md](02-adoptar-productos.md) | Crear tres productos empresariales y dos presentaciones con SKU. | 5 | 01 |
| 03 | [03-buscar.md](03-buscar.md) | Encontrar productos por partes del nombre, por código exacto y por el SKU de una presentación. | 3 | 01 |
| 04 | [04-continuar.md](04-continuar.md) | Pedir de a dos productos y seguir con la posición del último recibido. | 2 | 01 |
| 05 | [05-lotes-y-rechazos.md](05-lotes-y-rechazos.md) | Comprobar filtros sobre un lote de ids, traer las presentaciones de varios productos y los errores. | 4 | 01, 02 |

## Por qué este orden

1. **Productos y presentaciones primero.** La búsqueda por SKU necesita una presentación adoptada.
2. **Primera llamada antes de continuar.** La segunda llamada usa la posición que devolvió la primera.

## Lista de `id` que debe ir guardando

| Variable | Se obtiene en | Se usa en |
| --- | --- | --- |
| `<EMPRESA>` | 01 | 02, 03, 04, 05 |
| `<GP_ACETAMINOFEN>` | 01 | 02 |
| `<GP_AGUJA>` | 01 | 02, 05 |
| `<GP_IRBESARTAN>` | 01 | 02 |
| `<GPRES_CAJA>` | 01 | 02 |
| `<GPRES_SOBRE>` | 01 | 02 |
| `<ACETAMINOFEN>` | 02 | 05 |
| `<AGUJA>` | 02 | 05 |
| `<IRBESARTAN>` | 02 | — |
| `<PRES_CAJA>` | 02 | — |
| `<PRES_SOBRE>` | 02 | — |
| `<POS_K>` | 04 | — |
| `<POS_ID>` | 04 | — |

[Empezar → paso 01](01-consultar-datos.md)
