# Datos del ejercicio 7 (ficticios)

No existe una fuente del sistema anterior para movimientos de inventario: todos los datos son **ficticios** y sus identificadores son fijos para que la documentación sea estable. En la prueba automática, Operational Context y Commercial Relationship se simulan con estos datos.

| Dato | Valor | Interpretación |
| --- | --- | --- |
| Empresa | `d44a0000-0000-4000-8000-000000000001` | Empresa ficticia; todos los usuarios de prueba son miembros `ACTIVE`. |
| Sucursal | `d44b0000-0000-4000-8000-000000000001` | Bodega principal ficticia (`ACTIVE`). |
| Usuario operativo | `d44c0000-0000-4000-8000-000000000001` | Usuario de la empresa que confirmó el documento en Purchase o Sales. |
| Arroz 500 g | `d44d0000-0000-4000-8000-000000000001` | Producto empresarial con control de inventario; unidad base: unidad. |
| Aceite 1 L | `d44d0000-0000-4000-8000-000000000002` | Producto empresarial con control de inventario; unidad base: unidad. |
| Servicio de domicilio | `d44d0000-0000-4000-8000-000000000003` | Producto empresarial **sin** control de inventario. |
| Sucursal sin asignar | `d44b0000-0000-4000-8000-000000000002` | Sucursal ficticia `ACTIVE` sin usuarios asignados. |
| Compra | `d44e0000-0000-4000-8000-000000000001` | Documento ficticio de Purchase. |
| Venta | `d44e0000-0000-4000-8000-000000000002` | Documento ficticio de Sales. |
