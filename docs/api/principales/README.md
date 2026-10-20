# API principales de SIO

[← Índice](../index.md)

Esta sección reúne, por módulo funcional, **solo las operaciones de alto valor** que el frontend necesita para construir las funcionalidades del negocio. No sustituye a las fichas técnicas de los 12 microservicios ([índice de servicios](../index.md#api-por-microservicio)), donde están las 411 operaciones con todos sus parámetros, cuerpos, ejemplos y códigos: aquí cada funcionalidad responde cuatro preguntas y enlaza a la ficha detallada.

| Pregunta | Qué encontrarás |
|---|---|
| ¿Qué puede hacer el usuario? | La funcionalidad en términos del negocio |
| ¿Qué API debe consumir el frontend? | Método, URL completa de Render (entorno de desarrollo), permiso y parámetros relevantes |
| ¿Qué necesita antes? | Identificadores, configuración previa y dependencias con otros módulos |
| ¿Cómo sabe que funcionó? | Código HTTP, campos de la respuesta y errores que debe tratar |

Una misma operación puede aparecer en varios módulos (por ejemplo, la búsqueda de productos con existencias sirve a Ventas y a Inventario), pero su ficha detallada es una sola.

## Módulos

| Módulo | Qué cubre | API principales |
|---|---|---|
| [6.1 Acceso y contexto operativo](acceso-y-contexto-operativo.md) | Login, renovación y cierre de sesión, identificar al usuario, membresías, empresas y sucursales con acceso efectivo, selección de contexto | 6 |
| [6.2 Administración empresarial](administracion-empresarial.md) | Empresas, sucursales, usuarios de la empresa, asignación de sucursales, estado de membresías, auditoría y trazabilidad, numeración de documentos | 21 |
| [6.3 Gestión de clientes](gestion-de-clientes.md) | Identidades de personas y organizaciones, clientes de la empresa | 9 |
| [6.4 Gestión de proveedores](gestion-de-proveedores.md) | Proveedores de la empresa y lo que Compras exige de ellos | 9 |
| [6.5 Productos y precios](productos-y-precios.md) | Catálogo global, adopción por la empresa, impuesto de compra, listas de precios, precios, políticas de ganancia | 20 |
| [6.6 Ventas](ventas.md) | Borrador, líneas con lista de precios elegida, disponibilidad, confirmación, consulta, anulación | 14 |
| [6.7 Compras](compras.md) | Borrador, líneas con costo, impuestos, confirmación, recepción física, estado, anulación | 13 |
| [6.8 Inventario](inventario.md) | Existencias por empresa y sucursal, productos con disponibilidad, kardex, ajustes, conteos, evolución | 14 |
| [6.9 Reportes](reportes.md) | Productos más vendidos, ventas por sucursal, compras del período, evolución de existencias, indicadores | 10 |

## Convenciones de esta sección

- **URL completa**: se indica la del entorno de desarrollo en Render. Geography y Payment Reference no usan el prefijo `/api/v1`; los demás servicios sí.
- **Cabeceras**: todas las operaciones llevan `Authorization: Bearer <ACCESS_TOKEN>`. Las que envían cuerpo llevan `Content-Type: application/json`. Las confirmaciones, recepciones y anulaciones de Sales y Purchase exigen además `Idempotency-Key` (UUID generado por el frontend y reutilizado en los reintentos). Ver [Autenticación](../guias/autenticacion.md).
- **Permisos**: se escriben completos (`perm:{servicio}:{recurso}:{accion}`) y se leen de `resource_access["sio-api"].roles` del token ([Permisos](../guias/permisos.md)). Además del permiso, casi todas las operaciones de empresa exigen membresía `ACTIVE` en la empresa y, cuando hay sucursal, asignación `ACTIVE` a ella.
- **Identificadores**: cada parámetro enlaza a su guía en [parametros/](../parametros/README.md), donde está la consulta exacta que lo entrega y el campo del que se copia.
- **Versionado optimista**: las operaciones de modificación envían `version` (el valor recibido en la última lectura). Un `409 VERSION_CONFLICT` significa que alguien modificó el recurso: vuelve a leerlo y repite.
- **Ejemplos completos**: los flujos de extremo a extremo con JSON reales están en [ejemplos/](../ejemplos/README.md).
- **Operaciones internas**: algunas llamadas entre servicios (aplicar entradas y salidas de inventario, solicitar actualizaciones automáticas de precio, registrar eventos de auditoría) exigen una cuenta técnica y **no deben invocarse desde el frontend**. Se mencionan aquí únicamente para explicar los efectos de las operaciones públicas.
