# Datos del ejercicio — Ejercicio 9 — Actualizaciones automáticas de precio

[← Orden del ejercicio](ORDEN.md)

> **Datos reales del sistema anterior.** Los productos son filas de `docs/CAMPOS PRODUCTOS.xlsx` (se cita la fila de cada uno). Mapeo de columnas: [../mapeo-campos-excel.md](../mapeo-campos-excel.md). La empresa y los datos marcados como **ficticios** son inventados.

## Datos usados

| Dato | Valor |
| --- | --- |
| Fuente | `docs/CAMPOS PRODUCTOS.xlsx`, hoja `Hoja1` (encabezados en la fila 2) |
| Fila 40 | `Código` 000045 · ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED |
| Recepción 1 | Compra `5e5e5e5e-0000-4000-8000-000000000901`, línea `5d5d5d5d-0000-4000-8000-000000000901`: 10 cajas por 23.800 COP con impuesto (2.380 por caja). **Ficticia.** |
| Recepción 2 | Compra `5e5e5e5e-0000-4000-8000-000000000902`, línea `5d5d5d5d-0000-4000-8000-000000000902`: 10 cajas por 20.000 COP con impuesto (2.000 por caja). **Ficticia**, y su falla es **simulada**. |
| Política | `Medicamentos`, 30 % sobre el costo (**ficticio**). |
| Empresa | DROGUERÍA ACTUALIZACIONES FICTICIA S.A.S. (**ficticia**). |

## Cómo se interpretan

| Tema | Decisión |
| --- | --- |
| Costo real | (subtotal − descuento + impuesto) / cantidad de la presentación, sin volver a sumar el impuesto: 23.800 / 10 = 2.380. No es el costo FIFO de Inventory. |
| Costo de referencia | Si el costo real baja frente a la recepción anterior, se usa el promedio simple de ambos; si sube o se mantiene, el actual. 2.380 × 1,30 = 3.094. |
| Una actualización por lista | Cada recepción crea una actualización por cada lista con políticas, y se procesan en orden de recepción por presentación: si una falla, las siguientes de esa lista y presentación esperan. |
| Resolver | Una actualización `PENDING` o `FAILED` se puede resolver con un motivo: queda `RESOLVED`, no cambia precios y libera las siguientes. Las que ya terminaron no se resuelven. |

[Empezar → paso 01](01-consultar-datos.md)
