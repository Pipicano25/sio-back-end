# Datos del ejercicio — Ejercicio 10 — Búsqueda progresiva de productos y presentaciones por productos

[← Orden del ejercicio](ORDEN.md)

> **Datos reales del sistema anterior.** Los productos son filas de `docs/CAMPOS PRODUCTOS.xlsx` (se cita la fila de cada uno). Mapeo de columnas: [../mapeo-campos-excel.md](../mapeo-campos-excel.md). La empresa y los datos marcados como **ficticios** son inventados.

## Datos usados

| Dato | Valor |
| --- | --- |
| Fuente | `docs/CAMPOS PRODUCTOS.xlsx`, hoja `Hoja1` (encabezados en la fila 2) |
| Fila 40 | `Código` 000045 · ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED |
| Fila 413 | `Código` 000537 · AGUJA 18GX1 1/2 CAJAX100 RFZC18B RYMCO |
| Fila 16577 | `Código` 022315 · IRBESARTAN+HIDROCLOROTIAZIDA (IRBESARTAN/HCT) 150+12.5MG TABLETA CAJAX30MK |
| Presentaciones y SKU | **Ficticios**: «Caja x100» (`ACE-CJ100`) y «Sobre x10» (`ACE-SB10`) del acetaminofén. La fuente no trae presentaciones por fila. |
| Empresa | DROGUERÍA BÚSQUEDAS FICTICIA S.A.S. (**ficticia**), registrada en Operational Context. |

## Cómo se interpretan

| Tema | Decisión |
| --- | --- |
| Orden estable | Los resultados van ordenados por `display_name` (o por la clave de `sort`) y, a igualdad, por `id`. Ese orden no cambia entre llamadas. |
| Posición | Cada producto trae su `position`: el valor de la clave de orden y su `id`. Para seguir, se envía en `after` la posición del **último producto que se usó**; la búsqueda devuelve solo los posteriores. |
| Sin conteos | No hay `total_records`: `has_more` dice si quedan productos. Así una búsqueda no recorre toda la empresa para contar. |
| Modo evaluador | Con `company_product_ids` o `global_product_ids` (hasta 100) se comprueba qué productos de un lote cumplen los filtros. |

[Empezar → paso 01](01-consultar-datos.md)
