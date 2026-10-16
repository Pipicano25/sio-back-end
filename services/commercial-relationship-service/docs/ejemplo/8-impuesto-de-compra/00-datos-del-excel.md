# Datos del ejercicio — Ejercicio 8 — Tasa de impuesto de compra del producto

[← Orden del ejercicio](ORDEN.md)

> **Datos reales del sistema anterior.** Los productos son filas de `docs/CAMPOS PRODUCTOS.xlsx` (se cita la fila de cada uno). Mapeo de columnas: [../mapeo-campos-excel.md](../mapeo-campos-excel.md). La empresa y los datos marcados como **ficticios** son inventados.

## Datos usados

| Dato | Valor |
| --- | --- |
| Fuente | `docs/CAMPOS PRODUCTOS.xlsx`, hoja `Hoja1` (encabezados en la fila 2) |
| Fila 40 | `Código` 000045 · ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED |
| Fila 16577 | `Código` 022315 · IRBESARTAN+HIDROCLOROTIAZIDA (IRBESARTAN/HCT) 150+12.5MG TABLETA CAJAX30MK |
| Tasas | 19 % y 0 % son **ficticias**: la fuente no informa impuestos de compra y SIO no asigna ninguna tasa por su cuenta. |
| Empresa | DROGUERÍA IMPUESTOS FICTICIA S.A.S. (**ficticia**). |

## Cómo se interpretan

| Tema | Decisión |
| --- | --- |
| Sin configurar ≠ 0 % | `null` significa que nadie definió la tasa; `0` es una tasa válida (por ejemplo, un producto exento). Solo con tasa se puede confirmar una compra del producto. |
| Permiso propio | La tasa se modifica con `company_product_purchase_taxes:update`, no con el `PUT` del producto. Solo administradores y supervisores. |
| Sin efecto en compras confirmadas | Cada línea de compra congela su tasa al confirmar; cambiar la tasa del producto no modifica compras históricas. |

[Empezar → paso 01](01-consultar-datos.md)
