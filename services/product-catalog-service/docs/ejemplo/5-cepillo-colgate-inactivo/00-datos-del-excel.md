# Datos del Excel — Ejercicio 5 — Cepillo Colgate infantil pack x 2 (producto inactivo)

[← Orden del ejercicio](ORDEN.md)

Fuente: `docs/CAMPOS PRODUCTOS.xlsx`, hoja `Hoja1`.

## Lo que dice el Excel

| Columna | Valor |
| --- | --- |
| ID | 26396 |
| Código | 022348 |
| Referencia | NT |
| Nombre | CEPILLO COLGATE INFANTIL 2-5 AÑOS EXTRA SUAVE NIÑA PACK X2 |
| Nombre Tipo Producto | CONSUMO |
| Unidad Medida | PACK |
| Contenido Interno | vacío |
| Código Barras 1 | 022348 (6 dígitos: **igual a la columna `Código`**) |
| Estado | **I** (es el único producto inactivo del Excel) |
| Grupo 1 / 2 / 4 | 0005 MEDICO QUIRURGICOS / 0016 DISPOSITIVOS MEDICOS / 0213 COLGATE PALMOLIVE |
| Grupo 3 / 5 | 0133 NO APLICA / 0695 NO APLICA |
| % Impuesto | 19 |

## Cómo se interpreta en el catálogo

| Tema | Decisión |
| --- | --- |
| Qué es el producto | "Colgate cepillo dental infantil 2 a 5 años extra suave niña". |
| Marca / fabricante | Marca `COLGATE`; fabricante Colgate-Palmolive (Party Identity). |
| Unidad base | `UND` = un cepillo. |
| Presentación | `PACK_X2`: empaque `PACK`, factor 2. `Contenido Interno` viene vacío, pero el nombre dice `PACK X2`. |
| Categoría | `CUIDADO_ORAL > CEPILLOS_DENTALES`. `Nombre Tipo Producto = CONSUMO` no describe qué es el producto. |
| Atributos | Dureza de cerdas = Extra suave (`OPTION`) y rango de edad = "2 a 5 años" (`TEXT`). |
| Código de barras | **Ninguno**. `022348` es igual a la columna `Código` (código interno de la empresa) y no cumple GS1. Va a `CompanyProduct.internal_code` en Commercial Relationship Service. |
| Grupos | `GROUP_1` 0005 y `GROUP_2` 0016 (los mismos del ejercicio 4) y `GROUP_4` 0213. Se importan **tal como vienen**, aunque un cepillo no es un dispositivo médico: ver nota en el paso 11. |
| Estado `I` | Se carga todo y se inactiva al final (paso 12). |

Referencia general de columnas: [../mapeo-campos-excel.md](../mapeo-campos-excel.md).

[Empezar → paso 01](01-consultar-datos-base.md)
