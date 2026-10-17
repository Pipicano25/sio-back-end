# Ejercicio 9 — Actualizaciones automáticas de precio

[← Todos los ejercicios](../README.md)

**Qué enseña:** Ver cómo una **recepción física** de compra actualiza el precio de una lista con políticas: el **costo real** de la línea (con su impuesto) más el porcentaje de la política. Consultar las **actualizaciones automáticas** (cálculo y estado) y **resolver administrativamente** una que falló, sin cambiar precios. Solo administradores y supervisores las ven, porque exponen costos (spec 021).

**Datos:** **reales** del sistema anterior (`docs/CAMPOS PRODUCTOS.xlsx`) — detalle y decisiones en [00-datos-del-excel.md](00-datos-del-excel.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-del-excel.md](00-datos-del-excel.md) | Leer: las filas del Excel y cómo se interpretan | — | — |
| 01 | [01-consultar-datos.md](01-consultar-datos.md) | Obtener `<EMPRESA>`, el producto y su presentación global. | 3 | — |
| 02 | [02-preparar-la-politica.md](02-preparar-la-politica.md) | La caja del acetaminofén en la política `Medicamentos` (30 %) de la lista `PUBLICO`. | 5 | 01 |
| 03 | [03-recepciones.md](03-recepciones.md) | Una recepción crea el primer precio; la segunda falla (simulado) y queda pendiente de reintento. | 2 | 01, 02 |
| 04 | [04-consultar-actualizaciones.md](04-consultar-actualizaciones.md) | Ver el cálculo de cada actualización y encontrar la que falló. | 3 | 01 |
| 05 | [05-resolver.md](05-resolver.md) | Cerrarla con un motivo, sin cambiar precios. | 3 | 01, 02, 04 |

## Por qué este orden

1. **Política antes de recibir.** Solo las listas con una política activa en el momento de la recepción reciben precios automáticos; las demás conservan sus precios manuales.
2. **Consultar antes de resolver.** La resolución pide la `version` vigente de la actualización.

## Lista de `id` que debe ir guardando

| Variable | Se obtiene en | Se usa en |
| --- | --- | --- |
| `<EMPRESA>` | 01 | 02, 04, 05 |
| `<GP_ACETAMINOFEN>` | 01 | 02 |
| `<GPRES_CAJA>` | 01 | 02 |
| `<ACETAMINOFEN>` | 02 | — |
| `<CAJA>` | 02 | — |
| `<LISTA>` | 02 | 05 |
| `<MEDICAMENTOS>` | 02 | — |
| `<FALLIDA>` | 04 | 05 |

[Empezar → paso 01](01-consultar-datos.md)
