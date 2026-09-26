# Datos del Excel — Ejercicio 3 — Pañal Winny Gold etapa 6 XXXG, paquete x 30

[← Orden del ejercicio](ORDEN.md)

Fuente: `docs/CAMPOS PRODUCTOS.xlsx`, hoja `Hoja1`.

## Lo que dice el Excel

| Columna | Valor |
| --- | --- |
| ID | 17747 |
| Código | 015721 |
| Referencia | 74865 |
| Nombre | WINNY GOLD ETAPA 6 XXXG PAQUETEX30 TECNOQUIMICAS |
| Nombre Tipo Producto | PAÑALES |
| Unidad Medida | PAQUETE |
| Contenido Interno | 30 |
| Talla / Nombre Talla | 0 / vacío |
| Código Barras 1 | 7701021118264 (EAN-13 válido) |
| Código Barras 2 | 7701021118912 (EAN-13 válido) |
| Estado | A |
| Grupo 1 / 2 / 4 | 0113 ASEO Y LIMPIEZA / 0691 PAÑALES / 0125 TECNOQUIMICAS (WINNY) |
| Grupo 3 / 5 / 6 | 0133 NO APLICA / 0695 NO APLICA / 0836 EXCLUIR VIERNES DAO |
| % Impuesto | 19 |

## Cómo se interpreta en el catálogo

| Tema | Decisión |
| --- | --- |
| Qué es el producto | "Winny Gold pañal etapa 6 talla XXXG". |
| Marca / fabricante | Marca `WINNY` (Gold es la línea, forma parte del nombre); fabricante Tecnoquímicas. |
| Talla | Las columnas `Talla` y `Nombre Talla` vienen **vacías** en todo el Excel; la talla está en el nombre. Se crea el atributo `TALLA_PANAL` (`OPTION`) con todas las tallas. |
| Etapa | `ETAPA_PANAL` = 6 (`INTEGER`). |
| Unidad base | `UND` = un pañal. |
| Presentación | `PAQUETE_X30`: empaque `PACK`, factor 30 (`Contenido Interno = 30`). |
| Categoría | `CUIDADO_BEBE > PANALES_BEBE`. |
| Códigos de barras | Dos EAN-13 válidos, ambos del paquete. |
| Grupos | `GROUP_1` 0113, `GROUP_2` 0691, `GROUP_4` 0125. No se importan `NO APLICA` ni `EXCLUIR VIERNES DAO`. |
| No va al catálogo | `% Impuesto = 19` (tributario, sin dueño definido aún), código interno, referencia, precios, stock. |

Referencia general de columnas: [../mapeo-campos-excel.md](../mapeo-campos-excel.md).

[Empezar → paso 01](01-consultar-datos-base.md)
