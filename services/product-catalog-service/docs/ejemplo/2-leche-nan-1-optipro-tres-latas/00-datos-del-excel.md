# Datos del Excel — Ejercicio 2 — Leche NAN 1 Optipro: tres filas del Excel, un solo producto

[← Orden del ejercicio](ORDEN.md)

Fuente: `docs/CAMPOS PRODUCTOS.xlsx`, hoja `Hoja1`.

## Lo que dice el Excel

| Columna | Valor |
| --- | --- |
| ID / Código | 7334 / 007334 · 6138 / 006138 · 7333 / 007333 |
| Nombre (7334) | NAN 1 OPTIPRO LECHE POLVO LATAX400G RF12495528 NESTLE |
| Nombre (6138) | NAN 1 OPTIPRO LECHE POLVO LATAX900G NESTLE |
| Nombre (7333) | NAN 1 OPTIPRO LECHE POLVO LATAX1100G NESTLE |
| Nombre Tipo Producto | LECHES |
| Unidad Medida | LATA (las tres) |
| Contenido Interno | vacío (las tres) |
| Código Barras 1 | 7501059227453 · 7501059227644 · 7501059279124 (EAN-13 válidos) |
| Estado | A |
| Grupo 1 / 2 / 4 | 0687 ALIMENTOS / 0689 LECHES / 0336 NESTLE |
| Grupo 3 / 5 | 0133 NO APLICA / 0695 NO APLICA |
| Grupo 6 | 0836 EXCLUIR VIERNES DAO |
| Maneja Presentaciones | N |

## Cómo se interpreta en el catálogo

| Tema | Decisión |
| --- | --- |
| Qué es el producto | "NAN 1 Optipro leche en polvo". Las tres filas describen **el mismo producto** en tres tamaños de lata. En el sistema anterior cada tamaño era un producto; en el catálogo global es **un producto** con tres presentaciones. |
| Marca / fabricante | Marca `NAN`; fabricante Nestlé (Party Identity). |
| Unidad base | `G` (gramo). Así cada lata se expresa en gramos y las tres son comparables: 400, 900 y 1100 g. |
| Presentaciones | `LATA_400G`, `LATA_900G`, `LATA_1100G`, empaque `CAN`. **Ninguna** es base: ninguna equivale a 1 g. |
| Categoría | `ALIMENTOS > LECHES`. |
| Atributos | Etapa = 1 (`INTEGER`, sale de "NAN **1**") y fórmula infantil = sí (`BOOLEAN`). |
| Códigos de barras | Uno por fila del Excel → uno por presentación. |
| Grupos | `GROUP_1` 0687, `GROUP_2` 0689 y `GROUP_4` 0336. No se importan `NO APLICA` (G3, G5) ni `EXCLUIR VIERNES DAO` (G6). |
| No va al catálogo | `RF12495528` (referencia del proveedor dentro del nombre), `Maneja Presentaciones = N` (en el catálogo todo producto tiene presentaciones), códigos internos, precios, stock y lotes. |

Referencia general de columnas: [../mapeo-campos-excel.md](../mapeo-campos-excel.md).

[Empezar → paso 01](01-consultar-datos-base.md)
