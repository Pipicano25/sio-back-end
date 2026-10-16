# Ejercicio 7 — Políticas de ganancia de una lista de precios

[← Todos los ejercicios](../README.md)

**Qué enseña:** Crear **políticas de ganancia** en una lista (porcentaje de recargo sobre el costo real de compra), ver que una presentación no puede estar en **dos políticas de la misma lista**, **cambiar el porcentaje**, **retirar** una presentación e **inactivar** una política. Nada de esto cambia precios: los cambios rigen desde la siguiente recepción física de una compra (spec 021).

**Datos:** **reales** del sistema anterior (`docs/CAMPOS PRODUCTOS.xlsx`) — detalle y decisiones en [00-datos-del-excel.md](00-datos-del-excel.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-del-excel.md](00-datos-del-excel.md) | Leer: las filas del Excel y cómo se interpretan | — | — |
| 01 | [01-consultar-datos.md](01-consultar-datos.md) | Obtener `<EMPRESA>`, los productos y sus presentaciones globales. | 6 | — |
| 02 | [02-preparar-la-lista.md](02-preparar-la-lista.md) | Productos, presentaciones vendibles y la lista `PUBLICO`. | 6 | 01 |
| 03 | [03-crear-politicas.md](03-crear-politicas.md) | Dos políticas con porcentajes distintos y el rechazo de una presentación repetida. | 5 | 01, 02 |
| 04 | [04-modificar-politicas.md](04-modificar-politicas.md) | Historial de porcentajes y presentaciones; inactivación final. | 5 | 02, 03 |

## Por qué este orden

1. **Producto, presentaciones y lista antes de las políticas.** La política pertenece a una lista `ACTIVE` y solo admite presentaciones `ACTIVE` y vendibles de la empresa.
2. **Inactivar al final.** Una política inactiva es un estado final: no se modifica ni se reactiva.

## Lista de `id` que debe ir guardando

| Variable | Se obtiene en | Se usa en |
| --- | --- | --- |
| `<EMPRESA>` | 01 | 02, 03 |
| `<GP_ACETAMINOFEN>` | 01 | 02 |
| `<GP_IRBESARTAN>` | 01 | 02 |
| `<GPRES_CAJA>` | 01 | 02 |
| `<GPRES_SOBRE>` | 01 | 02 |
| `<GPRES_IRBE>` | 01 | 02 |
| `<ACETAMINOFEN>` | 02 | — |
| `<IRBESARTAN>` | 02 | — |
| `<CAJA>` | 02 | 03 |
| `<SOBRE>` | 02 | 03, 04 |
| `<IRBE>` | 02 | 03 |
| `<LISTA>` | 02 | 03 |
| `<ALIMENTOS>` | 03 | 04 |
| `<ESPECIALES>` | 03 | 04 |

[Empezar → paso 01](01-consultar-datos.md)
