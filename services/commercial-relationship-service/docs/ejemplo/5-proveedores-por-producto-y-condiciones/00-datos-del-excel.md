# Datos del ejercicio — Ejercicio 5 — Proveedores por producto y condiciones de pago

[← Orden del ejercicio](ORDEN.md)

> **Datos reales del sistema anterior.** Los productos son filas de `docs/CAMPOS PRODUCTOS.xlsx` (se cita la fila de cada uno). Mapeo de columnas: [../mapeo-campos-excel.md](../mapeo-campos-excel.md). La empresa y los datos marcados como **ficticios** son inventados.

## Datos usados

| Dato | Valor |
| --- | --- |
| Fuente | `docs/CAMPOS PRODUCTOS.xlsx`, hoja `Hoja1` (encabezados en la fila 2) |
| Fila 40 | `Código` 000045 · `Nombre Proveedor` ACETAMINOFEN 500MG TABLETA CAJAX100 SIEGFRIED · `Unidad Medida` CAJA |
| Proveedor | LABORATORIO PROVEEDOR FICTICIO S.A.S. (**ficticio**, NIT ficticio). |
| Costos, mínimos y condiciones | **Ficticios**: costo negociado 12500.5000 COP, mínimo 10 cajas, crédito a 30 días con cupo de 5 000 000 COP. La fuente no trae costos por proveedor (`Costo` vacío). |
| Empresa | DROGUERÍA COMPRAS FICTICIA S.A.S. (**ficticia**), registrada en Operational Context. |

## Cómo se interpretan

| Tema | Decisión |
| --- | --- |
| Código del proveedor | `Nombre Proveedor` → `supplier_product_code`: así llama el proveedor al producto. |
| Unidad de compra | Es siempre la **unidad base** del producto global (sin conversión de unidades en el MVP). |
| Relación por presentación | La relación general (sin presentación) y la de la caja x100 coexisten; se rechaza repetir la misma combinación proveedor + producto + presentación entre las `ACTIVE` (aclaración 3). |
| Proveedor activo | Solo un proveedor `ACTIVE` recibe productos y condiciones nuevos (FR-021, FR-031): si está inactivo o bloqueado se reactiva o desbloquea antes. |
| Tipo de condición | Se lee de Payment Reference en cada validación y no se copia: contado exige 0 días; crédito y financiación, más de 0. |

[Empezar → paso 01](01-consultar-datos.md)
