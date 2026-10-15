# Datos del ejercicio 3 (ficticios)

Todos los datos son **ficticios** y sus identificadores son fijos para que la documentación sea estable. En la prueba automática, Operational Context, Commercial Relationship, Product Catalog, Party Identity, Payment Reference e Inventory se simulan con estos datos.

| Dato | Valor | Interpretación |
| --- | --- | --- |
| Empresa | `d14a0000-0000-4000-8000-000000000001` | Empresa ficticia (moneda COP); todos los usuarios de prueba son miembros `ACTIVE`. |
| Sucursal principal | `d14b0000-0000-4000-8000-000000000001` | Bodega ficticia; todos los usuarios de prueba están asignados a ella. |
| Proveedor | `d14c0000-0000-4000-8000-000000000001` | Distribuidora Ficticia S.A.S. (`ACTIVE`), identificada como NIT 900123456. |
| Condición de pago | `d14c0000-0000-4000-8000-000000000003` | Contado (`CASH`) en COP del proveedor: la única admitida en el MVP (spec 020). |
| Condición a crédito | `d14c0000-0000-4000-8000-000000000006` | Crédito a 30 días del proveedor: existe, pero no se puede usar en el MVP. |
| Medio de pago | `d14c0000-0000-4000-8000-000000000011` | Efectivo (`CASH`, `ACTIVE`) en Payment Reference: referencia declarativa, no un pago. |
| Arroz 500 g | `d14d0000-0000-4000-8000-000000000001` | Producto con control de inventario (código 000045); unidad base `UND`. |
| Caja x12 | `d14e0000-0000-4000-8000-000000000001` | Presentación de compra del arroz: 12 unidades base. |
| Unidad del arroz | `86d18f28-13ae-5655-8f1e-48e6231acaa8` | Presentación de factor 1 del arroz (toda línea indica su presentación). |
| Unidad del aceite | `0e2be67b-ba11-51b8-9dd7-04739ec7d8d4` | Presentación de factor 1 del aceite. |
| Aceite 1 L | `d14d0000-0000-4000-8000-000000000002` | Producto con control de inventario (código 000046). |
| Servicio de transporte | `d14d0000-0000-4000-8000-000000000003` | Producto **sin** control de inventario (no se puede comprar en esta fase). |
