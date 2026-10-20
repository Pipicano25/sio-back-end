# Flujos de integración

[← Índice](../index.md)

Recorridos completos, paso a paso, con las rutas reales de Render y enlaces a la ficha de cada operación y a la guía de cada parámetro. Los identificadores de los ejemplos son ficticios.

| Flujo | Servicios implicados | Clase de la operación final |
|---|---|---|
| [Crear y confirmar una venta](crear-venta.md) | Operational Context, Commercial Relationship, Product Inventory Query, Payment Reference, Sales | `HIGH_RISK` (descuenta inventario) |
| [Registrar, confirmar y recibir una compra](registrar-compra.md) | Operational Context, Commercial Relationship, Payment Reference, Purchase | `HIGH_RISK` (ingresa inventario) |
| [Consultar inventario](consultar-inventario.md) | Operational Context, Product Inventory Query, Inventory | `READ` |
| [Configurar una lista de precios con política de ganancia](configurar-lista-precios.md) | Operational Context, Commercial Relationship, Purchase | `HIGH_RISK` (cambia precios de venta) |
| [Crear una empresa, una sucursal y sus usuarios](crear-empresa-y-sucursal.md) | Geography, Party Identity, Operational Context | `HIGH_RISK` (otorga acceso) |

Cada flujo enlaza al módulo correspondiente de [API principales](../principales/README.md), donde cada funcionalidad responde qué puede hacer el usuario, qué API consumir, qué necesita antes y cómo saber que funcionó.

Requisitos comunes: haber iniciado sesión ([Autenticación](../guias/autenticacion.md)) y conocer `company_id` y `branch_id` del usuario ([Primeros pasos](../guias/primeros-pasos.md)).
