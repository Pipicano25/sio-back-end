# Datos del ejercicio — Ejercicio 4 — Presentaciones de un producto empresarial

[← Orden del ejercicio](ORDEN.md)

> **Datos reales del sistema anterior.** Los productos son filas de `docs/CAMPOS PRODUCTOS.xlsx` (se cita la fila de cada uno). Mapeo de columnas: [../mapeo-campos-excel.md](../mapeo-campos-excel.md). La empresa y los datos marcados como **ficticios** son inventados.

## Datos usados

| Dato | Valor |
| --- | --- |
| Fuente | `docs/CAMPOS PRODUCTOS.xlsx`, hoja `Hoja1` (encabezados en la fila 2) |
| Fila 40 | `Código` 000045 · `Nombre` ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED · `Unidad Medida` CAJA · `Contenido Interno` 100 · `Maneja Presentaciones` S |
| Presentaciones | **Ficticias**: «Caja x100» y «Sobre x10» del acetaminofén y «Caja x100» de la aguja (fila 413), registradas en Product Catalog. La fuente no trae presentaciones por fila. |
| SKU | **Ficticios** (`ACE-CJ100`, `ACE-SB10`). |
| Empresa | DROGUERÍA PRESENTACIONES FICTICIA S.A.S. (**ficticia**), registrada en Operational Context. |

## Cómo se interpretan

| Tema | Decisión |
| --- | --- |
| Qué se adopta | La presentación global ya existe en Product Catalog; la empresa decide cuáles compra o vende y les pone su código o SKU. Solo se guarda el `id` de la presentación global. |
| Mismo producto | La presentación debe ser del **mismo** producto global que adoptó el producto empresarial. |
| Primer uso | Antes de guardar, Product Catalog registra el primer uso de la presentación; si falla, no se guarda nada. |
| Predeterminada | Hay como máximo una predeterminada de compra y una de venta por producto. Marcar otra retira la anterior en la misma operación, que sube su `version` (aclaración 4). Inactivar retira la marca (DS-05). |

[Empezar → paso 01](01-consultar-datos.md)
