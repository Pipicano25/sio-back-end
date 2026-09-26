# Datos del Excel — Ejercicio 4 — Aguja hipodérmica 18G x 1½" Rymco, caja x 100

[← Orden del ejercicio](ORDEN.md)

Fuente: `docs/CAMPOS PRODUCTOS.xlsx`, hoja `Hoja1`.

## Lo que dice el Excel

| Columna | Valor |
| --- | --- |
| ID | 537 |
| Código | 000537 |
| Referencia | 71430 |
| Nombre | AGUJA 18GX1 1/2 CAJAX100 RFZC18B RYMCO |
| Nombre Tipo Producto | HOSPITALARIOS |
| Nombre Corto | AGUJA 18GX1 1/2 |
| Unidad Medida | CAJA |
| Contenido Interno | 100 |
| Código Barras 1 | 27706634002850 (GTIN-14 válido) |
| Código Barras 2 | 7706634002856 (EAN-13 válido) |
| Estado | A |
| Grupo 1 / 2 / 4 | 0005 MEDICO QUIRURGICOS / 0016 DISPOSITIVOS MEDICOS / 0278 RYMCO |
| Grupo 5 | 0695 NO APLICA |
| % Impuesto | 19 |

## Cómo se interpreta en el catálogo

| Tema | Decisión |
| --- | --- |
| Qué es el producto | "Aguja hipodérmica 18G x 1 1/2 pulgadas". |
| Marca | **Ninguna**. Rymco es el fabricante; no hay una marca comercial distinta. `global_brand_id` es opcional. |
| Fabricante | Rymco (Party Identity). |
| Referencia `RFZC18B` | Es la referencia de catálogo **del fabricante** (viene en el nombre). Se registra como identificador `OTHER`. No confundir con la columna `Referencia` (71430), que es de la empresa. |
| Unidad base | `UND` = una aguja. |
| Presentaciones | `UNIDAD` (base) y `CAJA_X100` (empaque `BOX`, factor 100). |
| Códigos | El GTIN-14 `2 770663400285 0` se construye con los mismos 12 dígitos del EAN-13 `770663400285 6` más un **dígito indicador** (`2`). En GS1 eso significa: el GTIN-14 identifica un **agrupamiento** del artículo que identifica el EAN-13. Por eso: EAN-13 → `UNIDAD`, GTIN-14 → `CAJA_X100`. |
| Categoría | `DISPOSITIVOS_MEDICOS > AGUJAS_HIPODERMICAS`. |
| Atributos | Calibre = 18 (`INTEGER`, escala gauge) y longitud = 1.5 `PULG` (`DECIMAL` con unidad). |
| Grupos | `GROUP_1` 0005, `GROUP_2` 0016, `GROUP_4` 0278. `NO APLICA` no se importa. |

Referencia general de columnas: [../mapeo-campos-excel.md](../mapeo-campos-excel.md).

[Empezar → paso 01](01-consultar-datos-base.md)
