# Datos del ejercicio — Ejercicio 7 — Políticas de ganancia de una lista de precios

[← Orden del ejercicio](ORDEN.md)

> **Datos reales del sistema anterior.** Los productos son filas de `docs/CAMPOS PRODUCTOS.xlsx` (se cita la fila de cada uno). Mapeo de columnas: [../mapeo-campos-excel.md](../mapeo-campos-excel.md). La empresa y los datos marcados como **ficticios** son inventados.

## Datos usados

| Dato | Valor |
| --- | --- |
| Fuente | `docs/CAMPOS PRODUCTOS.xlsx`, hoja `Hoja1` (encabezados en la fila 2) |
| Fila 40 | `Código` 000045 · ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED |
| Fila 16577 | `Código` 022315 · IRBESARTAN+HIDROCLOROTIAZIDA (IRBESARTAN/HCT) 150+12.5MG TABLETA CAJAX30MK |
| Porcentajes | 15 %, 20 % y 50 % son **ficticios**: la fuente no tiene políticas de ganancia. |
| Empresa y lista | DROGUERÍA POLÍTICAS FICTICIA S.A.S. y la lista `PUBLICO` son **ficticias**. |

## Cómo se interpretan

| Tema | Decisión |
| --- | --- |
| Política | Agrupa presentaciones de una lista con un mismo porcentaje de recargo: `precio = costo real de compra × (1 + porcentaje / 100)`. Una lista puede tener varias. |
| Pertenencia | Una presentación está a lo sumo en una política de la misma lista; puede estar en políticas de otras listas. La base lo garantiza también ante operaciones simultáneas. |
| Historial | Cambiar el porcentaje o las presentaciones no reescribe nada: cierra la vigencia anterior y abre otra. Cada recepción usa las condiciones vigentes en el momento en que se recibió. |
| Sin efecto inmediato | Ninguna operación de políticas modifica precios (RC-021-2). |

[Empezar → paso 01](01-consultar-datos.md)
