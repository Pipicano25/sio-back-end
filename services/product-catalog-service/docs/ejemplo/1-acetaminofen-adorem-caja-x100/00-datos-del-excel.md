# Datos del Excel — Ejercicio 1 — Acetaminofén Adorem 500 mg, caja x 100

[← Orden del ejercicio](ORDEN.md)

Fuente: `docs/CAMPOS PRODUCTOS.xlsx`, hoja `Hoja1`.

## Lo que dice el Excel

| Columna | Valor |
| --- | --- |
| ID | 45 |
| Código | 000045 |
| Referencia | 48691 |
| Nombre | ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED |
| Nombre Marca | GENERAL |
| Nombre Tipo Producto | ETICOS |
| Nombre Corto | ACETAMINOFEN |
| Unidad Medida | CAJA |
| Contenido Interno | 100 |
| Código Barras 1 | 7707355056876 (EAN-13 válido) |
| Código Barras 2 | 7707355052038 (EAN-13 válido) |
| Estado | A |
| Grupo 1 | 0001 MEDICAMENTOS ETICOS |
| Grupo 2 | 0012 OTC |
| Grupo 3 | 0085 ANALGESICOS |
| Grupo 4 | 0170 SIEGFRIED |
| Grupo 5 | 0695 NO APLICA |
| Maneja Lotes / Fecha Vencimiento | S / S |

## Cómo se interpreta en el catálogo

| Tema | Decisión |
| --- | --- |
| Qué es el producto | "Acetaminofén 500 mg tableta". Del nombre se separa lo que es del producto (principio activo, concentración, forma) de lo que es de la presentación (`CAJAX100`) y del fabricante (`SIEGFRIED`). |
| Marca | `ADOREM`, que viene entre paréntesis en el nombre. La columna `Nombre Marca` dice `GENERAL` en casi todo el Excel, así que no sirve. |
| Fabricante | Siegfried → organización en Party Identity (sale del nombre y de `Grupo 4`). |
| Unidad base | `UND` = una tableta. Es la unidad más pequeña en que se puede vender. |
| Presentaciones | `TABLETA` (base, factor 1) y `CAJA_X100` (empaque `BOX`, factor 100). `Contenido Interno = 100` es el factor. |
| Categoría | `MEDICAMENTOS > MEDICAMENTOS_ETICOS` (sale de `Nombre Tipo Producto = ETICOS`). |
| Atributos | Principio activo = Acetaminofén (`TEXT`), concentración = 500 `MG` (`DECIMAL`), forma farmacéutica = Tableta (`OPTION`). |
| Códigos de barras | Dos EAN-13 válidos. Los dos identifican la caja (la tableta suelta no lleva código). |
| Grupos | `GROUP_1` a `GROUP_4` con el código y nombre del Excel. `Grupo 5 = NO APLICA` no se importa. |
| No va al catálogo | `Código` (000045), `Referencia` (48691), `Nombre Corto`, precios, costos, stock, impuestos, lotes y vencimientos: son datos de cada empresa (Commercial Relationship / Inventory). |

Referencia general de columnas: [../mapeo-campos-excel.md](../mapeo-campos-excel.md).

[Empezar → paso 01](01-consultar-datos-base.md)
