# Datos del ejercicio 4 (ficticios)

Todos los datos son **ficticios** y sus identificadores son fijos para que la documentación sea estable. En la prueba automática, Operational Context, Commercial Relationship, Product Catalog, Party Identity, e Inventory se simulan con estos datos.

| Dato | Valor | Interpretación |
| --- | --- | --- |
| Empresa | `d15a0000-0000-4000-8000-000000000001` | Empresa ficticia (moneda COP); todos los usuarios de prueba son miembros `ACTIVE`. |
| Sucursal principal | `d15b0000-0000-4000-8000-000000000001` | Almacén ficticio en Bogotá; todos los usuarios de prueba están asignados a ella. |
| Cliente persona | `d15c0000-0000-4000-8000-000000000001` | Ana Ficticia Pérez (`ACTIVE`), identificada como CC 1020304050. |
| Cliente organización | `d15c0000-0000-4000-8000-000000000002` | Tiendas Ficticias S.A.S. (`ACTIVE`), identificada como NIT 900123456. |
| Arroz 500 g | `d15d0000-0000-4000-8000-000000000001` | Vendible, con control de inventario; 1000 unidades a costo 1000. |
| Unidad de arroz | `d15e0000-0000-4000-8000-000000000002` | Presentación de factor 1 del arroz (toda venta indica su presentación). |
| Caja x12 | `d15e0000-0000-4000-8000-000000000001` | Presentación de venta del arroz: 12 unidades base. |
| Aceite 1 L | `d15d0000-0000-4000-8000-000000000002` | Vendible, con control de inventario; 1000 unidades a costo 6000. |
| Unidad de aceite | `d15e0000-0000-4000-8000-000000000003` | Presentación de factor 1 del aceite. |
| Servicio de instalación | `d15d0000-0000-4000-8000-000000000003` | Vendible pero **sin** control de inventario (no se puede vender en esta fase). |
| Lista de precios general (predeterminada) | `d15f0000-0000-4000-8000-000000000003` | Unidad de arroz a 1500, caja x12 a 18000 y unidad de aceite a 9000: cada presentación con su precio explícito. |
| Lista de precios mayorista | `d15f0000-0000-4000-8000-000000000001` | Caja x12 del arroz a 16000; unidad de aceite a 8500. |
| Lista de precios temporada | `d15f0000-0000-4000-8000-000000000002` | Sin precios para estos productos. |
