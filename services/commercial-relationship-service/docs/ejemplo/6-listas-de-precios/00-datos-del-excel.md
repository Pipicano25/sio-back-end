# Datos del ejercicio — Ejercicio 6 — Listas de precios y precio aplicable

[← Orden del ejercicio](ORDEN.md)

> **Datos reales del sistema anterior.** Los productos son filas de `docs/CAMPOS PRODUCTOS.xlsx` (se cita la fila de cada uno). Mapeo de columnas: [../mapeo-campos-excel.md](../mapeo-campos-excel.md). La empresa y los datos marcados como **ficticios** son inventados.

## Datos usados

| Dato | Valor |
| --- | --- |
| Fuente | `docs/CAMPOS PRODUCTOS.xlsx`, hoja `Hoja1` (encabezados en la fila 2) |
| Fila 16577 | `Código` 022315 · `Nombre` IRBESARTAN+HIDROCLOROTIAZIDA (IRBESARTAN/HCT) 150+12.5MG TABLETA CAJAX30MK · `Código Barras 1` 7702057716226 · `Precio Lista 10` **30420** (único precio por lista de toda la fuente) |
| Fila 40 | `Código` 000045 · ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED · sin precios por lista |
| Precios ficticios | Precio simple del acetaminofén 12000.00 COP y nuevo precio del irbesartán 31500.00 COP desde 2099 son **ficticios**. |
| Empresa | DROGUERÍA PRECIOS FICTICIA S.A.S. (**ficticia**), registrada en Operational Context. |

## Cómo se interpretan

| Tema | Decisión |
| --- | --- |
| Lista | `Precio Lista 10` → una `PriceList` con código `LISTA-10`; cada columna `Precio Lista N` sería otra lista. El precio concreto es un `PriceListItem`. |
| Moneda | La lista fija la moneda de sus precios (`COP`, 2 decimales) y no se puede cambiar. |
| Historia | Un precio en vigencia no se reescribe: se cierra o se cambia con `change-price`, que cierra el vigente y crea el nuevo en una sola operación. |
| Respaldo | Sin lista indicada y sin precio en la predeterminada se usa `sale_price` del producto empresarial; con una lista explícita sin precio **no** hay respaldo (aclaración 2). |

[Empezar → paso 01](01-consultar-datos.md)
