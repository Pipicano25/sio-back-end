# Documentación de las API de SIO

Documentación técnica de los 12 microservicios de SIO desplegados en Render (entorno de desarrollo `siodev`), dirigida al desarrollador frontend y a cualquier equipo que integre SIO mediante API HTTP. Esta carpeta Markdown se consulta directamente en GitHub y es la única ubicación oficial de la documentación de integración.

> **Estado:** completa. Las 411 operaciones de los 12 microservicios desplegados en Render están documentadas y contrastadas con el código y con los contratos OpenAPI (ver el [registro de avance](#registro-de-avance)). Los datos que no pudieron confirmarse están marcados **NO VERIFICADO** en cada documento.

**Fuente de verdad:** el código fuente de cada microservicio (routers, modelos Pydantic, permisos declarados), las especificaciones en `specs/` y los contratos OpenAPI publicados en `/openapi.json` de cada servicio. Cuando un dato no pudo confirmarse se marca expresamente **NO VERIFICADO**.

## Comienza aquí

| Documento | Contenido |
|---|---|
| [Primeros pasos](guias/primeros-pasos.md) | URLs base, cabeceras comunes, flujo de integración recomendado, arranque en frío de Render |
| [Autenticación con Keycloak](guias/autenticacion.md) | Realm `siodev`, cliente `sio-web`, Authorization Code + PKCE, tokens, renovación, cierre de sesión, qué validan las API |
| [Permisos y contexto operativo](guias/permisos.md) | Formato `perm:{servicio}:{recurso}:{accion}`, comodines `all`, grupos del realm, membresías por empresa y sucursal, aislamiento multi-tenant |
| [Errores y diagnóstico](guias/errores.md) | Problem Details, `code`, `trace_id`, códigos HTTP por tipo de error en cada servicio |
| [API principales por módulo](principales/README.md) | Nueve módulos funcionales (acceso y contexto operativo, administración empresarial, clientes, proveedores, productos y precios, ventas, compras, inventario, reportes): qué puede hacer el usuario, qué API consumir, qué necesita antes y cómo saber que funcionó |
| [Cómo obtener cada identificador](parametros/README.md) | Diecisiete guías reutilizables: `company_id`, `branch_id`, `company_customer_id`, `company_supplier_id`, `company_product_id`, `company_product_presentation_id`, `global_product_id`, `global_product_presentation_id`, `payment_method_id`, `person_identity_id`, `organization_identity_id`, `application_user_id`, `price_list_id`, `policy_id`, `sale_id`, `purchase_id` y los geográficos |
| [Ejemplos de flujos completos](ejemplos/README.md) | Crear una venta, registrar una compra, consultar inventario, configurar una lista de precios, crear una empresa y una sucursal |

## API por microservicio

| # | Microservicio | Base URL (Render, desarrollo) | Documentación |
|---|---|---|---|
| 1 | Geography | `https://sio-geography-dev.onrender.com` | [Ver referencia](servicios/geography.md) |
| 2 | Party Identity | `https://sio-party-identity-dev.onrender.com/api/v1` | [Ver referencia](servicios/party-identity.md) |
| 3 | Product Catalog | `https://sio-product-catalog-dev.onrender.com/api/v1` | [Ver referencia](servicios/product-catalog.md) |
| 4 | Operational Context | `https://sio-operational-context-dev.onrender.com/api/v1` | [Ver referencia](servicios/operational-context.md) |
| 5 | Payment Reference | `https://sio-payment-reference-dev.onrender.com` | [Ver referencia](servicios/payment-reference.md) |
| 6 | Commercial Relationship | `https://sio-commercial-relationship-dev.onrender.com/api/v1` | [Ver referencia](servicios/commercial-relationship.md) |
| 7 | Purchase | `https://sio-purchase-dev.onrender.com/api/v1` | [Ver referencia](servicios/purchase.md) |
| 8 | Sales | `https://sio-sales-dev.onrender.com/api/v1` | [Ver referencia](servicios/sales.md) |
| 9 | Inventory | `https://sio-inventory-dev.onrender.com/api/v1` | [Ver referencia](servicios/inventory.md) |
| 10 | Audit | `https://sio-audit-dev.onrender.com/api/v1` | [Ver referencia](servicios/audit.md) |
| 11 | Product Inventory Query | `https://sio-product-inventory-query-dev.onrender.com/api/v1` | [Ver referencia](servicios/product-inventory-query.md) |
| 12 | Business Reporting | `https://sio-business-reporting-dev.onrender.com/api/v1` | [Ver referencia](servicios/business-reporting.md) |

Geography y Payment Reference **no** incluyen `/api/v1` en su URL base; los otros diez sí. Las rutas `/health/live`, `/health/ready`, `/docs` y `/openapi.json` cuelgan siempre del dominio, sin prefijo. Las URL se confirmaron en vivo el 2026-10-19: los 12 servicios respondieron `200` en `/openapi.json`.

### ¿Para qué sirve cada servicio?

| Servicio | Funcionalidad |
|---|---|
| Geography | Países, divisiones administrativas y ciudades (datos globales) |
| Party Identity | Identidades de personas y organizaciones |
| Product Catalog | Catálogo global de productos, marcas, presentaciones y unidades |
| Operational Context | Empresas, sucursales, usuarios de aplicación, membresías y acceso operativo |
| Payment Reference | Tipos y condiciones de pago de referencia (datos globales) |
| Commercial Relationship | Clientes, proveedores, productos adoptados por la empresa, listas de precios y políticas |
| Purchase | Compras, detalles, impuestos y ciclo de vida de la compra |
| Sales | Ventas, detalles, pagos y ciclo de vida de la venta |
| Inventory | Existencias, entradas, salidas, ajustes, conteos y políticas de inventario |
| Audit | Eventos de auditoría y trazabilidad |
| Product Inventory Query | Consultas consolidadas de productos, precios y existencias por empresa y sucursal |
| Business Reporting | Reportes de ventas, compras e inventario por empresa y sucursal, en JSON y CSV |

## Fuente técnica de verdad

Cada servicio expone su contrato OpenAPI en `/openapi.json` y la documentación Swagger en `/docs` **si está habilitada** (`SIO_DOCS_ENABLED=true`; el 2026-10-19 lo estaba en los 12 servicios de Render). Cada ficha de esta carpeta se construye cruzando ese contrato con el código, porque el OpenAPI generado no incluye reglas de negocio, efectos secundarios ni dependencias entre servicios.

**Documentación pública ≠ API sin autenticación:** salvo `/health/*`, `/docs` y `/openapi.json`, todas las rutas exigen un Access Token Bearer válido y el permiso declarado por la operación.

## Clasificación de seguridad usada en toda la documentación

| Clase | Significado |
|---|---|
| `READ` | Solo consulta. No modifica información. |
| `WRITE` | Crea o modifica información de la empresa o de la plataforma. |
| `HIGH_RISK` | Operación sensible: elimina, inactiva, anula, cambia estados irreversibles, afecta saldos de inventario, precios, cartera o accesos de usuarios. |

Para cada operación `WRITE` y `HIGH_RISK`, la ficha del servicio indica qué datos pueden modificarse y qué efectos secundarios produce.

## Registro de avance

Cobertura contra los contratos OpenAPI desplegados en Render el 2026-10-19: **411 operaciones** en total, incluidas las dos rutas `/health/*` de cada servicio.

| Documento | Estado | Operaciones en OpenAPI desplegado | Operaciones documentadas |
|---|---|---|---|
| index.md | Hecho | — | — |
| guias/primeros-pasos.md | Hecho | — | — |
| guias/autenticacion.md | Hecho | — | — |
| guias/permisos.md | Hecho | — | — |
| guias/errores.md | Hecho | — | — |
| parametros/* (17 guías) | Hecho | — | — |
| ejemplos/* (5 flujos) | Hecho | — | — |
| principales/* (índice + 9 módulos) | Hecho | — | — |
| servicios/geography.md | Hecho | 17 | 17 |
| servicios/party-identity.md | Hecho | 54 | 54 |
| servicios/product-catalog.md | Hecho | 104 | 104 |
| servicios/operational-context.md | Hecho | 33 | 33 |
| servicios/payment-reference.md | Hecho | 12 | 12 |
| servicios/commercial-relationship.md | Hecho | 76 | 76 |
| servicios/purchase.md | Hecho | 24 | 24 |
| servicios/sales.md | Hecho | 23 | 23 |
| servicios/inventory.md | Hecho | 38 | 38 |
| servicios/audit.md | Hecho | 10 | 10 |
| servicios/product-inventory-query.md | Hecho | 10 | 10 |
| servicios/business-reporting.md | Hecho | 10 | 10 |
| **Total** | | **411** | **411** |

## Cobertura de ejemplos

Revisión individual de las 411 operaciones realizada el 2026-10-19 (auditoría automática sección por sección más validación de cada JSON contra el contrato OpenAPI desplegado y contra los modelos Pydantic del propio servicio):

| Servicio | Operaciones documentadas | Con ejemplo de solicitud validado | Con cuerpo de solicitud (de las que lo admiten) | Con ejemplo de respuesta validado | Operaciones con información NO VERIFICADA |
|---|---|---|---|---|---|
| Audit | 10 | 10 | 2/2 | 10 | 0 |
| Business Reporting | 10 | 10 | 0/0 | 10 | 0 |
| Commercial Relationship | 76 | 76 | 51/51 | 76 | 0 |
| Geography | 17 | 17 | 6/6 | 17 | 0 |
| Inventory | 38 | 38 | 19/19 | 38 | 0 |
| Operational Context | 33 | 33 | 18/18 | 33 | 0 |
| Party Identity | 54 | 54 | 32/32 | 54 | 0 |
| Payment Reference | 12 | 12 | 6/6 | 12 | 0 |
| Product Catalog | 104 | 104 | 67/67 | 104 | 1 (introducción de activos, ops. 96–102: disponibilidad en Render de la ruta pública de imágenes) |
| Product Inventory Query | 10 | 10 | 0/0 | 10 | 0 |
| Purchase | 24 | 24 | 12/12 | 24 | 0 |
| Sales | 23 | 23 | 10/10 | 23 | 0 |
| **Total** | **411** | **411** | **223/223** | **411** | **1** |

Criterios: un *ejemplo de solicitud* es un bloque cURL con método, URL completa de Render y cabeceras; un *ejemplo de respuesta* es un JSON conforme al modelo real o, cuando la operación no devuelve cuerpo, la indicación explícita `204 No Content: sin cuerpo` (o contenido no JSON para los CSV y las imágenes). Las operaciones con información NO VERIFICADA tienen ejemplos válidos, pero algún dato de su sección (un comportamiento, un valor por defecto o un efecto) no pudo confirmarse en el código y está marcado como tal. El 2026-10-19 se volvieron a revisar contra el código las 16 operaciones que tenían esa marca y se resolvieron 15; la única pendiente depende del despliegue en Render. Fuera de las fichas, las marcas NO VERIFICADO restantes dependen de configuración externa que no puede consultarse desde el repositorio: la guía de autenticación (valores en Render de `SIO_WEB_REDIRECT_URI`, `SIO_WEB_ORIGIN`, `SIO_WEB_DIRECT_ACCESS_GRANTS_ENABLED`, duración real de los tokens, usuarios de prueba e issuer), la guía de permisos (asignación real por grupo y membresías en Render), la guía de errores (campos desconocidos modelo a modelo, se indica por operación) y las dos referencias al `sio-web` en el módulo de acceso.

## Alcance de esta documentación

Incluye únicamente documentación Markdown de consumo funcional de las API: fichas técnicas, guías, identificadores, módulos principales y ejemplos. No incluye manuales de usuario, despliegues ni herramientas de publicación. No se ejecutaron operaciones de escritura contra las API, ni se modificaron bases de datos, Keycloak o Render para producirla.
