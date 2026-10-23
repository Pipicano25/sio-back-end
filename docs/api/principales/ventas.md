# 6.6 Ventas

[← API principales](README.md) · [← Índice](../index.md)

Operaciones con las que un vendedor registra una venta **de contado** en una sucursal: elige el cliente, busca los productos con su precio y sus existencias, arma la venta en borrador línea por línea, la confirma (Sales descuenta las existencias en Inventory, fija los costos FIFO y asigna el número del documento) y, si hace falta, la anula. La venta vive en [Sales](../servicios/sales.md); el cliente, los productos y los precios se consultan en los servicios que los administran y Sales los valida al guardar y al confirmar.

| Parte | Servicio | Qué aporta a la venta |
|---|---|---|
| **Cliente** | [Commercial Relationship](../servicios/commercial-relationship.md) | `company_customer_id` ([customer_id](../parametros/customer-id.md)); debe estar `ACTIVE` y tener identificación |
| **Productos, presentaciones y precios** | [Product Inventory Query](../servicios/product-inventory-query.md) y [Commercial Relationship](../servicios/commercial-relationship.md) | `company_product_id`, `company_product_presentation_id`, `price_list_id` y el precio vigente por presentación |
| **Método de pago** | [Payment Reference](../servicios/payment-reference.md) | `payment_method_id` ([payment_method_id](../parametros/payment-method-id.md)) |
| **Venta** | [Sales](../servicios/sales.md) | `sale_id` ([sale_id](../parametros/sale-id.md)), líneas, totales, confirmación, anulación y numeración |

Flujo de uso paso a paso con respuestas completas: [Crear una venta](../ejemplos/crear-venta.md).

| # | API | Método y URL | Permiso | Referencia técnica |
|---|---|---|---|---|
| 1 | Buscar el cliente de la venta | `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-customers` | `perm:commercial-relationship:company_customers:read` | [CR 13](../servicios/commercial-relationship.md#13-get-companiescompany_idcompany-customers) |
| 2 | Buscar productos con precio y existencias en la sucursal | `GET https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/product-overviews` | `perm:product-inventory-query:product_overviews:read` (+ `perm:commercial-relationship:price_list_items:read` para ver precios y `perm:product-inventory-query:stock:read` para ver existencias) | [PIQS 4](../servicios/product-inventory-query.md#4-get-companiescompany_idbranchesbranch_idproduct-overviews) |
| 3 | Consultar las listas de precios de la empresa | `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-lists` | `perm:commercial-relationship:price_lists:read` | [CR 46](../servicios/commercial-relationship.md#46-get-companiescompany_idprice-lists) |
| 4 | Consultar los precios vigentes de una presentación | `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-list-items` | `perm:commercial-relationship:price_list_items:read` | [CR 52](../servicios/commercial-relationship.md#52-get-companiescompany_idprice-list-items) |
| 5 | Consultar los métodos de pago | `GET https://sio-payment-reference-dev.onrender.com/global-payment-methods` | `perm:payment-reference:global_payment_methods:read` | [PR 9](../servicios/payment-reference.md#9-get-global-payment-methods) |
| 6 | Crear la venta en borrador | `POST https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales` | `perm:sales:sales:create` (+ `perm:sales:sale_details:create` si se envían líneas) | [Sales 3](../servicios/sales.md#3-post-companiescompany_idsales) |
| 7 | Agregar una línea a la venta | `POST https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}/details` | `perm:sales:sale_details:create` | [Sales 7](../servicios/sales.md#7-post-companiescompany_idsalessale_iddetails) |
| 8 | Modificar una línea de la venta | `PUT https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}/details/{detail_id}` | `perm:sales:sale_details:update` | [Sales 9](../servicios/sales.md#9-put-companiescompany_idsalessale_iddetailsdetail_id) |
| 9 | Eliminar una línea de la venta | `DELETE https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}/details/{detail_id}` | `perm:sales:sale_details:delete` | [Sales 10](../servicios/sales.md#10-delete-companiescompany_idsalessale_iddetailsdetail_id) |
| 10 | Consultar la venta con sus líneas y totales | `GET https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}` | `perm:sales:sales:read` | [Sales 5](../servicios/sales.md#5-get-companiescompany_idsalessale_id) |
| 11 | Verificar la disponibilidad antes de confirmar | `GET https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}/availability` | `perm:sales:sales:read` | [Sales 15](../servicios/sales.md#15-get-companiescompany_idsalessale_idavailability) |
| 12 | Confirmar la venta | `POST https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}/confirmation` | `perm:sales:sales:update` | [Sales 11](../servicios/sales.md#11-post-companiescompany_idsalessale_idconfirmation) |
| 13 | Listar y buscar las ventas | `GET https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales` | `perm:sales:sales:read` | [Sales 4](../servicios/sales.md#4-get-companiescompany_idsales) |
| 14 | Anular una venta | `POST https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}/cancellation` | `perm:sales:sales:delete` | [Sales 12](../servicios/sales.md#12-post-companiescompany_idsalessale_idcancellation) |

Operaciones relacionadas que no se consideran principales (ver las fichas): modificar el encabezado de un borrador (sucursal, cliente, método de pago u observaciones; Sales 6), listar solo las líneas de una venta (Sales 8), consultar las operaciones de confirmación o anulación de una venta y una operación concreta (Sales 13 y 14; se usan únicamente para dar seguimiento a una operación que quedó `PENDING`, ver la [API 12](#12-confirmar-la-venta)), administrar las secuencias de numeración (Sales 16–21, documentadas como [API 18 a 21 de Administración empresarial](administracion-empresarial.md#18-consultar-las-secuencias-de-numeración)) y los agregados de ventas que consume Reportes (Sales 22 y 23, ver [Reportes](reportes.md)).

Orden habitual de una venta: [API 1](#1-buscar-el-cliente-de-la-venta) (cliente) → [API 2](#2-buscar-productos-con-precio-y-existencias-en-la-sucursal) (productos con precio y existencias en la sucursal) → si el vendedor quiere ofrecer otro precio, [API 3](#3-consultar-las-listas-de-precios-de-la-empresa) y [API 4](#4-consultar-los-precios-vigentes-de-una-presentación) → [API 5](#5-consultar-los-métodos-de-pago) (método de pago) → [API 6](#6-crear-la-venta-en-borrador) → [API 7](#7-agregar-una-línea-a-la-venta), [API 8](#8-modificar-una-línea-de-la-venta) y [API 9](#9-eliminar-una-línea-de-la-venta) mientras se arma → [API 10](#10-consultar-la-venta-con-sus-líneas-y-totales) y [API 11](#11-verificar-la-disponibilidad-antes-de-confirmar) para revisar → [API 12](#12-confirmar-la-venta). Después: [API 13](#13-listar-y-buscar-las-ventas) para encontrarla y [API 14](#14-anular-una-venta) si hay que anularla.

**Regla de precios aprobada para el frontend.** El precio de cada línea **lo resuelve Sales**, nunca lo escribe el vendedor:

1. La interfaz muestra los precios vigentes de la presentación ordenados **de mayor a menor** (la [API 2](#2-buscar-productos-con-precio-y-existencias-en-la-sucursal) devuelve el de la lista por defecto; la [API 4](#4-consultar-los-precios-vigentes-de-una-presentación) devuelve todos los vigentes para ordenarlos).
2. El vendedor elige uno; la interfaz envía el `price_list_id` de ese precio en la línea.
3. Si no elige ninguno, la línea se envía con `price_list_id: null` y Sales aplica la lista de precios **por defecto** de la empresa.
4. Nunca se envía `unit_price`: Sales responde `422 SALES.VALIDATION_ERROR` con `errors[].code` `UNIT_PRICE_NOT_ALLOWED`. El precio aplicado vuelve en `lines[].unit_price` y la lista en `lines[].price_list_id`; `lines[].price_list_requested` indica si lo eligió el vendedor (`true`) o se aplicó el de la lista por defecto (`false`). Si un precio cambia entre guardar la línea y confirmar, la confirmación responde `409 SALES.PRICES_CHANGED` y la línea debe volver a guardarse (ver la [API 12](#12-confirmar-la-venta)).

**Antes de empezar: configuración obligatoria.** Sin estos requisitos la venta no se puede crear o confirmar:

| Requisito | Quién lo configura | Error si falta |
|---|---|---|
| El vendedor tiene membresía `ACTIVE` en la empresa y asignación `ACTIVE` a la sucursal de la venta | [API 10](administracion-empresarial.md#10-asociar-un-usuario-a-una-empresa-crear-membresía) y [API 12 de Administración empresarial](administracion-empresarial.md#12-asignar-un-usuario-a-una-sucursal) | `403 SALES.BRANCH_ACCESS_DENIED` |
| El token tiene los permisos de Sales que indica cada API, además de `perm:sales:sales:read` para consultar | Keycloak (administrador de la plataforma) | `403 SALES.FORBIDDEN` |
| La empresa tiene al menos una **secuencia de numeración de ventas** activa, de la sucursal o de la empresa | [API 19 de Administración empresarial](administracion-empresarial.md#19-crear-una-secuencia-de-numeración) | `409 SALES.SEQUENCE_NOT_CONFIGURED` al confirmar |
| El cliente está `ACTIVE` y su identidad tiene documento de identificación | [Gestión de clientes](gestion-de-clientes.md) | `409 SALES.REFERENCES_NOT_ELIGIBLE` |
| Cada producto está `ACTIVE`, es vendible y está controlado por inventario; la presentación está `ACTIVE` y es vendible; la presentación tiene precio vigente en la lista elegida o en la lista por defecto | [Productos y precios](productos-y-precios.md) | `409 SALES.REFERENCES_NOT_ELIGIBLE` |
| El método de pago está `ACTIVE` | Catálogo global de Payment Reference ([API 5](#5-consultar-los-métodos-de-pago)) | `409 SALES.REFERENCES_NOT_ELIGIBLE` |
| Hay existencias suficientes en la sucursal (solo al confirmar) | [Inventario](inventario.md) | `409 SALES.INSUFFICIENT_STOCK` |

Convenciones de todo el módulo:

- `TU_ACCESS_TOKEN` es el Access Token de [Acceso y contexto operativo](acceso-y-contexto-operativo.md); los UUID son ficticios y coherentes entre las API de este documento.
- **Alcance actual: ventas de contado.** Sales fija en toda venta `payment_condition_code_snapshot: "CASH"`, `payment_terms_days_snapshot: 0` y `due_date` igual a la fecha de la operación. Enviar `due_date`, `customer_payment_condition_id`, `payment_condition_code_snapshot` o `payment_terms_days_snapshot` responde `422 SALES.VALIDATION_ERROR` con `errors[].code` `PAYMENT_CONDITION_NOT_ALLOWED`; enviar `operation_date` responde `OPERATION_DATE_NOT_ALLOWED` (la fecha la fija Sales con la fecha del día en la zona horaria de la sucursal). Tampoco hay descuentos ni impuestos por línea: `discount_amount` y `tax_amount` solo pueden ser `0` (`DISCOUNT_NOT_ALLOWED`, `TAX_NOT_ALLOWED`).
- Todas las API de Sales con cuerpo JSON **rechazan campos desconocidos** con `422 SALES.VALIDATION_ERROR` y `errors[].code` `UNKNOWN_FIELD`; los campos obligatorios que faltan llegan con `REQUIRED` y los mal formados con `INVALID_FORMAT`. Cada elemento de `errors[]` trae `field` (ruta del campo, p. ej. `lines[0].quantity`), `message`, `code` y, en las líneas, `line_number`.
- Las cantidades e importes se envían como número o como texto (`"3.5"`) y **vuelven siempre como texto**: cantidades y precios unitarios con 4 decimales (`"2.0000"`, `"800.0000"`), importes con 2 (`"1600.00"`) y el factor de la presentación guardado en la línea con 8 (`"1.00000000"`). La cantidad debe ser mayor que cero (`QUANTITY_NOT_POSITIVE`), con máximo 4 decimales (`TOO_MANY_DECIMALS`) y menor que 10<sup>14</sup> (`AMOUNT_OUT_OF_RANGE`); además, cantidad × factor de la presentación no puede superar 4 decimales (`BASE_QUANTITY_PRECISION`). `subtotal = quantity × unit_price` redondeado a 2 decimales y `total = subtotal`.
- Errores comunes a todas las API de Sales (no se repiten en cada tabla): `401` con `{"detail": "Se requiere un token de acceso Bearer"}` u otro `detail` cuando el token falta, venció o no es válido (renovar una vez y reintentar; si falla, volver al login); `403` con `code` `SALES.FORBIDDEN` cuando el token no tiene el permiso indicado o es un token de servicio y no de usuario (mostrar que faltan permisos y el `trace_id`); `400 SALES.MALFORMED_BODY` cuando el cuerpo no es JSON válido; `503 SALES.DEPENDENCY_UNAVAILABLE` cuando la base de datos u otro servicio no responde, con la extensión `dependency` (`database`, `operational-context`, `commercial-relationship`, `product-catalog`, `party-identity`, `inventory` o `payment-reference`) para saber cuál falló (reintentar más tarde; nada se guarda, salvo lo indicado en la [API 12](#12-confirmar-la-venta)). Los demás errores llegan en Problem Details (`application/problem+json`) con `type` `https://sio/errors/sales/<código-en-minúsculas>`, `title`, `status`, `detail`, `instance` (ruta de la solicitud), `code` `SALES.…` y `trace_id`; ver la [guía de errores](../guias/errores.md). Las API 1 a 5 pertenecen a otros servicios y sus errores comunes llevan el prefijo de cada servicio (`COMMERCIAL_RELATIONSHIP.…`, `PRODUCT_INVENTORY_QUERY.…`); los de Payment Reference se indican en la [API 5](#5-consultar-los-métodos-de-pago).
- **Alcance.** Las consultas (API 10, 11 y 13) exigen membresía `ACTIVE` en la empresa; fuera de ese alcance, o si la venta no existe o es de otra empresa, la respuesta es `404 SALES.NOT_FOUND`, igual que si no existiera. Las escrituras (API 6 a 9, 12 y 14) exigen además una **asignación `ACTIVE` a la sucursal de la venta**, con la sucursal y la empresa activas; si falta, `403 SALES.BRANCH_ACCESS_DENIED`. Todas las API de Sales exigen un token de **usuario humano**: un token de cuenta de servicio recibe `403 SALES.FORBIDDEN`.
- **Control de versión.** Toda escritura sobre una venta (API 7, 8, 9, 12 y 14) envía la `version` actual de la venta; si otra persona la cambió antes, la API responde `409 SALES.VERSION_CONFLICT` y el frontend debe volver a leerla con la [API 10](#10-consultar-la-venta-con-sus-líneas-y-totales) y repetir con la nueva `version`. Cada escritura exitosa devuelve la venta completa con la `version` incrementada.
- **Estados.** `DRAFT` (se puede editar, confirmar o anular), `CONFIRMED` (solo se puede anular) y `CANCELLED` (final). Una acción fuera del estado permitido responde `409 SALES.INVALID_STATUS`; en ese error el campo `status` del cuerpo **no** es el número HTTP sino el estado actual de la venta (`"status": "CONFIRMED"`), porque Sales sobrescribe ese campo: el frontend debe tomar el código HTTP de la respuesta y no de ese campo. Mientras una confirmación o anulación está en curso, cualquier escritura responde `409 SALES.OPERATION_IN_PROGRESS` con `operation_id`.
- **Idempotencia.** Confirmar y anular (API 12 y 14) exigen el encabezado `Idempotency-Key` (1 a 150 caracteres ASCII imprimibles, sin espacios; por ejemplo un UUID generado por la interfaz y conservado hasta recibir una respuesta definitiva). Repetir la misma solicitud con la misma clave devuelve el mismo resultado sin repetir efectos; usar la misma clave para otra venta, otra acción u otro usuario responde `409 SALES.IDEMPOTENCY_KEY_CONFLICT`. Ambas aceptan también el encabezado opcional `X-Correlation-Id` (UUID) para correlacionar trazas.
- **Rentabilidad.** Los campos `unit_cost_snapshot`, `cost_total`, `cost_known`, `gross_margin_amount` y `gross_margin_percentage` de cada línea y `has_unknown_cost` de la venta **solo aparecen** si el token tiene `perm:sales:sales:read-profitability`; sin ese permiso se omiten (no llegan en `null`). Los ejemplos de este documento no los incluyen.
- Las respuestas de Sales traen `created_by` y `updated_by` (el `sub` de Keycloak de quien actuó), `created_by_user_id` (el usuario de aplicación de Operational Context), `created_at` y `updated_at`. Las respuestas no incluyen encabezado `Location`.
- Toda escritura queda registrada en [Audit](../servicios/audit.md) con las acciones `CREATE_SALE`, `UPDATE_SALE`, `ADD_SALE_DETAIL`, `UPDATE_SALE_DETAIL`, `DELETE_SALE_DETAIL`, `CONFIRM_SALE` y `CANCEL_SALE` sobre las entidades `Sale` y `SaleDetail`; se consultan con la [API 16](administracion-empresarial.md#16-consultar-la-trazabilidad-de-la-empresa-auditoría) (lista los eventos de auditoría de la empresa; sus errores están en esa sección) y la [API 17 de Administración empresarial](administracion-empresarial.md#17-consultar-el-historial-de-una-venta-una-compra-o-un-producto) (historial de una venta concreta; errores en esa sección).

---

## 1. Buscar el cliente de la venta

**Método:** `GET`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-customers`
**Permiso requerido:** `perm:commercial-relationship:company_customers:read`

### ¿Qué hace esta API?

Lista, con paginación y búsqueda, los clientes de la empresa para que el vendedor elija a quién le vende. Es la misma consulta que la [API 7 de Gestión de clientes](gestion-de-clientes.md#7-buscar-y-listar-los-clientes-de-la-empresa) (allí está el detalle completo de filtros por identidad y la administración de la cartera); aquí se documenta el uso desde la venta. La búsqueda es sobre `internal_code` y `display_name`, **no** sobre el documento: para encontrar a un cliente por documento hay que buscar primero la identidad en Gestión de clientes (API 1 o 3 de ese módulo) y filtrar aquí por `person_identity_id` u `organization_identity_id`.

El `items[].id` del cliente elegido es el `company_customer_id` que se envía en la [API 6](#6-crear-la-venta-en-borrador). Sales exige que el cliente esté `ACTIVE` y que su identidad tenga documento de identificación; por eso conviene buscar con `status=ACTIVE` (valor por defecto). Si el cliente no existe todavía, se registra con las API 1 a 6 de [Gestión de clientes](gestion-de-clientes.md) antes de crear la venta.

Antes necesita: `company_id` con membresía `ACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-customers?search=perez&status=ACTIVE&page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa en la que se vende | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `search` | string (≤ 100) | No | Búsqueda parcial, sin distinguir mayúsculas, en `internal_code` y `display_name` | Texto libre: parte del código interno o del nombre; p. ej. `CLI-0001` o `perez` | `?search=perez` | Interfaz (lo que escribe el vendedor) |
| `status` | `ACTIVE` \| `INACTIVE` \| `ALL` | No; por defecto `ACTIVE` | Estado de los clientes | Uno de: `ACTIVE` (por defecto), `INACTIVE`, `ALL`; p. ej. `ACTIVE` | `&status=ACTIVE` | Interfaz; para vender usar `ACTIVE` |
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `&page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |
| `customer_kind` | `PERSON` \| `ORGANIZATION` | No | Solo personas o solo organizaciones | Uno de: `PERSON`, `ORGANIZATION`; p. ej. `PERSON` | `&customer_kind=PERSON` | Interfaz |
| `person_identity_id` | UUID | No | Solo el cliente con esa identidad de persona | UUID de una persona; p. ej. `a0e1d2c3-b4a5-4968-8776-655443322110` | `&person_identity_id=a0e1d2c3-b4a5-4968-8776-655443322110` | `items[].id` de la [API 1 de Gestión de clientes](gestion-de-clientes.md#1-buscar-la-identidad-de-una-persona) (busca personas por documento o nombre; sus errores están en esa sección) · guía [person_identity_id](../parametros/person-identity-id.md) |
| `organization_identity_id` | UUID | No | Solo el cliente con esa identidad de organización | UUID de una organización; p. ej. `0f1e2d3c-4b5a-4968-8776-655443322111` | `&organization_identity_id=0f1e2d3c-4b5a-4968-8776-655443322111` | `items[].id` de la [API 3 de Gestión de clientes](gestion-de-clientes.md#3-buscar-la-identidad-de-una-organización) (busca organizaciones por NIT o nombre; sus errores están en esa sección) · guía [organization_identity_id](../parametros/organization-identity-id.md) |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-customers?search=perez&status=ACTIVE&page=1&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[CompanyCustomerResponse]`):

```json
{
  "items": [
    {
      "id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "customer_kind": "PERSON",
      "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
      "organization_identity_id": null,
      "internal_code": "CLI-0001",
      "display_name": "Ana Pérez",
      "preferred_contact_person_id": null
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].id` | UUID | El `company_customer_id` que se envía en la [API 6](#6-crear-la-venta-en-borrador) y con el que se filtra en la [API 13](#13-listar-y-buscar-las-ventas) · guía [customer_id](../parametros/customer-id.md) |
| `items[].internal_code`, `display_name` | string | Lo que se muestra en el selector de cliente de la venta |
| `items[].customer_kind` | `PERSON` \| `ORGANIZATION` | Tipo de cliente; indica qué identidad consultar para mostrar el documento (API 9 o 10 de Gestión de clientes) |
| `items[].person_identity_id`, `organization_identity_id` | UUID \| null | Identidad asociada; solo una tiene valor |
| `items[].status` | `ACTIVE` \| `INACTIVE` | Solo los `ACTIVE` se aceptan en la venta; con `INACTIVE` la API 6 responde `409 SALES.REFERENCES_NOT_ELIGIBLE` |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación; `items` vacío cuando no hay coincidencias (no es error) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` en ella | Volver a leer el contexto operativo |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `search` > 100, `status` o `customer_kind` fuera de la enumeración, UUID inválido, paginación fuera de rango | Corregir los filtros |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir `perm:operational-context:application_users:read` |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Operational Context no responde al verificar la membresía | Reintentar más tarde |

## 2. Buscar productos con precio y existencias en la sucursal

**Método:** `GET`
**URL:** `https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/product-overviews`
**Permiso requerido:** `perm:product-inventory-query:product_overviews:read`; además, para que la respuesta incluya los precios se requiere `perm:commercial-relationship:price_list_items:read` y para las existencias `perm:product-inventory-query:stock:read` (sin ellos, los bloques `price` y `stock` llegan en `null`)

### ¿Qué hace esta API?

Es el buscador de productos del punto de venta. En una sola consulta devuelve, para la sucursal donde se vende, los productos de la empresa con sus presentaciones vendibles, el **precio vigente de cada presentación en la lista de precios por defecto** (o en la lista que se indique con `price_list_id`) y las **existencias** de la sucursal. Con lo que devuelve, la interfaz tiene el `company_product_id`, el `company_product_presentation_id` y el `price_list_id` que necesita cada línea de la [API 6](#6-crear-la-venta-en-borrador) y la [API 7](#7-agregar-una-línea-a-la-venta).

Reúne datos de Commercial Relationship (productos, presentaciones, precios), Product Catalog (catálogo global, códigos de barras, imagen) e Inventory (existencias). Pagina **por cursor**, sin totales: para la página siguiente se repite la misma consulta con `cursor=<next_cursor>` y los mismos filtros, orden y `page_size`. No reserva existencias ni valida nada: la validación definitiva la hace Sales al guardar la línea y al confirmar.

Para vender solo sirven los productos `ACTIVE` (valor por defecto del filtro `status`) con presentaciones `is_sellable: true` y `status: "ACTIVE"`; además Sales exige que el producto esté controlado por inventario. Si el vendedor quiere ofrecer un precio distinto al de la lista por defecto, consulta todos los precios vigentes de la presentación con la [API 4](#4-consultar-los-precios-vigentes-de-una-presentación).

Antes necesita: `company_id` con membresía `ACTIVE` y `branch_id` de esa empresa.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/product-overviews?search=acetaminofen&status=ACTIVE&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa en la que se vende | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `branch_id` | UUID | Sí | Sucursal donde se vende; sus existencias son las que se muestran | `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `memberships[].branches[].branch_id` (con `allowed: true`) de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `search` | string (≤ 200) | No | Búsqueda parcial en el nombre, `internal_code`, `reference_code` y SKU de las presentaciones | Texto libre; p. ej. `acetaminofen` | `?search=acetaminofen` | Interfaz (lo que escribe el vendedor) |
| `status` | `ACTIVE` \| `INACTIVE` \| `ALL` | No; por defecto `ACTIVE` | Estado del producto empresarial | Uno de: `ACTIVE` (por defecto), `INACTIVE`, `ALL`; p. ej. `ACTIVE` | `&status=ACTIVE` | Interfaz; para vender usar `ACTIVE` |
| `page_size` | integer 1–20 | No; por defecto `20` | Productos por página | Entero de `1` a `20`; p. ej. `20` | `&page_size=20` | Interfaz |
| `cursor` | string | No | Cursor de la página siguiente | Texto opaco devuelto en `next_cursor`; p. ej. `eyJrIjoiQWNldGFtaW5vZsOpbiJ9` | `&cursor=eyJrIjoiQWNldGFtaW5vZsOpbiJ9` | `next_cursor` de la respuesta anterior de esta misma API |
| `internal_code` | string (≤ 60) | No | Código interno exacto, sin distinguir mayúsculas | Código completo; p. ej. `PRD-0001` | `&internal_code=PRD-0001` | Interfaz (código que escribe o escanea el vendedor) |
| `sku` | string (≤ 80) | No | SKU exacto de una presentación | SKU completo; p. ej. `7701234567890` | `&sku=7701234567890` | Interfaz |
| `barcode` | string (≤ 120) | No | Código de barras exacto (Product Catalog) | Código completo; p. ej. `7701234567890` | `&barcode=7701234567890` | Interfaz (lector de código de barras) |
| `identifier` | string (≤ 120) | No | Identificador global exacto (Product Catalog) | Código completo; p. ej. `7701234567890` | `&identifier=7701234567890` | Interfaz |
| `brand_id` | UUID (repetible) | No | Solo productos de esas marcas | UUID de marca, uno o varios; p. ej. `b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e` | `&brand_id=b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e` | `brand.id` de una respuesta anterior de esta API o el catálogo de marcas de [Productos y precios](productos-y-precios.md) |
| `category_id` | UUID (repetible) | No | Solo productos de esas categorías | UUID de categoría, uno o varios; p. ej. `c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f` | `&category_id=c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f` | `categories[].id` de una respuesta anterior de esta API o el catálogo de categorías de [Productos y precios](productos-y-precios.md) |
| `include_descendants` | boolean | No | Con `category_id`, incluye las subcategorías | `true` o `false`; p. ej. `true` | `&include_descendants=true` | Interfaz |
| `product_type` | string (≤ 20) | No | Tipo de producto | Código de tipo tal como lo devuelve `product_type`; p. ej. `GOOD` | `&product_type=GOOD` | `product_type` de una respuesta anterior de esta API |
| `has_image` | boolean | No | Solo productos con o sin imagen (spec 024, pendiente de despliegue: al menos una presentación con imagen principal; la imagen pasa a `presentations[]`, ver [Product Inventory Query](../servicios/product-inventory-query.md#imágenes-por-presentación-spec-024-pendiente-de-despliegue)) | `true` o `false`; p. ej. `true` | `&has_image=true` | Interfaz |
| `stock_state` | `IN_STOCK` \| `OUT_OF_STOCK` | No | Solo productos con o sin existencias en la sucursal; requiere `perm:product-inventory-query:stock:read` | Uno de: `IN_STOCK`, `OUT_OF_STOCK`; p. ej. `IN_STOCK` | `&stock_state=IN_STOCK` | Interfaz |
| `price_list_id` | UUID | No | Lista de precios con la que se resuelve `presentations[].price`; sin este filtro se usa la lista por defecto | UUID de una lista de precios; p. ej. `5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b` | `&price_list_id=5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b` | `items[].id` de la [API 3](#3-consultar-las-listas-de-precios-de-la-empresa) (lista las listas de precios de la empresa; errores en §3) |
| `sort` | string | No | Orden | Uno de: `display_name`, `internal_code`, `created_at`, con sufijo opcional `:asc` o `:desc`; sin `sort`, `display_name:asc` (por defecto con `search`); p. ej. `display_name:asc` | `&sort=display_name:asc` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/product-overviews?search=acetaminofen&status=ACTIVE&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`CursorPage[ProductOverview]`; token con permiso de precios y de existencias):

```json
{
  "items": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
      "display_name": "Acetaminofén 500 mg",
      "canonical_name": "Acetaminofén 500 mg tableta",
      "internal_code": "PRD-0001",
      "reference_code": null,
      "status": "ACTIVE",
      "global_status": "ACTIVE",
      "product_type": "GOOD",
      "brand": {"id": "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e", "code": "GEN", "name": "Genérico"},
      "categories": [
        {"id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f", "code": "ANALG", "name": "Analgésicos", "is_primary": true}
      ],
      "identifiers": [
        {"type": "EAN13", "value": "7701234567890", "is_primary": true, "global_product_presentation_id": "c6c7d8e9-f0a1-4b2c-9d3e-4f5a6b7c8d94"}
      ],
      "base_unit": {"id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e", "code": "UN", "name": "Unidad"},
      "has_image": true,
      "image_url": "https://sio-product-catalog-dev.onrender.com/public/product-images/firma-ilustrativa",
      "presentations": [
        {
          "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
          "global_product_presentation_id": "c6c7d8e9-f0a1-4b2c-9d3e-4f5a6b7c8d94",
          "code": "UN",
          "name": "Unidad",
          "sku": "7701234567890",
          "internal_code": "PRD-0001-U",
          "status": "ACTIVE",
          "is_sellable": true,
          "base_quantity_factor": "1.0000",
          "price": {
            "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
            "price_list_item_id": "6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c",
            "unit_price": "800.00",
            "currency_code": "COP",
            "resolution": "PRICE_LIST_ITEM"
          }
        }
      ],
      "stock": {
        "base_unit": {"id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e", "code": "UN", "name": "Unidad"},
        "total_base_quantity": "800.0000",
        "branches": [
          {
            "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
            "base_quantity": "800.0000",
            "balance_state": "REGISTERED",
            "minimum_stock": "100.0000",
            "minimum_state": "ABOVE_MINIMUM"
          }
        ],
        "equivalences": [
          {"company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83", "whole_units": 800, "remainder_base_quantity": "0.0000"}
        ]
      }
    }
  ],
  "page_size": 20,
  "has_next": false,
  "next_cursor": null,
  "pagination_reset": false,
  "pagination_reset_reason": null,
  "partial": false,
  "partial_reason": null,
  "sort_applied": "display_name:asc",
  "resolved_at": "2026-10-20T15:40:00Z"
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].company_product_id` | UUID | El `company_product_id` de la línea de venta (API 6 y 7) · guía [company_product_id](../parametros/company-product-id.md) |
| `items[].display_name`, `internal_code`, `brand`, `categories[]`, `identifiers[]`, `image_url` | varios | Lo que se muestra en el buscador; `identifiers[]` trae los códigos de barras (`type`, `value`) |
| `items[].status`, `global_status` | `ACTIVE` \| `INACTIVE` | Solo los productos `ACTIVE` se pueden vender |
| `items[].presentations[].company_product_presentation_id` | UUID | El `company_product_presentation_id` de la línea de venta (API 6 y 7) · guía [company_product_presentation_id](../parametros/company-product-presentation-id.md) |
| `items[].presentations[].code`, `name`, `sku`, `base_quantity_factor` | string | Presentación a mostrar; `base_quantity_factor` son las unidades base que contiene (4 decimales) |
| `items[].presentations[].status`, `is_sellable` | string, boolean | Solo las presentaciones `ACTIVE` y vendibles se aceptan en la venta |
| `items[].presentations[].price` | objeto \| null | Precio vigente por unidad de presentación en la lista por defecto (o en `price_list_id`). `null` si el token no tiene `perm:commercial-relationship:price_list_items:read` |
| `items[].presentations[].price.price_list_id`, `price_list_item_id` | UUID \| null | Lista y precio aplicados; `price_list_id` es el valor que se envía en la línea si el vendedor elige este precio |
| `items[].presentations[].price.unit_price`, `currency_code` | string \| null, string | Precio a mostrar (2 decimales) y moneda |
| `items[].presentations[].price.resolution` | string | `PRICE_LIST_ITEM` (hay precio), `NO_PRICE_IN_LIST`, `NO_APPLICABLE_PRICE_LIST` o `PRICE_LIST_NOT_APPLICABLE`; en los tres últimos `unit_price` es `null` y la presentación **no se puede vender** con esa lista (Sales respondería `409 SALES.REFERENCES_NOT_ELIGIBLE`) |
| `items[].stock` | objeto \| null | Existencias de la sucursal en unidad base. `null` si el token no tiene `perm:product-inventory-query:stock:read` |
| `items[].stock.branches[].base_quantity`, `balance_state` | string, string | Saldo disponible en la sucursal (4 decimales) y `REGISTERED` (hay saldo registrado, aunque sea cero) o `NOT_REGISTERED` |
| `items[].stock.branches[].minimum_stock`, `minimum_state` | string \| null | Política de mínimo; solo con `perm:inventory:product-policies:read` (`NO_POLICY`, `BELOW_MINIMUM`, `AT_MINIMUM`, `ABOVE_MINIMUM`) |
| `items[].stock.equivalences[]` | array | Cuántas unidades enteras de cada presentación caben en el saldo (`whole_units`) y el resto en unidad base |
| `has_next`, `next_cursor` | boolean, string \| null | Si hay más páginas, repetir la consulta con `cursor=next_cursor` y los mismos filtros |
| `pagination_reset`, `pagination_reset_reason` | boolean, string \| null | `true` si el servicio ignoró el cursor y volvió a la primera página (`FILTERS_CHANGED`, `SORT_CHANGED`, `PAGE_SIZE_CHANGED`, `CURSOR_EXPIRED`; los cursores caducan a los 900 s) |
| `partial`, `partial_reason` | boolean, string \| null | `true` si la página se cortó antes de llenarse; **no es el final**: continuar con `next_cursor` |
| `sort_applied`, `resolved_at` | string | Orden aplicado y momento de la consulta |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `403` | `PRODUCT_INVENTORY_QUERY.FORBIDDEN` | Falta `perm:product-inventory-query:product_overviews:read`, o se envió `stock_state` sin `perm:product-inventory-query:stock:read` | Mostrar que faltan permisos; no enviar `stock_state` si el usuario no ve existencias |
| `404` | `PRODUCT_INVENTORY_QUERY.NOT_FOUND` | La empresa no existe, el usuario no tiene membresía `ACTIVE` en ella o la sucursal no es de la empresa | Volver a leer el contexto operativo |
| `422` | `PRODUCT_INVENTORY_QUERY.VALIDATION_ERROR` | Filtro desconocido (`errors[].code` `UNKNOWN_FIELD`), valor mal formado (`INVALID_FORMAT`), `page_size` fuera de 1–20, texto más largo que el máximo | Corregir los filtros |
| `422` | `PRODUCT_INVENTORY_QUERY.INVALID_CURSOR` | El `cursor` está manipulado o es ilegible | Repetir la consulta sin `cursor` |
| `503` | `PRODUCT_INVENTORY_QUERY.DEPENDENCY_UNAVAILABLE` | Commercial Relationship, Product Catalog, Inventory u Operational Context no respondieron a tiempo (3 s por llamada, 8 s en total) | Reintentar más tarde |

## 3. Consultar las listas de precios de la empresa

**Método:** `GET`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-lists`
**Permiso requerido:** `perm:commercial-relationship:price_lists:read`

### ¿Qué hace esta API?

Lista las listas de precios de la empresa (código, nombre, moneda, vigencia y cuál es la **lista por defecto**). En la venta sirve para dos cosas: mostrar el nombre de la lista a la que pertenece cada precio que se ofrece al vendedor (la [API 4](#4-consultar-los-precios-vigentes-de-una-presentación) devuelve solo el `price_list_id`) y para resolver los precios del buscador con otra lista (`price_list_id` de la [API 2](#2-buscar-productos-con-precio-y-existencias-en-la-sucursal)). Sales solo acepta en una línea listas `ACTIVE` y vigentes en la fecha de la venta y de la misma moneda de la empresa; con otra lista responde `409 SALES.REFERENCES_NOT_ELIGIBLE` (`PRICE_LIST_NOT_APPLICABLE` o `PRICE_CURRENCY_MISMATCH`).

Por defecto solo devuelve listas `ACTIVE`. La administración de las listas (crearlas, modificarlas, marcar la lista por defecto) está en [Productos y precios](productos-y-precios.md).

Antes necesita: `company_id` con membresía `ACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-lists?status=ACTIVE&page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `status` | `ACTIVE` \| `INACTIVE` \| `ALL` | No; por defecto `ACTIVE` | Estado de las listas | Uno de: `ACTIVE` (por defecto), `INACTIVE`, `ALL`; p. ej. `ACTIVE` | `?status=ACTIVE` | Interfaz; para vender usar `ACTIVE` |
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `&page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |
| `search` | string (≤ 100) | No | Búsqueda parcial, sin distinguir mayúsculas, en `code` y `name` | Texto libre; p. ej. `general` | `&search=general` | Interfaz |
| `currency_code` | string (3 letras) | No | Solo listas de esa moneda | Código ISO 4217 de 3 letras; p. ej. `COP` | `&currency_code=COP` | `currency_code` de la venta (API 10) o `default_currency` de la empresa en la [API 3 de Administración empresarial](administracion-empresarial.md#3-consultar-una-empresa) (devuelve los datos de la empresa; sus errores están en esa sección) |
| `is_default` | boolean | No | Solo la lista por defecto (`true`) o las demás (`false`) | `true` o `false`; p. ej. `true` | `&is_default=true` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-lists?status=ACTIVE&page=1&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[PriceListResponse]`):

```json
{
  "items": [
    {
      "id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-02-10T10:00:00Z",
      "updated_at": "2026-02-10T10:00:00Z",
      "code": "GENERAL",
      "name": "Lista general",
      "description": null,
      "currency_code": "COP",
      "is_default": true,
      "valid_from": "2026-02-10T10:00:00Z",
      "valid_to": null
    },
    {
      "id": "7a8b9c0d-1e2f-4a3b-9c4d-5e6f7a8b9c0d",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-03-01T10:00:00Z",
      "updated_at": "2026-03-01T10:00:00Z",
      "code": "MAYORISTA",
      "name": "Lista mayorista",
      "description": "Precios para compras por volumen",
      "currency_code": "COP",
      "is_default": false,
      "valid_from": "2026-03-01T10:00:00Z",
      "valid_to": null
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 2,
  "total_pages": 1
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].id` | UUID | El `price_list_id` que se envía en la línea de la venta (API 6, 7 y 8) y con el que se filtra en las API 2 y 4 |
| `items[].code`, `name`, `description` | string \| null | Nombre de la lista que se muestra junto a cada precio ofrecido |
| `items[].currency_code` | string | Moneda; debe coincidir con la de la empresa, si no Sales rechaza la línea (`PRICE_CURRENCY_MISMATCH`) |
| `items[].is_default` | boolean | `true` en la lista que Sales aplica cuando la línea no envía `price_list_id`; solo una lista es la lista por defecto |
| `items[].status`, `valid_from`, `valid_to` | string, datetime, datetime \| null | Solo las listas `ACTIVE` y vigentes se aceptan en la venta |
| `items[].version` | integer | Solo se usa al administrar la lista en Productos y precios |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación; `items` vacío cuando no hay coincidencias (no es error) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` en ella | Volver a leer el contexto operativo |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `search` > 100, `status` fuera de la enumeración, `currency_code` que no tiene 3 letras, `is_default` que no es booleano, paginación fuera de rango | Corregir los filtros |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir `perm:operational-context:application_users:read` |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Operational Context no responde al verificar la membresía | Reintentar más tarde |

## 4. Consultar los precios vigentes de una presentación

**Método:** `GET`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-list-items`
**Permiso requerido:** `perm:commercial-relationship:price_list_items:read`

### ¿Qué hace esta API?

Devuelve los precios registrados en las listas de precios de la empresa, filtrados por presentación y vigencia. Es la consulta con la que la interfaz obtiene **todos los precios vigentes de la presentación que el vendedor está agregando** (uno por lista de precios) para mostrarlos **de mayor a menor** y dejar que elija; del precio elegido se envía su `price_list_id` en la línea. La [API 2](#2-buscar-productos-con-precio-y-existencias-en-la-sucursal) ya trae el precio de la lista por defecto, así que esta consulta solo es necesaria cuando la empresa tiene más de una lista y el vendedor puede ofrecer otro precio.

Para obtener únicamente los precios aplicables a la venta, filtrar por `company_product_presentation_id`, `status=ACTIVE` (valor por defecto) y `applicable_at` con la fecha y hora actuales; sin `applicable_at` la respuesta incluye también precios futuros o ya vencidos. El `unit_price` es por unidad de presentación. Sales vuelve a resolver el precio al guardar la línea y al confirmar, así que el valor que se muestre aquí es informativo: el que vale es `lines[].unit_price` de la respuesta de Sales.

Antes necesita: `company_id` con membresía `ACTIVE` y el `company_product_presentation_id` elegido en la [API 2](#2-buscar-productos-con-precio-y-existencias-en-la-sucursal).

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-list-items?company_product_presentation_id=a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83&status=ACTIVE&applicable_at=2026-10-20T15%3A00%3A00Z&page=1&page_size=50' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `company_product_presentation_id` | UUID | No (recomendado en la venta) | Solo los precios de esa presentación | UUID de una presentación; p. ej. `a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83` | `?company_product_presentation_id=a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83` | `items[].presentations[].company_product_presentation_id` de la [API 2](#2-buscar-productos-con-precio-y-existencias-en-la-sucursal) (busca productos con precio y existencias; errores en §2) · guía [company_product_presentation_id](../parametros/company-product-presentation-id.md) |
| `status` | `ACTIVE` \| `INACTIVE` \| `ALL` | No; por defecto `ACTIVE` | Estado del precio (`INACTIVE` son precios cerrados) | Uno de: `ACTIVE` (por defecto), `INACTIVE`, `ALL`; p. ej. `ACTIVE` | `&status=ACTIVE` | Interfaz; para vender usar `ACTIVE` |
| `applicable_at` | datetime con zona horaria | No (recomendado en la venta) | Solo los precios vigentes en ese instante (`valid_from` ≤ instante < `valid_to`) | Fecha y hora ISO 8601 con zona; p. ej. `2026-10-20T15:00:00Z` (en la URL, `2026-10-20T15%3A00%3A00Z`) | `&applicable_at=2026-10-20T15%3A00%3A00Z` | Interfaz (fecha y hora actuales) |
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `&page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `50` | `&page_size=50` | Interfaz |
| `price_list_id` | UUID | No | Solo los precios de esa lista | UUID de una lista; p. ej. `5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b` | `&price_list_id=5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b` | `items[].id` de la [API 3](#3-consultar-las-listas-de-precios-de-la-empresa) (lista las listas de precios; errores en §3) |
| `company_product_id` | UUID | No | Solo los precios de las presentaciones de ese producto | UUID de un producto; p. ej. `e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `&company_product_id=e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `items[].company_product_id` de la [API 2](#2-buscar-productos-con-precio-y-existencias-en-la-sucursal) (busca productos; errores en §2) · guía [company_product_id](../parametros/company-product-id.md) |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-list-items?company_product_presentation_id=a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83&status=ACTIVE&applicable_at=2026-10-20T15%3A00%3A00Z&page=1&page_size=50`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[PriceListItemResponse]`; la interfaz los ordena por `unit_price` de mayor a menor antes de mostrarlos):

```json
{
  "items": [
    {
      "id": "6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-02-10T10:05:00Z",
      "updated_at": "2026-02-10T10:05:00Z",
      "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "unit_price": "800.00",
      "currency_code": "COP",
      "valid_from": "2026-02-10T10:05:00Z",
      "valid_to": null,
      "origin": "MANUAL",
      "closure_reason": null,
      "automatic_application_id": null
    },
    {
      "id": "8b9c0d1e-2f3a-4b4c-8d5e-6f7a8b9c0d1e",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-03-01T10:05:00Z",
      "updated_at": "2026-03-01T10:05:00Z",
      "price_list_id": "7a8b9c0d-1e2f-4a3b-9c4d-5e6f7a8b9c0d",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "unit_price": "750.00",
      "currency_code": "COP",
      "valid_from": "2026-03-01T10:05:00Z",
      "valid_to": null,
      "origin": "MANUAL",
      "closure_reason": null,
      "automatic_application_id": null
    }
  ],
  "page": 1,
  "page_size": 50,
  "total_records": 2,
  "total_pages": 1
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].price_list_id` | UUID | Lista a la que pertenece el precio; es el valor que se envía en `price_list_id` de la línea si el vendedor elige este precio. Su nombre se obtiene de la [API 3](#3-consultar-las-listas-de-precios-de-la-empresa) |
| `items[].id` | UUID | Identificador del precio; Sales lo devuelve como `lines[].price_list_item_id` para que la interfaz sepa qué precio aplicó |
| `items[].unit_price`, `currency_code` | string, string | Precio por unidad de presentación (2 decimales) y moneda; ordenar de mayor a menor para mostrarlos |
| `items[].company_product_id`, `company_product_presentation_id` | UUID | Producto y presentación a los que aplica el precio |
| `items[].status`, `valid_from`, `valid_to` | string, datetime, datetime \| null | Vigencia; con `applicable_at` solo llegan los vigentes |
| `items[].origin` | `MANUAL` \| `AUTOMATIC` | Si el precio lo registró un usuario o lo generó una aplicación automática de precios tras una compra |
| `items[].closure_reason`, `automatic_application_id` | string \| null, UUID \| null | Motivo de cierre (solo precios `INACTIVE`) y aplicación automática que lo generó |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación; `items` vacío significa que la presentación no tiene precio vigente en ninguna lista y **no se puede vender** |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` en ella | Volver a leer el contexto operativo |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | UUID inválido, `status` fuera de la enumeración, `applicable_at` sin zona horaria o mal formado, paginación fuera de rango | Corregir los filtros |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir `perm:operational-context:application_users:read` |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Operational Context no responde al verificar la membresía | Reintentar más tarde |

## 5. Consultar los métodos de pago

**Método:** `GET`
**URL:** `https://sio-payment-reference-dev.onrender.com/global-payment-methods`
**Permiso requerido:** `perm:payment-reference:global_payment_methods:read`

### ¿Qué hace esta API?

Lista el catálogo **global** de métodos de pago de la plataforma (efectivo, transferencia, tarjeta, etc.), igual para todas las empresas. El vendedor elige con cuál paga el cliente y la interfaz envía su `id` como `payment_method_id` en la [API 6](#6-crear-la-venta-en-borrador). Sales guarda en la venta el código y el nombre del método (`payment_method_code_snapshot`, `payment_method_name_snapshot`) tal como estaban al crearla. Como las ventas del MVP son de contado, el método de pago es solo informativo: no genera cuentas por cobrar ni valida referencias de pago.

Solo se aceptan métodos `ACTIVE`: con uno `INACTIVE` la API 6 responde `409 SALES.REFERENCES_NOT_ELIGIBLE` (`PAYMENT_METHOD_INACTIVE`). Conviene filtrar con `status=ACTIVE`. Esta URL **no lleva** el prefijo `/api/v1`.

Antes necesita: solo el token; no depende de la empresa.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-payment-reference-dev.onrender.com/global-payment-methods?status=ACTIVE&page=1&page_size=50' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:** no requiere parámetros de ruta.

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `status` | `ACTIVE` \| `INACTIVE` | No | Estado del método | Uno de: `ACTIVE`, `INACTIVE`; sin el filtro se devuelven todos; p. ej. `ACTIVE` | `?status=ACTIVE` | Interfaz; para vender usar `ACTIVE` |
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `&page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `50` | `&page_size=50` | Interfaz |
| `search` | string | No | Búsqueda parcial, sin distinguir mayúsculas, en `code` y `name` | Texto libre; p. ej. `efectivo` | `&search=efectivo` | Interfaz |
| `method_type` | `CASH` \| `BANK` \| `CARD` \| `WALLET` \| `CHECK` \| `OTHER` | No | Tipo funcional del método | Uno de: `CASH`, `BANK`, `CARD`, `WALLET`, `CHECK`, `OTHER`; p. ej. `CASH` | `&method_type=CASH` | Interfaz |
| `requires_reference` | boolean | No | Solo métodos que exigen (o no) un número de referencia de pago | `true` o `false`; p. ej. `false` | `&requires_reference=false` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-payment-reference-dev.onrender.com/global-payment-methods?status=ACTIVE&page=1&page_size=50`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[GlobalPaymentMethodResponse]`):

```json
{
  "items": [
    {
      "id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
      "code": "CASH",
      "name": "Efectivo",
      "method_type": "CASH",
      "requires_reference": false,
      "status": "ACTIVE",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-01-15T12:00:00Z",
      "updated_at": "2026-01-15T12:00:00Z"
    },
    {
      "id": "c8d9e0f1-a2b3-4c4d-9e5f-6a7b8c9d0e16",
      "code": "TRANSFER",
      "name": "Transferencia bancaria",
      "method_type": "BANK",
      "requires_reference": true,
      "status": "ACTIVE",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-01-15T12:00:00Z",
      "updated_at": "2026-01-15T12:00:00Z"
    }
  ],
  "page": 1,
  "page_size": 50,
  "total_records": 2,
  "total_pages": 1
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].id` | UUID | El `payment_method_id` que se envía en la [API 6](#6-crear-la-venta-en-borrador) · guía [payment_method_id](../parametros/payment-method-id.md) |
| `items[].code`, `name` | string | Lo que se muestra en el selector; Sales los copia a `payment_method_code_snapshot` y `payment_method_name_snapshot` |
| `items[].method_type` | `CASH` \| `BANK` \| `CARD` \| `WALLET` \| `CHECK` \| `OTHER` | Tipo funcional, útil para agrupar o mostrar un icono |
| `items[].requires_reference` | boolean | Si el método normalmente exige un número de referencia; en el MVP Sales **no** pide ni guarda esa referencia |
| `items[].status` | `ACTIVE` \| `INACTIVE` | Solo los `ACTIVE` se aceptan en la venta |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación |

### Posibles errores

Payment Reference todavía no responde en Problem Details: sus errores llegan con el formato básico `{"detail": …}` y sin `code`, salvo los conflictos propios de la administración del catálogo, que no aplican a esta consulta.

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `403` | sin `code` (`{"detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta."}`) | El token no tiene `perm:payment-reference:global_payment_methods:read` | Mostrar que faltan permisos |
| `422` | sin `code` (`{"detail": [...]}` de FastAPI) | `status` o `method_type` fuera de la enumeración, `requires_reference` que no es booleano, paginación fuera de rango | Corregir los filtros |
| `503` | sin `code` (`{"detail": "Payment Reference no puede atender la solicitud porque su base de datos no está disponible. Intente de nuevo en unos momentos."}`) | La base de datos de Payment Reference no está disponible | Reintentar más tarde |

## 6. Crear la venta en borrador

**Método:** `POST`
**URL:** `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales`
**Permiso requerido:** `perm:sales:sales:create`; si el cuerpo trae líneas, también `perm:sales:sale_details:create` (sin él la API responde `403 SALES.FORBIDDEN`)

### ¿Qué hace esta API?

Crea la venta en estado `DRAFT` con su encabezado (sucursal, cliente, método de pago y observaciones) y, opcionalmente, sus primeras líneas (hasta 100). Un borrador no descuenta existencias ni tiene número: es la venta que el vendedor va armando hasta confirmarla con la [API 12](#12-confirmar-la-venta). Si el cuerpo no trae líneas, se agregan después con la [API 7](#7-agregar-una-línea-a-la-venta).

Efectos verificados en el código:

- Valida que el usuario tenga asignación `ACTIVE` a la sucursal y luego todas las referencias en Commercial Relationship (cliente, productos, presentaciones, precio), Party Identity (identificación del cliente) y Payment Reference (método de pago). Una referencia inexistente, de otra empresa o incoherente responde `422`; una que existe pero no se puede usar responde `409 SALES.REFERENCES_NOT_ELIGIBLE`; si hay de ambas clases se informa el `422`.
- Resuelve el precio de cada línea en Commercial Relationship con la regla de precios descrita al inicio: lista elegida (`price_list_id`) o lista por defecto; nunca acepta `unit_price`.
- Copia en la venta el nombre y la identificación del cliente, el código y nombre del método de pago, y en cada línea los códigos y nombres del producto y la presentación, el factor y la unidad. Estos datos se vuelven a validar al confirmar.
- Fija `currency_code` con la moneda de la empresa, `operation_date` y `due_date` con la fecha del día en la zona horaria de la sucursal, la condición de contado (`CASH`, 0 días) y `version: 1`.
- Registra el evento de auditoría `CREATE_SALE` (entidad `Sale`). No toca Inventory ni la secuencia de numeración.

Antes necesita: `company_id` y `branch_id` con asignación `ACTIVE` del usuario, el `company_customer_id` de la [API 1](#1-buscar-el-cliente-de-la-venta), el `payment_method_id` de la [API 5](#5-consultar-los-métodos-de-pago) y, para cada línea, el producto, la presentación y opcionalmente la lista de precios de las API 2 a 4.

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "company_customer_id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
    "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
    "observations": "Venta mostrador",
    "lines": [
      {
        "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
        "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
        "price_list_id": null,
        "quantity": "2"
      }
    ]
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa de la venta | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_customer_id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "observations": "Venta mostrador",
  "lines": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "price_list_id": null,
      "quantity": "2"
    }
  ]
}
```
| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `branch_id` | UUID | Sí | Sucursal donde se vende; el usuario debe tener asignación `ACTIVE` a ella | `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `memberships[].branches[].branch_id` (con `allowed: true`) de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) · guía [branch_id](../parametros/branch-id.md) |
| `company_customer_id` | UUID | Sí | Cliente `ACTIVE` de la empresa con identificación registrada | `c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f` | `items[].id` de la [API 1](#1-buscar-el-cliente-de-la-venta) (busca los clientes de la empresa; errores en §1) · guía [customer_id](../parametros/customer-id.md) |
| `payment_method_id` | UUID | Sí | Método de pago `ACTIVE` | `b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05` | `items[].id` de la [API 5](#5-consultar-los-métodos-de-pago) (lista los métodos de pago; errores en §5) · guía [payment_method_id](../parametros/payment-method-id.md) |
| `observations` | string \| null | No | Nota libre de la venta, hasta 2000 caracteres | `"Venta mostrador"` | Interfaz |
| `lines` | array | No; por defecto `[]` | Líneas iniciales, máximo 100 (`LINES_LIMIT_EXCEEDED`) | ver filas siguientes | Interfaz |
| `lines[].company_product_id` | UUID | Sí | Producto empresarial `ACTIVE`, vendible y controlado por inventario | `e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `items[].company_product_id` de la [API 2](#2-buscar-productos-con-precio-y-existencias-en-la-sucursal) (busca productos con precio y existencias; errores en §2) · guía [company_product_id](../parametros/company-product-id.md) |
| `lines[].company_product_presentation_id` | UUID | Sí | Presentación `ACTIVE` y vendible de ese mismo producto | `a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83` | `items[].presentations[].company_product_presentation_id` de la [API 2](#2-buscar-productos-con-precio-y-existencias-en-la-sucursal) (presentaciones vendibles del producto; errores en §2) · guía [company_product_presentation_id](../parametros/company-product-presentation-id.md) |
| `lines[].price_list_id` | UUID \| null | No; por defecto `null` | Lista de precios del precio que eligió el vendedor; con `null` Sales usa la lista por defecto de la empresa | `7a8b9c0d-1e2f-4a3b-9c4d-5e6f7a8b9c0d` | `items[].price_list_id` del precio elegido en la [API 4](#4-consultar-los-precios-vigentes-de-una-presentación) (precios vigentes de la presentación; errores en §4) o `items[].presentations[].price.price_list_id` de la [API 2](#2-buscar-productos-con-precio-y-existencias-en-la-sucursal) (precio de la lista por defecto; errores en §2); `null` si el vendedor no eligió precio |
| `lines[].quantity` | number \| string | Sí | Cantidad en unidades de la presentación; mayor que cero, máximo 4 decimales | `"2"` | Interfaz (cantidad que escribe el vendedor) |
| `lines[].discount_amount` | number \| string | No; por defecto `0` | Descuento de la línea; en el MVP solo se admite `0` | `0` | No se envía |
| `lines[].tax_amount` | number \| string | No; por defecto `0` | Impuesto de la línea; en el MVP solo se admite `0` | `0` | No se envía |

Campos que **no** se envían y la API rechaza con `422 SALES.VALIDATION_ERROR`: `lines[].unit_price` (`UNIT_PRICE_NOT_ALLOWED`), `operation_date` (`OPERATION_DATE_NOT_ALLOWED`), `due_date`, `customer_payment_condition_id`, `payment_condition_code_snapshot`, `payment_terms_days_snapshot` (`PAYMENT_CONDITION_NOT_ALLOWED`) y cualquier otro campo no listado (`UNKNOWN_FIELD`).

### Respuesta exitosa

`201 Created` (`SaleResponse` con `lines`; sin encabezado `Location`):

```json
{
  "id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_customer_id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "customer_payment_condition_id": null,
  "payment_condition_code_snapshot": "CASH",
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "payment_method_code_snapshot": "CASH",
  "payment_method_name_snapshot": "Efectivo",
  "payment_terms_days_snapshot": 0,
  "due_date": "2026-10-20",
  "sale_sequence_id": null,
  "number": null,
  "sequence_value": null,
  "status": "DRAFT",
  "operation_date": "2026-10-20",
  "customer_name_snapshot": "Ana Pérez",
  "customer_identification_snapshot": "CC 1012345678",
  "currency_code": "COP",
  "observations": "Venta mostrador",
  "subtotal": "1600.00",
  "discount_total": "0.00",
  "tax_total": "0.00",
  "total": "1600.00",
  "inventory_operation_id": null,
  "created_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancellation_reason": null,
  "pending_operation_id": null,
  "version": 1,
  "created_at": "2026-10-20T15:50:00Z",
  "updated_at": "2026-10-20T15:50:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "lines": [
    {
      "id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
      "sale_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
      "line_number": 1,
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
      "price_list_item_id": "6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c",
      "price_list_requested": false,
      "price_source": "PRICE_LIST_ITEM",
      "product_code_snapshot": "PRD-0001",
      "product_name_snapshot": "Acetaminofén 500 mg",
      "presentation_code_snapshot": "UN",
      "presentation_name_snapshot": "Unidad",
      "base_quantity_factor_snapshot": "1.00000000",
      "unit_code_snapshot": "UN",
      "quantity": "2.0000",
      "base_quantity": "2.0000",
      "unit_price": "800.0000",
      "discount_amount": "0.00",
      "tax_amount": "0.00",
      "subtotal": "1600.00",
      "total": "1600.00",
      "created_at": "2026-10-20T15:50:00Z",
      "updated_at": "2026-10-20T15:50:00Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ]
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `id` | UUID | El `sale_id` de la venta; se usa en las API 7 a 12 y 14 · guía [sale_id](../parametros/sale-id.md) |
| `status` | `DRAFT` \| `CONFIRMED` \| `CANCELLED` | Estado; recién creada siempre es `DRAFT` |
| `version` | integer | Versión actual; es la que se envía en la siguiente escritura (API 7, 8, 9, 12 y 14) |
| `number`, `sequence_value`, `sale_sequence_id` | string \| null, integer \| null, UUID \| null | Número del documento; `null` mientras la venta es borrador, se asignan al confirmar |
| `operation_date`, `due_date` | date | Fecha de la venta (hoy en la zona horaria de la sucursal) y vencimiento (igual a la fecha, contado); se recalculan y quedan fijas al confirmar |
| `customer_name_snapshot`, `customer_identification_snapshot` | string | Nombre e identificación del cliente copiados al guardar (p. ej. `CC 1012345678`); se muestran en el documento |
| `payment_method_code_snapshot`, `payment_method_name_snapshot` | string | Método de pago copiado al guardar |
| `payment_condition_code_snapshot`, `payment_terms_days_snapshot`, `customer_payment_condition_id` | string, integer, null | Siempre `CASH`, `0` y `null`: venta de contado |
| `currency_code` | string | Moneda de la empresa al crear la venta |
| `subtotal`, `discount_total`, `tax_total`, `total` | string | Totales con 2 decimales; `total = subtotal` y descuentos e impuestos en `0.00` |
| `inventory_operation_id` | UUID \| null | Operación de salida en Inventory; tiene valor solo cuando la venta está confirmada |
| `pending_operation_id` | UUID \| null | Confirmación o anulación en curso; mientras tenga valor no se puede escribir en la venta |
| `cancelled_by_user_id`, `cancelled_at`, `cancellation_reason` | UUID \| null, datetime \| null, string \| null | Datos de la anulación; `null` si no se anuló |
| `created_by_user_id` | UUID | Usuario de aplicación (Operational Context) que creó la venta |
| `lines[].id` | UUID | El `detail_id` que se usa en las API 8 y 9 |
| `lines[].line_number` | integer | Número de línea a mostrar; es el que aparece en `errors[].line_number` |
| `lines[].price_list_id`, `price_list_item_id` | UUID | Lista y precio que aplicó Sales |
| `lines[].price_list_requested` | boolean | `true` si el vendedor envió `price_list_id`; `false` si se aplicó la lista por defecto |
| `lines[].price_source` | string | Origen del precio; siempre `PRICE_LIST_ITEM` |
| `lines[].product_code_snapshot`, `product_name_snapshot`, `presentation_code_snapshot`, `presentation_name_snapshot`, `unit_code_snapshot` | string | Datos del producto y la presentación copiados al guardar la línea |
| `lines[].base_quantity_factor_snapshot`, `base_quantity` | string | Factor de la presentación (8 decimales) y cantidad en unidad base (`quantity × factor`), que es la que descuenta Inventory |
| `lines[].quantity`, `unit_price` | string | Cantidad y precio unitario por presentación (4 decimales) |
| `lines[].subtotal`, `total`, `discount_amount`, `tax_amount` | string | Importes de la línea con 2 decimales |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `403` | `SALES.FORBIDDEN` | Falta `perm:sales:sales:create`, o se enviaron líneas sin `perm:sales:sale_details:create`, o el token es de una cuenta de servicio | Mostrar que faltan permisos y el `trace_id` |
| `403` | `SALES.BRANCH_ACCESS_DENIED` | El usuario no tiene asignación `ACTIVE` a la sucursal de la venta, o la sucursal o la empresa están inactivas | Mostrar el mensaje y pedir la asignación al administrador ([API 12 de Administración empresarial](administracion-empresarial.md#12-asignar-un-usuario-a-una-sucursal)) |
| `403` | `SALES.OPERATIONAL_ACCESS_DENIED` | Operational Context no permite al usuario consultar su acceso operativo | Pedir `perm:operational-context:application_users:read` indicando el `trace_id` |
| `404` | `SALES.NOT_FOUND` | La empresa no existe, el usuario no es miembro `ACTIVE`, la sucursal es de otra empresa o la venta no existe en la empresa | Volver a leer el contexto operativo o la lista de ventas |
| `422` | `SALES.VALIDATION_ERROR` | Encabezado o líneas inválidos: `REQUIRED`, `UNKNOWN_FIELD`, `INVALID_FORMAT`, `LINES_LIMIT_EXCEEDED`, `UNIT_PRICE_NOT_ALLOWED`, `OPERATION_DATE_NOT_ALLOWED`, `PAYMENT_CONDITION_NOT_ALLOWED`, `QUANTITY_NOT_POSITIVE`, `TOO_MANY_DECIMALS`, `AMOUNT_OUT_OF_RANGE`, `BASE_QUANTITY_PRECISION`, `DISCOUNT_NOT_ALLOWED`, `TAX_NOT_ALLOWED`; o referencias inexistentes o de otra empresa: `BRANCH_NOT_FOUND`, `CUSTOMER_NOT_FOUND`, `PERSON_IDENTITY_NOT_FOUND`, `ORGANIZATION_IDENTITY_NOT_FOUND`, `PAYMENT_METHOD_NOT_FOUND`, `COMPANY_PRODUCT_NOT_FOUND`, `PRESENTATION_NOT_FOUND`, `PRESENTATION_OF_OTHER_PRODUCT`, `PRICE_LIST_NOT_FOUND` | Mostrar cada `errors[].message` junto al campo (`errors[].field`, p. ej. `lines[0].quantity`) y corregir |
| `409` | `SALES.REFERENCES_NOT_ELIGIBLE` | Una referencia existe pero no se puede usar; `errors[].code`: `COMPANY_INACTIVE`, `BRANCH_INACTIVE`, `CUSTOMER_NOT_ELIGIBLE` (cliente inactivo), `CUSTOMER_IDENTIFICATION_MISSING`, `PAYMENT_METHOD_INACTIVE`, `PRODUCT_INACTIVE`, `PRODUCT_NOT_SELLABLE`, `PRODUCT_NOT_INVENTORY_CONTROLLED`, `PRESENTATION_INACTIVE`, `PRESENTATION_NOT_SELLABLE`, `PRICE_NOT_IN_LIST` (la lista elegida no tiene precio vigente para la presentación), `PRICE_NOT_AVAILABLE` (no hay lista por defecto vigente con precio), `PRICE_LIST_NOT_APPLICABLE` (lista inactiva o no vigente), `PRICE_CURRENCY_MISMATCH`, `APPLICATION_USER_INACTIVE` | Mostrar cada `errors[].message` junto al campo o la línea (`line_number`) y pedir otra referencia o corregir la configuración |
| `503` | `SALES.DEPENDENCY_UNAVAILABLE` | Operational Context, Commercial Relationship, Party Identity, Payment Reference o la base de datos no respondieron (extensión `dependency`) | Reintentar más tarde; no se guardó nada |

Ejemplo `403` sin asignación a la sucursal:

```json
{
  "type": "https://sio/errors/sales/branch-access-denied",
  "title": "Acceso a la sucursal denegado",
  "status": 403,
  "detail": "No tiene una asignación activa a la sucursal de la venta, o la sucursal o la empresa no están activas. Solicite la asignación al administrador de la empresa.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales",
  "code": "SALES.BRANCH_ACCESS_DENIED",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

Ejemplo `422` por enviar `unit_price` en una línea:

```json
{
  "type": "https://sio/errors/sales/validation-error",
  "title": "Solicitud inválida",
  "status": 422,
  "detail": "La solicitud contiene datos inválidos.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales",
  "code": "SALES.VALIDATION_ERROR",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "lines[0].unit_price",
      "message": "El precio lo resuelve el sistema; no se admite precio manual.",
      "code": "UNIT_PRICE_NOT_ALLOWED"
    }
  ]
}
```

Ejemplo `409` con un cliente inactivo y una lista sin precio para la presentación:

```json
{
  "type": "https://sio/errors/sales/references-not-eligible",
  "title": "Referencias no aptas",
  "status": 409,
  "detail": "Una o más referencias existen, pero su estado o configuración actual impide usarlas en la venta.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales",
  "code": "SALES.REFERENCES_NOT_ELIGIBLE",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "company_customer_id",
      "message": "El cliente no está activo (INACTIVE).",
      "code": "CUSTOMER_NOT_ELIGIBLE"
    },
    {
      "field": "lines[0].price_list_id",
      "message": "La lista de precios no tiene precio vigente para la presentación.",
      "code": "PRICE_NOT_IN_LIST",
      "line_number": 1
    }
  ]
}
```

## 7. Agregar una línea a la venta

**Método:** `POST`
**URL:** `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}/details`
**Permiso requerido:** `perm:sales:sale_details:create`

### ¿Qué hace esta API?

Agrega una línea (producto, presentación, cantidad y, si el vendedor eligió un precio, su lista) a una venta en `DRAFT` y devuelve la **venta completa** con los totales recalculados. Es la API que se usa cada vez que el vendedor añade un producto al carrito. Una venta admite hasta 100 líneas; el mismo producto puede aparecer en varias líneas.

Efectos verificados en el código:

- Comprueba, en este orden: asignación `ACTIVE` a la sucursal de la venta, que no haya una confirmación o anulación en curso (`409 OPERATION_IN_PROGRESS`), estado `DRAFT` (`409 INVALID_STATUS`), `version` (`409 VERSION_CONFLICT`), formato de la línea (`422`) y referencias y precio (`422` o `409 REFERENCES_NOT_ELIGIBLE`).
- Resuelve el precio con la regla de precios del módulo y copia los datos del producto y la presentación en la línea. La línea toma el menor `line_number` libre (las líneas no se renumeran al eliminar).
- Incrementa la `version` de la venta y registra el evento de auditoría `ADD_SALE_DETAIL` (entidad `SaleDetail`).

Antes necesita: el `sale_id` y la `version` actual de la venta (respuesta de la [API 6](#6-crear-la-venta-en-borrador) o de la [API 10](#10-consultar-la-venta-con-sus-líneas-y-totales)) y los datos de la línea de las API 2 a 4.

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a/details' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
    "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
    "price_list_id": "7a8b9c0d-1e2f-4a3b-9c4d-5e6f7a8b9c0d",
    "quantity": "3",
    "version": 1
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa de la venta | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `sale_id` | UUID | Sí | Venta | `9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a` | `id` de la respuesta de la [API 6](#6-crear-la-venta-en-borrador) (crea la venta; errores en §6) o `items[].id` de la [API 13](#13-listar-y-buscar-las-ventas) (lista las ventas; errores en §13) · guía [sale_id](../parametros/sale-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
  "price_list_id": "7a8b9c0d-1e2f-4a3b-9c4d-5e6f7a8b9c0d",
  "quantity": "3",
  "version": 1
}
```
| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_product_id` | UUID | Sí | Producto empresarial `ACTIVE`, vendible y controlado por inventario | `e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `items[].company_product_id` de la [API 2](#2-buscar-productos-con-precio-y-existencias-en-la-sucursal) (busca productos con precio y existencias; errores en §2) · guía [company_product_id](../parametros/company-product-id.md) |
| `company_product_presentation_id` | UUID | Sí | Presentación `ACTIVE` y vendible de ese mismo producto | `a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83` | `items[].presentations[].company_product_presentation_id` de la [API 2](#2-buscar-productos-con-precio-y-existencias-en-la-sucursal) (presentaciones vendibles del producto; errores en §2) · guía [company_product_presentation_id](../parametros/company-product-presentation-id.md) |
| `price_list_id` | UUID \| null | No; por defecto `null` | Lista de precios del precio que eligió el vendedor; con `null` Sales usa la lista por defecto de la empresa | `7a8b9c0d-1e2f-4a3b-9c4d-5e6f7a8b9c0d` | `items[].price_list_id` del precio elegido en la [API 4](#4-consultar-los-precios-vigentes-de-una-presentación) (precios vigentes de la presentación; errores en §4) o `items[].presentations[].price.price_list_id` de la [API 2](#2-buscar-productos-con-precio-y-existencias-en-la-sucursal) (precio de la lista por defecto; errores en §2); `null` si el vendedor no eligió precio |
| `quantity` | number \| string | Sí | Cantidad en unidades de la presentación; mayor que cero, máximo 4 decimales | `"2"` | Interfaz (cantidad que escribe el vendedor) |
| `discount_amount` | number \| string | No; por defecto `0` | Descuento de la línea; en el MVP solo se admite `0` | `0` | No se envía |
| `tax_amount` | number \| string | No; por defecto `0` | Impuesto de la línea; en el MVP solo se admite `0` | `0` | No se envía |
| `version` | integer ≥ 1 | Sí | Versión actual de la venta | `1` | `version` de la respuesta de la [API 6](#6-crear-la-venta-en-borrador) (crea la venta; errores en §6) o de la [API 10](#10-consultar-la-venta-con-sus-líneas-y-totales) (consulta la venta; errores en §10) |

No se envía `unit_price` (`422 UNIT_PRICE_NOT_ALLOWED`) ni ningún otro campo (`UNKNOWN_FIELD`). En el ejemplo el vendedor eligió el precio de la lista mayorista, por eso la línea nueva vuelve con `price_list_requested: true`.

### Respuesta exitosa

`201 Created` (la venta completa, `SaleResponse` con `lines`, con la línea nueva y la `version` incrementada):

```json
{
  "id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_customer_id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "customer_payment_condition_id": null,
  "payment_condition_code_snapshot": "CASH",
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "payment_method_code_snapshot": "CASH",
  "payment_method_name_snapshot": "Efectivo",
  "payment_terms_days_snapshot": 0,
  "due_date": "2026-10-20",
  "sale_sequence_id": null,
  "number": null,
  "sequence_value": null,
  "status": "DRAFT",
  "operation_date": "2026-10-20",
  "customer_name_snapshot": "Ana Pérez",
  "customer_identification_snapshot": "CC 1012345678",
  "currency_code": "COP",
  "observations": "Venta mostrador",
  "subtotal": "3850.00",
  "discount_total": "0.00",
  "tax_total": "0.00",
  "total": "3850.00",
  "inventory_operation_id": null,
  "created_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancellation_reason": null,
  "pending_operation_id": null,
  "version": 2,
  "created_at": "2026-10-20T15:50:00Z",
  "updated_at": "2026-10-20T15:55:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "lines": [
    {
      "id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
      "sale_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
      "line_number": 1,
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
      "price_list_item_id": "6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c",
      "price_list_requested": false,
      "price_source": "PRICE_LIST_ITEM",
      "product_code_snapshot": "PRD-0001",
      "product_name_snapshot": "Acetaminofén 500 mg",
      "presentation_code_snapshot": "UN",
      "presentation_name_snapshot": "Unidad",
      "base_quantity_factor_snapshot": "1.00000000",
      "unit_code_snapshot": "UN",
      "quantity": "2.0000",
      "base_quantity": "2.0000",
      "unit_price": "800.0000",
      "discount_amount": "0.00",
      "tax_amount": "0.00",
      "subtotal": "1600.00",
      "total": "1600.00",
      "created_at": "2026-10-20T15:50:00Z",
      "updated_at": "2026-10-20T15:50:00Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    },
    {
      "id": "b1a1e4be-5fb8-42b0-81c5-ca85b2fdcea6",
      "sale_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
      "line_number": 2,
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "price_list_id": "7a8b9c0d-1e2f-4a3b-9c4d-5e6f7a8b9c0d",
      "price_list_item_id": "8b9c0d1e-2f3a-4b4c-8d5e-6f7a8b9c0d1e",
      "price_list_requested": true,
      "price_source": "PRICE_LIST_ITEM",
      "product_code_snapshot": "PRD-0001",
      "product_name_snapshot": "Acetaminofén 500 mg",
      "presentation_code_snapshot": "UN",
      "presentation_name_snapshot": "Unidad",
      "base_quantity_factor_snapshot": "1.00000000",
      "unit_code_snapshot": "UN",
      "quantity": "3.0000",
      "base_quantity": "3.0000",
      "unit_price": "750.0000",
      "discount_amount": "0.00",
      "tax_amount": "0.00",
      "subtotal": "2250.00",
      "total": "2250.00",
      "created_at": "2026-10-20T15:55:00Z",
      "updated_at": "2026-10-20T15:55:00Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ]
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `version` | integer | Nueva versión de la venta; enviarla en la siguiente escritura |
| `lines[]` | array | Todas las líneas de la venta, con la nueva al final de su `line_number`; los campos se describen en la [API 6](#6-crear-la-venta-en-borrador) |
| `lines[].id` | UUID | `detail_id` de la línea nueva, para modificarla (API 8) o eliminarla (API 9) |
| `lines[].unit_price`, `price_list_id`, `price_list_requested` | string, UUID, boolean | Precio que aplicó Sales y si lo eligió el vendedor; mostrar este precio, no el de la consulta previa |
| `subtotal`, `total` | string | Totales de la venta recalculados |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `403` | `SALES.BRANCH_ACCESS_DENIED` | El usuario no tiene asignación `ACTIVE` a la sucursal de la venta, o la sucursal o la empresa están inactivas | Mostrar el mensaje y pedir la asignación al administrador ([API 12 de Administración empresarial](administracion-empresarial.md#12-asignar-un-usuario-a-una-sucursal)) |
| `403` | `SALES.OPERATIONAL_ACCESS_DENIED` | Operational Context no permite al usuario consultar su acceso operativo | Pedir `perm:operational-context:application_users:read` indicando el `trace_id` |
| `404` | `SALES.NOT_FOUND` | La empresa no existe, el usuario no es miembro `ACTIVE`, la sucursal es de otra empresa o la venta no existe en la empresa | Volver a leer el contexto operativo o la lista de ventas |
| `409` | `SALES.OPERATION_IN_PROGRESS` | La venta tiene una confirmación o anulación en curso (extensión `operation_id`) | Esperar y volver a leer la venta con la [API 10](#10-consultar-la-venta-con-sus-líneas-y-totales) |
| `409` | `SALES.INVALID_STATUS` | La venta no está en `DRAFT`; en este error el campo `status` del cuerpo trae el estado actual de la venta (`CONFIRMED` o `CANCELLED`), no el número HTTP | Volver a leer la venta; una venta confirmada o anulada ya no se edita |
| `409` | `SALES.VERSION_CONFLICT` | La `version` enviada no es la actual | Volver a leer la venta con la [API 10](#10-consultar-la-venta-con-sus-líneas-y-totales) y repetir con la nueva `version` |
| `422` | `SALES.VALIDATION_ERROR` | Datos de la línea inválidos (también `LINES_LIMIT_EXCEEDED` si la venta ya tiene 100 líneas); `errors[].code`: `REQUIRED`, `UNKNOWN_FIELD`, `INVALID_FORMAT`, `UNIT_PRICE_NOT_ALLOWED` (se envió `unit_price`), `QUANTITY_NOT_POSITIVE`, `TOO_MANY_DECIMALS`, `AMOUNT_OUT_OF_RANGE`, `BASE_QUANTITY_PRECISION`, `DISCOUNT_NOT_ALLOWED`, `TAX_NOT_ALLOWED`; o referencias inexistentes, de otra empresa o incoherentes: `COMPANY_PRODUCT_NOT_FOUND`, `PRESENTATION_NOT_FOUND`, `PRESENTATION_OF_OTHER_PRODUCT`, `PRICE_LIST_NOT_FOUND` | Mostrar cada `errors[].message` junto al campo (`errors[].field`) y corregir |
| `409` | `SALES.REFERENCES_NOT_ELIGIBLE` | Una referencia existe pero no se puede usar; `errors[].code`: `COMPANY_INACTIVE`, `BRANCH_INACTIVE`, `CUSTOMER_NOT_ELIGIBLE` (cliente inactivo), `CUSTOMER_IDENTIFICATION_MISSING`, `PAYMENT_METHOD_INACTIVE`, `PRODUCT_INACTIVE`, `PRODUCT_NOT_SELLABLE`, `PRODUCT_NOT_INVENTORY_CONTROLLED`, `PRESENTATION_INACTIVE`, `PRESENTATION_NOT_SELLABLE`, `PRICE_NOT_IN_LIST` (la lista elegida no tiene precio vigente para la presentación), `PRICE_NOT_AVAILABLE` (no hay lista por defecto vigente con precio), `PRICE_LIST_NOT_APPLICABLE` (lista inactiva o no vigente), `PRICE_CURRENCY_MISMATCH`, `APPLICATION_USER_INACTIVE` | Mostrar cada `errors[].message` junto al campo o la línea (`line_number`) y pedir otra referencia o corregir la configuración |
| `503` | `SALES.DEPENDENCY_UNAVAILABLE` | Operational Context, Commercial Relationship, Party Identity, Payment Reference o la base de datos no respondieron (extensión `dependency`) | Reintentar más tarde; no se guardó nada |

Ejemplo `409` cuando otra persona modificó la venta antes:

```json
{
  "type": "https://sio/errors/sales/version-conflict",
  "title": "Conflicto de versión",
  "status": 409,
  "detail": "El recurso cambió desde la última consulta. Vuelva a consultarlo e intente de nuevo.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a/details",
  "code": "SALES.VERSION_CONFLICT",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

## 8. Modificar una línea de la venta

**Método:** `PUT`
**URL:** `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}/details/{detail_id}`
**Permiso requerido:** `perm:sales:sale_details:update`

### ¿Qué hace esta API?

Reemplaza los datos de una línea de una venta en `DRAFT`: cantidad, presentación, producto o lista de precios. Se envía la línea **completa** (los mismos campos que en la [API 7](#7-agregar-una-línea-a-la-venta)), no solo lo que cambió. Devuelve la venta completa con los totales recalculados. También es la forma de **actualizar el precio** de una línea cuando la confirmación responde `409 SALES.PRICES_CHANGED`: basta con volver a enviar la línea con los mismos datos para que Sales resuelva y guarde el precio vigente.

Efectos verificados en el código: mismas comprobaciones y mismo orden que la [API 7](#7-agregar-una-línea-a-la-venta); vuelve a resolver el precio y a copiar los datos del producto y la presentación; conserva el `line_number`; incrementa la `version` de la venta y registra el evento de auditoría `UPDATE_SALE_DETAIL` (entidad `SaleDetail`).

Antes necesita: `sale_id`, `version` actual y el `detail_id` (`lines[].id`) de la línea, tomados de la respuesta de la [API 10](#10-consultar-la-venta-con-sus-líneas-y-totales) o de la última escritura.

### ¿Cómo se realiza la solicitud?

```bash
curl -X PUT \
  'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a/details/b1a1e4be-5fb8-42b0-81c5-ca85b2fdcea6' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
    "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
    "price_list_id": "7a8b9c0d-1e2f-4a3b-9c4d-5e6f7a8b9c0d",
    "quantity": "5",
    "version": 2
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa de la venta | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `sale_id` | UUID | Sí | Venta | `9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a` | `id` de la respuesta de la [API 6](#6-crear-la-venta-en-borrador) (crea la venta; errores en §6) o `items[].id` de la [API 13](#13-listar-y-buscar-las-ventas) (lista las ventas; errores en §13) · guía [sale_id](../parametros/sale-id.md) |
| `detail_id` | UUID | Sí | Línea que se modifica | `b1a1e4be-5fb8-42b0-81c5-ca85b2fdcea6` | `lines[].id` de la respuesta de la [API 10](#10-consultar-la-venta-con-sus-líneas-y-totales) (consulta la venta con sus líneas; errores en §10) o de la [API 7](#7-agregar-una-línea-a-la-venta) (agrega la línea; errores en §7) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
  "price_list_id": "7a8b9c0d-1e2f-4a3b-9c4d-5e6f7a8b9c0d",
  "quantity": "5",
  "version": 2
}
```
| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_product_id` | UUID | Sí | Producto empresarial `ACTIVE`, vendible y controlado por inventario | `e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `items[].company_product_id` de la [API 2](#2-buscar-productos-con-precio-y-existencias-en-la-sucursal) (busca productos con precio y existencias; errores en §2) · guía [company_product_id](../parametros/company-product-id.md) |
| `company_product_presentation_id` | UUID | Sí | Presentación `ACTIVE` y vendible de ese mismo producto | `a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83` | `items[].presentations[].company_product_presentation_id` de la [API 2](#2-buscar-productos-con-precio-y-existencias-en-la-sucursal) (presentaciones vendibles del producto; errores en §2) · guía [company_product_presentation_id](../parametros/company-product-presentation-id.md) |
| `price_list_id` | UUID \| null | No; por defecto `null` | Lista de precios del precio que eligió el vendedor; con `null` Sales usa la lista por defecto de la empresa | `7a8b9c0d-1e2f-4a3b-9c4d-5e6f7a8b9c0d` | `items[].price_list_id` del precio elegido en la [API 4](#4-consultar-los-precios-vigentes-de-una-presentación) (precios vigentes de la presentación; errores en §4) o `items[].presentations[].price.price_list_id` de la [API 2](#2-buscar-productos-con-precio-y-existencias-en-la-sucursal) (precio de la lista por defecto; errores en §2); `null` si el vendedor no eligió precio |
| `quantity` | number \| string | Sí | Cantidad en unidades de la presentación; mayor que cero, máximo 4 decimales | `"5"` | Interfaz (cantidad que escribe el vendedor) |
| `discount_amount` | number \| string | No; por defecto `0` | Descuento de la línea; en el MVP solo se admite `0` | `0` | No se envía |
| `tax_amount` | number \| string | No; por defecto `0` | Impuesto de la línea; en el MVP solo se admite `0` | `0` | No se envía |
| `version` | integer ≥ 1 | Sí | Versión actual de la venta (no de la línea) | `2` | `version` de la respuesta de la [API 10](#10-consultar-la-venta-con-sus-líneas-y-totales) (consulta la venta; errores en §10) o de la última escritura |

Como en la API 7, no se envía `unit_price` ni ningún campo no listado.

### Respuesta exitosa

`200 OK` (la venta completa, `SaleResponse` con `lines`):

```json
{
  "id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_customer_id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "customer_payment_condition_id": null,
  "payment_condition_code_snapshot": "CASH",
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "payment_method_code_snapshot": "CASH",
  "payment_method_name_snapshot": "Efectivo",
  "payment_terms_days_snapshot": 0,
  "due_date": "2026-10-20",
  "sale_sequence_id": null,
  "number": null,
  "sequence_value": null,
  "status": "DRAFT",
  "operation_date": "2026-10-20",
  "customer_name_snapshot": "Ana Pérez",
  "customer_identification_snapshot": "CC 1012345678",
  "currency_code": "COP",
  "observations": "Venta mostrador",
  "subtotal": "5350.00",
  "discount_total": "0.00",
  "tax_total": "0.00",
  "total": "5350.00",
  "inventory_operation_id": null,
  "created_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancellation_reason": null,
  "pending_operation_id": null,
  "version": 3,
  "created_at": "2026-10-20T15:50:00Z",
  "updated_at": "2026-10-20T16:00:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "lines": [
    {
      "id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
      "sale_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
      "line_number": 1,
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
      "price_list_item_id": "6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c",
      "price_list_requested": false,
      "price_source": "PRICE_LIST_ITEM",
      "product_code_snapshot": "PRD-0001",
      "product_name_snapshot": "Acetaminofén 500 mg",
      "presentation_code_snapshot": "UN",
      "presentation_name_snapshot": "Unidad",
      "base_quantity_factor_snapshot": "1.00000000",
      "unit_code_snapshot": "UN",
      "quantity": "2.0000",
      "base_quantity": "2.0000",
      "unit_price": "800.0000",
      "discount_amount": "0.00",
      "tax_amount": "0.00",
      "subtotal": "1600.00",
      "total": "1600.00",
      "created_at": "2026-10-20T15:50:00Z",
      "updated_at": "2026-10-20T15:50:00Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    },
    {
      "id": "b1a1e4be-5fb8-42b0-81c5-ca85b2fdcea6",
      "sale_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
      "line_number": 2,
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "price_list_id": "7a8b9c0d-1e2f-4a3b-9c4d-5e6f7a8b9c0d",
      "price_list_item_id": "8b9c0d1e-2f3a-4b4c-8d5e-6f7a8b9c0d1e",
      "price_list_requested": true,
      "price_source": "PRICE_LIST_ITEM",
      "product_code_snapshot": "PRD-0001",
      "product_name_snapshot": "Acetaminofén 500 mg",
      "presentation_code_snapshot": "UN",
      "presentation_name_snapshot": "Unidad",
      "base_quantity_factor_snapshot": "1.00000000",
      "unit_code_snapshot": "UN",
      "quantity": "5.0000",
      "base_quantity": "5.0000",
      "unit_price": "750.0000",
      "discount_amount": "0.00",
      "tax_amount": "0.00",
      "subtotal": "3750.00",
      "total": "3750.00",
      "created_at": "2026-10-20T15:55:00Z",
      "updated_at": "2026-10-20T16:00:00Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ]
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `version` | integer | Nueva versión de la venta |
| `lines[]` | array | Líneas con la modificada actualizada (`quantity`, `unit_price`, `subtotal`, `total`, `updated_at`); los campos se describen en la [API 6](#6-crear-la-venta-en-borrador) |
| `subtotal`, `total` | string | Totales recalculados |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `403` | `SALES.BRANCH_ACCESS_DENIED` | El usuario no tiene asignación `ACTIVE` a la sucursal de la venta, o la sucursal o la empresa están inactivas | Mostrar el mensaje y pedir la asignación al administrador ([API 12 de Administración empresarial](administracion-empresarial.md#12-asignar-un-usuario-a-una-sucursal)) |
| `403` | `SALES.OPERATIONAL_ACCESS_DENIED` | Operational Context no permite al usuario consultar su acceso operativo | Pedir `perm:operational-context:application_users:read` indicando el `trace_id` |
| `404` | `SALES.NOT_FOUND` | La empresa, la venta o la línea no existen en el alcance del usuario | Volver a leer la venta con la [API 10](#10-consultar-la-venta-con-sus-líneas-y-totales) |
| `409` | `SALES.OPERATION_IN_PROGRESS` | La venta tiene una confirmación o anulación en curso (extensión `operation_id`) | Esperar y volver a leer la venta con la [API 10](#10-consultar-la-venta-con-sus-líneas-y-totales) |
| `409` | `SALES.INVALID_STATUS` | La venta no está en `DRAFT`; en este error el campo `status` del cuerpo trae el estado actual de la venta (`CONFIRMED` o `CANCELLED`), no el número HTTP | Volver a leer la venta; una venta confirmada o anulada ya no se edita |
| `409` | `SALES.VERSION_CONFLICT` | La `version` enviada no es la actual | Volver a leer la venta con la [API 10](#10-consultar-la-venta-con-sus-líneas-y-totales) y repetir con la nueva `version` |
| `422` | `SALES.VALIDATION_ERROR` | Datos de la línea inválidos; `errors[].code`: `REQUIRED`, `UNKNOWN_FIELD`, `INVALID_FORMAT`, `UNIT_PRICE_NOT_ALLOWED` (se envió `unit_price`), `QUANTITY_NOT_POSITIVE`, `TOO_MANY_DECIMALS`, `AMOUNT_OUT_OF_RANGE`, `BASE_QUANTITY_PRECISION`, `DISCOUNT_NOT_ALLOWED`, `TAX_NOT_ALLOWED`; o referencias inexistentes, de otra empresa o incoherentes: `COMPANY_PRODUCT_NOT_FOUND`, `PRESENTATION_NOT_FOUND`, `PRESENTATION_OF_OTHER_PRODUCT`, `PRICE_LIST_NOT_FOUND` | Mostrar cada `errors[].message` junto al campo (`errors[].field`) y corregir |
| `409` | `SALES.REFERENCES_NOT_ELIGIBLE` | Una referencia existe pero no se puede usar; `errors[].code`: `COMPANY_INACTIVE`, `BRANCH_INACTIVE`, `CUSTOMER_NOT_ELIGIBLE` (cliente inactivo), `CUSTOMER_IDENTIFICATION_MISSING`, `PAYMENT_METHOD_INACTIVE`, `PRODUCT_INACTIVE`, `PRODUCT_NOT_SELLABLE`, `PRODUCT_NOT_INVENTORY_CONTROLLED`, `PRESENTATION_INACTIVE`, `PRESENTATION_NOT_SELLABLE`, `PRICE_NOT_IN_LIST` (la lista elegida no tiene precio vigente para la presentación), `PRICE_NOT_AVAILABLE` (no hay lista por defecto vigente con precio), `PRICE_LIST_NOT_APPLICABLE` (lista inactiva o no vigente), `PRICE_CURRENCY_MISMATCH`, `APPLICATION_USER_INACTIVE` | Mostrar cada `errors[].message` junto al campo o la línea (`line_number`) y pedir otra referencia o corregir la configuración |
| `503` | `SALES.DEPENDENCY_UNAVAILABLE` | Operational Context, Commercial Relationship, Party Identity, Payment Reference o la base de datos no respondieron (extensión `dependency`) | Reintentar más tarde; no se guardó nada |

Ejemplo `409` al intentar modificar una venta ya confirmada:

```json
{
  "type": "https://sio/errors/sales/invalid-status",
  "title": "Estado no permitido",
  "status": "CONFIRMED",
  "detail": "La acción no está permitida para una venta en estado CONFIRMED.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a/details/b1a1e4be-5fb8-42b0-81c5-ca85b2fdcea6",
  "code": "SALES.INVALID_STATUS",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

## 9. Eliminar una línea de la venta

**Método:** `DELETE`
**URL:** `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}/details/{detail_id}?version={version}`
**Permiso requerido:** `perm:sales:sale_details:delete`

### ¿Qué hace esta API?

Elimina una línea de una venta en `DRAFT` y devuelve la venta completa sin esa línea y con los totales recalculados. La `version` de la venta va como **parámetro de consulta**, porque la solicitud no lleva cuerpo.

Efectos verificados en el código: comprueba asignación a la sucursal, operación en curso, estado `DRAFT` y `version` en ese orden; las líneas restantes **no** se renumeran (una línea nueva tomará el menor número libre); incrementa la `version` y registra el evento de auditoría `DELETE_SALE_DETAIL` (entidad `SaleDetail`). Una venta puede quedar sin líneas, pero así no se puede confirmar (`422 SALES.SALE_WITHOUT_LINES`).

Antes necesita: `sale_id`, `version` actual y `detail_id` de la línea, tomados de la [API 10](#10-consultar-la-venta-con-sus-líneas-y-totales) o de la última escritura.

### ¿Cómo se realiza la solicitud?

```bash
curl -X DELETE \
  'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a/details/b1a1e4be-5fb8-42b0-81c5-ca85b2fdcea6?version=3' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa de la venta | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `sale_id` | UUID | Sí | Venta | `9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a` | `id` de la respuesta de la [API 6](#6-crear-la-venta-en-borrador) (crea la venta; errores en §6) o `items[].id` de la [API 13](#13-listar-y-buscar-las-ventas) (lista las ventas; errores en §13) · guía [sale_id](../parametros/sale-id.md) |
| `detail_id` | UUID | Sí | Línea que se elimina | `b1a1e4be-5fb8-42b0-81c5-ca85b2fdcea6` | `lines[].id` de la respuesta de la [API 10](#10-consultar-la-venta-con-sus-líneas-y-totales) (consulta la venta con sus líneas; errores en §10) o de la última escritura |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `version` | integer ≥ 1 | Sí | Versión actual de la venta | Entero desde `1`; p. ej. `3` | `?version=3` | `version` de la respuesta de la [API 10](#10-consultar-la-venta-con-sus-líneas-y-totales) (consulta la venta; errores en §10) o de la última escritura |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a/details/b1a1e4be-5fb8-42b0-81c5-ca85b2fdcea6?version=3`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (la venta completa, `SaleResponse` con `lines`, sin la línea eliminada):

```json
{
  "id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_customer_id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "customer_payment_condition_id": null,
  "payment_condition_code_snapshot": "CASH",
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "payment_method_code_snapshot": "CASH",
  "payment_method_name_snapshot": "Efectivo",
  "payment_terms_days_snapshot": 0,
  "due_date": "2026-10-20",
  "sale_sequence_id": null,
  "number": null,
  "sequence_value": null,
  "status": "DRAFT",
  "operation_date": "2026-10-20",
  "customer_name_snapshot": "Ana Pérez",
  "customer_identification_snapshot": "CC 1012345678",
  "currency_code": "COP",
  "observations": "Venta mostrador",
  "subtotal": "1600.00",
  "discount_total": "0.00",
  "tax_total": "0.00",
  "total": "1600.00",
  "inventory_operation_id": null,
  "created_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancellation_reason": null,
  "pending_operation_id": null,
  "version": 4,
  "created_at": "2026-10-20T15:50:00Z",
  "updated_at": "2026-10-20T16:05:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "lines": [
    {
      "id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
      "sale_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
      "line_number": 1,
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
      "price_list_item_id": "6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c",
      "price_list_requested": false,
      "price_source": "PRICE_LIST_ITEM",
      "product_code_snapshot": "PRD-0001",
      "product_name_snapshot": "Acetaminofén 500 mg",
      "presentation_code_snapshot": "UN",
      "presentation_name_snapshot": "Unidad",
      "base_quantity_factor_snapshot": "1.00000000",
      "unit_code_snapshot": "UN",
      "quantity": "2.0000",
      "base_quantity": "2.0000",
      "unit_price": "800.0000",
      "discount_amount": "0.00",
      "tax_amount": "0.00",
      "subtotal": "1600.00",
      "total": "1600.00",
      "created_at": "2026-10-20T15:50:00Z",
      "updated_at": "2026-10-20T15:50:00Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ]
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `version` | integer | Nueva versión de la venta |
| `lines[]` | array | Líneas restantes, con su `line_number` original; los campos se describen en la [API 6](#6-crear-la-venta-en-borrador) |
| `subtotal`, `total` | string | Totales recalculados; `0.00` si no quedan líneas |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `403` | `SALES.BRANCH_ACCESS_DENIED` | El usuario no tiene asignación `ACTIVE` a la sucursal de la venta, o la sucursal o la empresa están inactivas | Mostrar el mensaje y pedir la asignación al administrador ([API 12 de Administración empresarial](administracion-empresarial.md#12-asignar-un-usuario-a-una-sucursal)) |
| `403` | `SALES.OPERATIONAL_ACCESS_DENIED` | Operational Context no permite al usuario consultar su acceso operativo | Pedir `perm:operational-context:application_users:read` indicando el `trace_id` |
| `404` | `SALES.NOT_FOUND` | La empresa, la venta o la línea no existen en el alcance del usuario | Volver a leer la venta con la [API 10](#10-consultar-la-venta-con-sus-líneas-y-totales) |
| `409` | `SALES.OPERATION_IN_PROGRESS` | La venta tiene una confirmación o anulación en curso (extensión `operation_id`) | Esperar y volver a leer la venta con la [API 10](#10-consultar-la-venta-con-sus-líneas-y-totales) |
| `409` | `SALES.INVALID_STATUS` | La venta no está en `DRAFT`; en este error el campo `status` del cuerpo trae el estado actual de la venta (`CONFIRMED` o `CANCELLED`), no el número HTTP | Volver a leer la venta; una venta confirmada o anulada ya no se edita |
| `409` | `SALES.VERSION_CONFLICT` | La `version` enviada no es la actual | Volver a leer la venta con la [API 10](#10-consultar-la-venta-con-sus-líneas-y-totales) y repetir con la nueva `version` |
| `422` | `SALES.VALIDATION_ERROR` | Falta `version` (`REQUIRED`) o no es un entero ≥ 1 (`INVALID_FORMAT`), o un UUID de la ruta está mal formado | Enviar la `version` actual |
| `503` | `SALES.DEPENDENCY_UNAVAILABLE` | Operational Context o la base de datos no respondieron (extensión `dependency`) | Reintentar más tarde; no se eliminó nada |

## 10. Consultar la venta con sus líneas y totales

**Método:** `GET`
**URL:** `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}`
**Permiso requerido:** `perm:sales:sales:read`

### ¿Qué hace esta API?

Devuelve una venta completa: encabezado, líneas, totales, estado, número (si está confirmada), datos de anulación y la `version` actual. Es la consulta con la que la interfaz muestra el borrador mientras se arma, recupera la `version` antes de cualquier escritura, vuelve a leer la venta después de un `409 VERSION_CONFLICT` o `409 SALES.PRICES_CHANGED` y muestra el documento confirmado o anulado. Si la venta tiene `pending_operation_id`, hay una confirmación o anulación en curso.

Solo exige membresía `ACTIVE` en la empresa (no asignación a la sucursal) y funciona aunque la empresa esté inactiva. No modifica nada.

Antes necesita: el `sale_id` de la [API 6](#6-crear-la-venta-en-borrador) o de la [API 13](#13-listar-y-buscar-las-ventas).

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa de la venta | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `sale_id` | UUID | Sí | Venta | `9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a` | `id` de la respuesta de la [API 6](#6-crear-la-venta-en-borrador) (crea la venta; errores en §6) o `items[].id` de la [API 13](#13-listar-y-buscar-las-ventas) (lista las ventas; errores en §13) · guía [sale_id](../parametros/sale-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`SaleResponse` con `lines`; aquí el borrador después de eliminar la segunda línea en la API 9):

```json
{
  "id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_customer_id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "customer_payment_condition_id": null,
  "payment_condition_code_snapshot": "CASH",
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "payment_method_code_snapshot": "CASH",
  "payment_method_name_snapshot": "Efectivo",
  "payment_terms_days_snapshot": 0,
  "due_date": "2026-10-20",
  "sale_sequence_id": null,
  "number": null,
  "sequence_value": null,
  "status": "DRAFT",
  "operation_date": "2026-10-20",
  "customer_name_snapshot": "Ana Pérez",
  "customer_identification_snapshot": "CC 1012345678",
  "currency_code": "COP",
  "observations": "Venta mostrador",
  "subtotal": "1600.00",
  "discount_total": "0.00",
  "tax_total": "0.00",
  "total": "1600.00",
  "inventory_operation_id": null,
  "created_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancellation_reason": null,
  "pending_operation_id": null,
  "version": 4,
  "created_at": "2026-10-20T15:50:00Z",
  "updated_at": "2026-10-20T16:05:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "lines": [
    {
      "id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
      "sale_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
      "line_number": 1,
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
      "price_list_item_id": "6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c",
      "price_list_requested": false,
      "price_source": "PRICE_LIST_ITEM",
      "product_code_snapshot": "PRD-0001",
      "product_name_snapshot": "Acetaminofén 500 mg",
      "presentation_code_snapshot": "UN",
      "presentation_name_snapshot": "Unidad",
      "base_quantity_factor_snapshot": "1.00000000",
      "unit_code_snapshot": "UN",
      "quantity": "2.0000",
      "base_quantity": "2.0000",
      "unit_price": "800.0000",
      "discount_amount": "0.00",
      "tax_amount": "0.00",
      "subtotal": "1600.00",
      "total": "1600.00",
      "created_at": "2026-10-20T15:50:00Z",
      "updated_at": "2026-10-20T15:50:00Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ]
}
```

Los campos son los descritos en la [API 6](#6-crear-la-venta-en-borrador). Para el frontend son clave `status`, `version`, `pending_operation_id`, `lines[].id` (el `detail_id` de las API 8 y 9), `lines[].line_number`, `lines[].unit_price` y los totales.

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `version` | integer | Versión que se envía en la siguiente escritura |
| `status` | `DRAFT` \| `CONFIRMED` \| `CANCELLED` | Define qué acciones se muestran: editar y confirmar solo en `DRAFT`, anular en `DRAFT` o `CONFIRMED` |
| `pending_operation_id` | UUID \| null | Si tiene valor, deshabilitar las acciones y volver a consultar más tarde |
| `lines[]` | array | Líneas ordenadas por `line_number` |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `403` | `SALES.OPERATIONAL_ACCESS_DENIED` | Operational Context no permite al usuario consultar su acceso operativo | Pedir `perm:operational-context:application_users:read` indicando el `trace_id` |
| `404` | `SALES.NOT_FOUND` | La empresa no existe, el usuario no es miembro `ACTIVE` o la venta no existe en la empresa | Volver a leer el contexto operativo o la lista de ventas |
| `422` | `SALES.VALIDATION_ERROR` | `company_id` o `sale_id` no son UUID (`INVALID_FORMAT`) | Corregir la ruta |
| `503` | `SALES.DEPENDENCY_UNAVAILABLE` | Operational Context o la base de datos no respondieron (extensión `dependency`) | Reintentar más tarde |

Ejemplo `404` con una venta inexistente o de otra empresa:

```json
{
  "type": "https://sio/errors/sales/not-found",
  "title": "Recurso no encontrado",
  "status": 404,
  "detail": "El recurso solicitado no existe o no está disponible para su usuario.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
  "code": "SALES.NOT_FOUND",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

## 11. Verificar la disponibilidad antes de confirmar

**Método:** `GET`
**URL:** `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}/availability`
**Permiso requerido:** `perm:sales:sales:read`

### ¿Qué hace esta API?

Consulta en Inventory las existencias de la sucursal de la venta para cada producto de sus líneas y dice si alcanzan. Las líneas del mismo producto se suman (`line_numbers` indica cuáles) y la cantidad se compara en unidad base (`quantity × factor`). Sirve para avisar al vendedor **antes** de confirmar; **no reserva** existencias: otra venta puede consumirlas entre esta consulta y la confirmación, y la verificación definitiva la hace Inventory al confirmar (`409 SALES.INSUFFICIENT_STOCK`).

Solo exige membresía `ACTIVE` en la empresa. No modifica nada.

Antes necesita: el `sale_id` de una venta con líneas.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a/availability' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa de la venta | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `sale_id` | UUID | Sí | Venta | `9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a` | `id` de la respuesta de la [API 6](#6-crear-la-venta-en-borrador) (crea la venta; errores en §6) o `items[].id` de la [API 13](#13-listar-y-buscar-las-ventas) (lista las ventas; errores en §13) · guía [sale_id](../parametros/sale-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`AvailabilityResponse`):

```json
{
  "sale_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "all_available": true,
  "products": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "line_numbers": [
        1
      ],
      "required_base_quantity": "2.0000",
      "available_base_quantity": "800.0000",
      "is_available": true
    }
  ]
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `all_available` | boolean | `true` si todas las líneas tienen existencias suficientes; si es `false`, avisar antes de confirmar |
| `branch_id` | UUID | Sucursal cuyas existencias se consultaron (la de la venta) |
| `products[].company_product_id` | UUID | Producto |
| `products[].line_numbers` | array de integer | Líneas de la venta que usan ese producto |
| `products[].required_base_quantity`, `available_base_quantity` | string | Cantidad pedida y disponible en unidad base (4 decimales) |
| `products[].is_available` | boolean | Si alcanza para ese producto; marcar las líneas con `false` |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `403` | `SALES.OPERATIONAL_ACCESS_DENIED` | Operational Context no permite al usuario consultar su acceso operativo | Pedir `perm:operational-context:application_users:read` indicando el `trace_id` |
| `404` | `SALES.NOT_FOUND` | La empresa no existe, el usuario no es miembro `ACTIVE` o la venta no existe en la empresa | Volver a leer el contexto operativo o la lista de ventas |
| `503` | `SALES.DEPENDENCY_UNAVAILABLE` | Inventory, Operational Context o la base de datos no respondieron (extensión `dependency`, p. ej. `inventory`) | Permitir confirmar igualmente: la confirmación hace la verificación definitiva |

## 12. Confirmar la venta

**Método:** `POST`
**URL:** `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}/confirmation`
**Permiso requerido:** `perm:sales:sales:update`

### ¿Qué hace esta API?

Convierte el borrador en una venta **confirmada**: descuenta las existencias en Inventory, copia los costos FIFO de la salida, asigna el número del documento y deja la venta en `CONFIRMED`. Es una operación de **alto riesgo** e idempotente: exige el encabezado `Idempotency-Key` y, si la respuesta no llega (corte de red, tiempo agotado), se repite **con la misma clave** y se obtiene el mismo resultado sin descontar dos veces.

Efectos verificados en el código, en este orden:

1. Asignación `ACTIVE` a la sucursal; repetición con la misma clave (devuelve el resultado guardado o retoma una operación pendiente; la clave queda ligada a la venta, a la acción y al usuario, si no `409 IDEMPOTENCY_KEY_CONFLICT`); operación en curso (`409 OPERATION_IN_PROGRESS`); estado `DRAFT` (`409 INVALID_STATUS`); `version` (`409 VERSION_CONFLICT`); venta con al menos una línea (`422 SALE_WITHOUT_LINES`).
2. Vuelve a validar el cliente, los productos, las presentaciones, el método de pago y el usuario operativo (`422` o `409 REFERENCES_NOT_ELIGIBLE`) y **vuelve a resolver el precio** de cada línea con la misma intención (lista elegida o lista por defecto). Si el precio, la lista o el ítem de precio cambiaron respecto de lo guardado, responde `409 SALES.PRICES_CHANGED` sin efectos.
3. Consulta informativa de existencias: si no alcanzan, `409 SALES.INSUFFICIENT_STOCK` sin efectos (si Inventory no responde en este paso, sigue adelante).
4. Busca la secuencia de ventas activa de la sucursal o, si no hay, la de la empresa, para el período de la fecha del día en la zona horaria de la sucursal: sin secuencia `409 SALES.SEQUENCE_NOT_CONFIGURED`; agotada `409 SALES.SEQUENCE_EXHAUSTED`. Las secuencias se administran con las [API 18 a 21 de Administración empresarial](administracion-empresarial.md#18-consultar-las-secuencias-de-numeración).
5. Registra la operación `CONFIRM` en `PENDING`, fija `operation_date` y `due_date` y congela los datos copiados. Envía la salida a Inventory (origen `SALE`, una salida por línea, clave = `id` de la operación).
6. Con la salida aplicada: copia los costos FIFO de cada línea, asigna `number` y `sequence_value` de la secuencia, deja la venta `CONFIRMED`, la operación `SUCCEEDED` y registra el evento de auditoría `CONFIRM_SALE`. Nunca se consume un número sin confirmar: si la numeración falla después de aplicar la salida, Sales pide el reverso en Inventory.

Si Inventory rechaza la salida por existencias, responde `409 SALES.INSUFFICIENT_STOCK` con los faltantes por línea; por otra causa, `409 SALES.INVENTORY_REJECTED` y la operación queda `FAILED` (la venta sigue en `DRAFT`). Si Inventory **no responde**, la respuesta es `503 SALES.DEPENDENCY_UNAVAILABLE` con `operation_id`: la operación queda `PENDING`, la venta muestra `pending_operation_id` y un proceso de conciliación la termina; el frontend repite la solicitud con la **misma** `Idempotency-Key` o consulta la venta (API 10) hasta que `pending_operation_id` sea `null`. El seguimiento detallado de la operación está en Sales 13 y 14 ([ficha](../servicios/sales.md#13-get-companiescompany_idsalessale_idoperations), permiso `perm:sales:sale_operations:read`).

Antes necesita: `sale_id` y `version` actual de la venta (API 10), al menos una línea, una secuencia de numeración activa y existencias suficientes en la sucursal (API 11).

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a/confirmation' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Idempotency-Key: 4f7c1d2e-8a9b-4c3d-9e5f-6a7b8c9d0e1f' \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 4
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa de la venta | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `sale_id` | UUID | Sí | Venta | `9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a` | `id` de la respuesta de la [API 6](#6-crear-la-venta-en-borrador) (crea la venta; errores en §6) o `items[].id` de la [API 13](#13-listar-y-buscar-las-ventas) (lista las ventas; errores en §13) · guía [sale_id](../parametros/sale-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `Authorization` | string | Sí | `Bearer` y el Access Token | `Bearer TU_ACCESS_TOKEN` | `access_token` de la [API 1 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#1-iniciar-sesión-usuario-y-contraseña) (inicia sesión; sus errores están en esa sección) |
| `Content-Type` | string | Sí | Tipo del cuerpo | `application/json` | Fijo |
| `Idempotency-Key` | string (1–150, ASCII imprimible sin espacios) | Sí | Clave única de este intento de confirmación; se reutiliza solo para repetir la misma solicitud | `4f7c1d2e-8a9b-4c3d-9e5f-6a7b8c9d0e1f` | Interfaz: un UUID generado al pulsar «Confirmar» y conservado hasta recibir una respuesta definitiva |
| `X-Correlation-Id` | UUID | No | Identificador para correlacionar trazas | `4e5f6a7b-8c9d-4e0f-9a1b-2c3d4e5f6a7b` | Interfaz (opcional) |

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "version": 4
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `version` | integer ≥ 1 | Sí | Versión actual de la venta | `4` | `version` de la respuesta de la [API 10](#10-consultar-la-venta-con-sus-líneas-y-totales) (consulta la venta; errores en §10) o de la última escritura |

### Respuesta exitosa

`200 OK` (`SaleResponse` con `lines`; también se devuelve `200` con el mismo cuerpo al repetir con la misma clave):

```json
{
  "id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_customer_id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "customer_payment_condition_id": null,
  "payment_condition_code_snapshot": "CASH",
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "payment_method_code_snapshot": "CASH",
  "payment_method_name_snapshot": "Efectivo",
  "payment_terms_days_snapshot": 0,
  "due_date": "2026-10-20",
  "sale_sequence_id": "2c3d4e5f-6a7b-4c8d-9e0f-1a2b3c4d5e6f",
  "number": "V-000123",
  "sequence_value": 123,
  "status": "CONFIRMED",
  "operation_date": "2026-10-20",
  "customer_name_snapshot": "Ana Pérez",
  "customer_identification_snapshot": "CC 1012345678",
  "currency_code": "COP",
  "observations": "Venta mostrador",
  "subtotal": "1600.00",
  "discount_total": "0.00",
  "tax_total": "0.00",
  "total": "1600.00",
  "inventory_operation_id": "3d4e5f6a-7b8c-4d9e-8f0a-1b2c3d4e5f6a",
  "created_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancellation_reason": null,
  "pending_operation_id": null,
  "version": 6,
  "created_at": "2026-10-20T15:50:00Z",
  "updated_at": "2026-10-20T16:10:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "lines": [
    {
      "id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
      "sale_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
      "line_number": 1,
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
      "price_list_item_id": "6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c",
      "price_list_requested": false,
      "price_source": "PRICE_LIST_ITEM",
      "product_code_snapshot": "PRD-0001",
      "product_name_snapshot": "Acetaminofén 500 mg",
      "presentation_code_snapshot": "UN",
      "presentation_name_snapshot": "Unidad",
      "base_quantity_factor_snapshot": "1.00000000",
      "unit_code_snapshot": "UN",
      "quantity": "2.0000",
      "base_quantity": "2.0000",
      "unit_price": "800.0000",
      "discount_amount": "0.00",
      "tax_amount": "0.00",
      "subtotal": "1600.00",
      "total": "1600.00",
      "created_at": "2026-10-20T15:50:00Z",
      "updated_at": "2026-10-20T15:50:00Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ]
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `status` | string | `CONFIRMED` |
| `number`, `sequence_value`, `sale_sequence_id` | string, integer, UUID | Número del documento (prefijo, valor y relleno según la secuencia), valor numérico y secuencia usada; mostrar `number` en el comprobante |
| `operation_date`, `due_date` | date | Fecha de negocio fijada al confirmar (hoy en la zona horaria de la sucursal) |
| `inventory_operation_id` | UUID | Salida de inventario aplicada; es la que se revierte si se anula |
| `version` | integer | Nueva versión; la confirmación actualiza la venta en dos pasos, así que puede aumentar más de una unidad. Usar siempre la devuelta (p. ej. para anular) |
| `lines[]` | array | Líneas con los datos congelados; con `perm:sales:sales:read-profitability` incluyen costos FIFO y márgenes |
| `pending_operation_id` | null | Sin operación en curso |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `403` | `SALES.BRANCH_ACCESS_DENIED` | El usuario no tiene asignación `ACTIVE` a la sucursal de la venta, o la sucursal o la empresa están inactivas | Mostrar el mensaje y pedir la asignación al administrador ([API 12 de Administración empresarial](administracion-empresarial.md#12-asignar-un-usuario-a-una-sucursal)) |
| `403` | `SALES.OPERATIONAL_ACCESS_DENIED` | Operational Context no permite al usuario consultar su acceso operativo | Pedir `perm:operational-context:application_users:read` indicando el `trace_id` |
| `404` | `SALES.NOT_FOUND` | La empresa no existe, el usuario no es miembro `ACTIVE`, la sucursal es de otra empresa o la venta no existe en la empresa | Volver a leer el contexto operativo o la lista de ventas |
| `422` | `SALES.VALIDATION_ERROR` | Falta `Idempotency-Key` (`errors[].field` `Idempotency-Key`, `code` `IDEMPOTENCY_KEY_REQUIRED`) o es inválida o `X-Correlation-Id` no es UUID (`INVALID_FORMAT`); falta `version`; o una referencia ya no existe (`COMPANY_PRODUCT_NOT_FOUND`…); o una línea tiene descuento o impuesto (`DISCOUNT_NOT_ALLOWED`, `TAX_NOT_ALLOWED`) | Corregir; para la clave, generar una y enviarla |
| `422` | `SALES.SALE_WITHOUT_LINES` | La venta no tiene líneas | Agregar al menos una línea con la [API 7](#7-agregar-una-línea-a-la-venta) |
| `409` | `SALES.IDEMPOTENCY_KEY_CONFLICT` | La clave ya se usó para otra venta, otra acción u otro usuario | Generar una clave nueva |
| `409` | `SALES.OPERATION_IN_PROGRESS` | La venta tiene una confirmación o anulación en curso (extensión `operation_id`) | Esperar y volver a leer la venta con la [API 10](#10-consultar-la-venta-con-sus-líneas-y-totales) |
| `409` | `SALES.INVALID_STATUS` | La venta no está en `DRAFT`; en este error el campo `status` del cuerpo trae el estado actual de la venta (`CONFIRMED` o `CANCELLED`), no el número HTTP | Volver a leer la venta; una venta confirmada o anulada ya no se edita |
| `409` | `SALES.VERSION_CONFLICT` | La `version` enviada no es la actual | Volver a leer la venta con la [API 10](#10-consultar-la-venta-con-sus-líneas-y-totales) y repetir con la nueva `version` |
| `409` | `SALES.REFERENCES_NOT_ELIGIBLE` | Una referencia existe pero no se puede usar; `errors[].code`: `COMPANY_INACTIVE`, `BRANCH_INACTIVE`, `CUSTOMER_NOT_ELIGIBLE` (cliente inactivo), `CUSTOMER_IDENTIFICATION_MISSING`, `PAYMENT_METHOD_INACTIVE`, `PRODUCT_INACTIVE`, `PRODUCT_NOT_SELLABLE`, `PRODUCT_NOT_INVENTORY_CONTROLLED`, `PRESENTATION_INACTIVE`, `PRESENTATION_NOT_SELLABLE`, `PRICE_NOT_IN_LIST` (la lista elegida no tiene precio vigente para la presentación), `PRICE_NOT_AVAILABLE` (no hay lista por defecto vigente con precio), `PRICE_LIST_NOT_APPLICABLE` (lista inactiva o no vigente), `PRICE_CURRENCY_MISMATCH`, `APPLICATION_USER_INACTIVE` | Mostrar cada `errors[].message` junto al campo o la línea (`line_number`) y pedir otra referencia o corregir la configuración |
| `409` | `SALES.PRICES_CHANGED` | El precio vigente de una o más líneas cambió desde que se guardaron; `errors[]` trae por línea `stored` (lo guardado) y `current` (lo vigente) | Mostrar el precio nuevo, volver a guardar esas líneas con la [API 8](#8-modificar-una-línea-de-la-venta) y confirmar de nuevo con la nueva `version` y una clave nueva |
| `409` | `SALES.INSUFFICIENT_STOCK` | No hay existencias suficientes en la sucursal; `shortages[]` trae `line_numbers`, `company_product_id`, `available` y `requested` (unidad base) | Mostrar las líneas sin existencias y ajustar cantidades o eliminarlas |
| `409` | `SALES.SEQUENCE_NOT_CONFIGURED` | No hay secuencia de ventas activa para la sucursal ni para la empresa | Pedir al administrador que la cree con la [API 19 de Administración empresarial](administracion-empresarial.md#19-crear-una-secuencia-de-numeración) |
| `409` | `SALES.SEQUENCE_EXHAUSTED` | La secuencia llegó a su número máximo para el período (extensión `period_key`) | Pedir al administrador que ajuste la secuencia ([API 21 de Administración empresarial](administracion-empresarial.md#21-consultar-y-modificar-una-secuencia)) |
| `409` | `SALES.INVENTORY_REJECTED` | Inventory rechazó la salida por otra causa (extensión `details` con `inventory_code` e `inventory_status`); la operación quedó `FAILED` y la venta sigue en `DRAFT` | Mostrar el mensaje con el `trace_id`; reintentar con una clave nueva cuando se corrija la causa |
| `409` | `SALES.OPERATION_NOT_APPLIED` | La conciliación comprobó que Inventory nunca aplicó una operación pendiente y la cerró | Repetir la confirmación con una clave nueva |
| `503` | `SALES.DEPENDENCY_UNAVAILABLE` | Un servicio no respondió (extensión `dependency`). Si es `inventory` y trae `operation_id`, la operación quedó `PENDING` | Con `operation_id`: repetir con la **misma** clave o consultar la venta hasta que `pending_operation_id` sea `null`. Sin `operation_id`: reintentar más tarde; no se hizo nada |

Ejemplo `409` por precios cambiados:

```json
{
  "type": "https://sio/errors/sales/prices-changed",
  "title": "Precios cambiados",
  "status": 409,
  "detail": "El precio aplicable de una o más líneas cambió desde que se guardaron. Actualice esas líneas y confirme de nuevo.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a/confirmation",
  "code": "SALES.PRICES_CHANGED",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "lines[0].unit_price",
      "line_number": 1,
      "code": "PRICE_CHANGED",
      "message": "El precio aplicable de la línea cambió desde que se guardó.",
      "stored": {
        "unit_price": "800.0000",
        "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
        "price_list_item_id": "6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c"
      },
      "current": {
        "unit_price": "850.0000",
        "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
        "price_list_item_id": "9c0d1e2f-3a4b-4c5d-8e6f-7a8b9c0d1e2f"
      }
    }
  ]
}
```

Ejemplo `409` sin secuencia de numeración:

```json
{
  "type": "https://sio/errors/sales/sequence-not-configured",
  "title": "Secuencia no configurada",
  "status": 409,
  "detail": "No hay una secuencia de numeración activa para la sucursal ni para la empresa. Configure una secuencia de ventas antes de confirmar.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a/confirmation",
  "code": "SALES.SEQUENCE_NOT_CONFIGURED",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

Ejemplo `409` por existencias insuficientes:

```json
{
  "type": "https://sio/errors/sales/insufficient-stock",
  "title": "Existencias insuficientes",
  "status": 409,
  "detail": "No hay existencias suficientes en la sucursal para una o más líneas. La venta no se confirmó.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a/confirmation",
  "code": "SALES.INSUFFICIENT_STOCK",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "shortages": [
    {
      "line_numbers": [
        1
      ],
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "available": "1.0000",
      "requested": "2.0000"
    }
  ]
}
```

Ejemplo `503` con la operación pendiente porque Inventory no respondió:

```json
{
  "type": "https://sio/errors/sales/dependency-unavailable",
  "title": "Dependencia no disponible",
  "status": 503,
  "detail": "Un servicio requerido no está disponible temporalmente. Intente de nuevo más tarde.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a/confirmation",
  "code": "SALES.DEPENDENCY_UNAVAILABLE",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "operation_id": "0b1c2d3e-4f5a-4b6c-8d7e-9f0a1b2c3d4e",
  "dependency": "inventory"
}
```

## 13. Listar y buscar las ventas

**Método:** `GET`
**URL:** `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales`
**Permiso requerido:** `perm:sales:sales:read`

### ¿Qué hace esta API?

Lista las ventas de la empresa con paginación y filtros por estado, sucursal, cliente, rango de fechas de la venta y número de documento. Es la consulta del historial de ventas y la forma de encontrar una venta para verla (API 10) o anularla (API 14). Los elementos **no** incluyen `lines`: para ver las líneas se consulta la venta con la [API 10](#10-consultar-la-venta-con-sus-líneas-y-totales).

Orden fijo: `operation_date` descendente, luego `created_at` descendente e `id`. Solo exige membresía `ACTIVE` en la empresa (ve las ventas de todas sus sucursales) y funciona con la empresa inactiva.

Antes necesita: `company_id` con membresía `ACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales?status=CONFIRMED&branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7&operation_date_from=2026-10-01&operation_date_to=2026-10-31&page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa de la venta | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `status` | `DRAFT` \| `CONFIRMED` \| `CANCELLED` | No; sin filtro devuelve todos | Estado de la venta | Uno de: `DRAFT`, `CONFIRMED`, `CANCELLED`; p. ej. `CONFIRMED` | `?status=CONFIRMED` | Interfaz |
| `branch_id` | UUID | No | Solo ventas de esa sucursal | UUID de sucursal; p. ej. `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `&branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7` | `memberships[].branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |
| `operation_date_from` | date (`AAAA-MM-DD`) | No | Fecha de la venta desde (incluida) | Fecha ISO; p. ej. `2026-10-01` | `&operation_date_from=2026-10-01` | Interfaz |
| `operation_date_to` | date (`AAAA-MM-DD`) | No | Fecha de la venta hasta (incluida); no puede ser anterior a `operation_date_from` (`INVALID_DATE_RANGE`) | Fecha ISO; p. ej. `2026-10-31` | `&operation_date_to=2026-10-31` | Interfaz |
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `&page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |
| `company_customer_id` | UUID | No | Solo ventas de ese cliente | UUID de cliente; p. ej. `c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f` | `&company_customer_id=c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f` | `items[].id` de la [API 1](#1-buscar-el-cliente-de-la-venta) (busca los clientes; errores en §1) · guía [customer_id](../parametros/customer-id.md) |
| `number` | string (1–80) | No | Número de documento exacto | Número completo de una venta confirmada; p. ej. `V-000123` | `&number=V-000123` | `number` de la respuesta de la [API 12](#12-confirmar-la-venta) (confirma la venta; errores en §12) o el número impreso en el comprobante |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales?status=CONFIRMED&branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7&operation_date_from=2026-10-01&operation_date_to=2026-10-31&page=1&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`SalePage`; cada elemento es un `SaleResponse` **sin** `lines`):

```json
{
  "items": [
    {
      "id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "company_customer_id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
      "customer_payment_condition_id": null,
      "payment_condition_code_snapshot": "CASH",
      "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
      "payment_method_code_snapshot": "CASH",
      "payment_method_name_snapshot": "Efectivo",
      "payment_terms_days_snapshot": 0,
      "due_date": "2026-10-20",
      "sale_sequence_id": "2c3d4e5f-6a7b-4c8d-9e0f-1a2b3c4d5e6f",
      "number": "V-000123",
      "sequence_value": 123,
      "status": "CONFIRMED",
      "operation_date": "2026-10-20",
      "customer_name_snapshot": "Ana Pérez",
      "customer_identification_snapshot": "CC 1012345678",
      "currency_code": "COP",
      "observations": "Venta mostrador",
      "subtotal": "1600.00",
      "discount_total": "0.00",
      "tax_total": "0.00",
      "total": "1600.00",
      "inventory_operation_id": "3d4e5f6a-7b8c-4d9e-8f0a-1b2c3d4e5f6a",
      "created_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "cancelled_by_user_id": null,
      "cancelled_at": null,
      "cancellation_reason": null,
      "pending_operation_id": null,
      "version": 6,
      "created_at": "2026-10-20T15:50:00Z",
      "updated_at": "2026-10-20T16:10:00Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].id` | UUID | El `sale_id` para consultar (API 10) o anular (API 14) · guía [sale_id](../parametros/sale-id.md) |
| `items[].number`, `operation_date`, `status`, `customer_name_snapshot`, `total` | varios | Columnas habituales del historial; `number` es `null` en los borradores |
| `items[].version` | integer | Versión que se envía al anular desde la lista |
| `items[].pending_operation_id` | UUID \| null | Venta con una operación en curso |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación; `items` vacío cuando no hay coincidencias (no es error) |

Los demás campos de cada elemento son los descritos en la [API 6](#6-crear-la-venta-en-borrador). Con `perm:sales:sales:read-profitability` cada elemento incluye además `has_unknown_cost`.

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `403` | `SALES.OPERATIONAL_ACCESS_DENIED` | Operational Context no permite al usuario consultar su acceso operativo | Pedir `perm:operational-context:application_users:read` indicando el `trace_id` |
| `404` | `SALES.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` | Volver a leer el contexto operativo |
| `422` | `SALES.VALIDATION_ERROR` | Filtro desconocido (`UNKNOWN_FIELD`), `status` fuera de la enumeración, UUID o fecha mal formados, `number` vacío o > 80, paginación fuera de rango (`INVALID_FORMAT`), o `operation_date_to` anterior a `operation_date_from` (`INVALID_DATE_RANGE`) | Corregir los filtros |
| `503` | `SALES.DEPENDENCY_UNAVAILABLE` | Operational Context o la base de datos no respondieron (extensión `dependency`) | Reintentar más tarde |

Ejemplo `422` con el rango de fechas invertido:

```json
{
  "type": "https://sio/errors/sales/validation-error",
  "title": "Solicitud inválida",
  "status": 422,
  "detail": "La solicitud contiene datos inválidos.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales",
  "code": "SALES.VALIDATION_ERROR",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "operation_date_to",
      "message": "La fecha final no puede ser anterior a la inicial.",
      "code": "INVALID_DATE_RANGE"
    }
  ]
}
```

## 14. Anular una venta

**Método:** `POST`
**URL:** `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}/cancellation`
**Permiso requerido:** `perm:sales:sales:delete`

### ¿Qué hace esta API?

Anula una venta en `DRAFT` o `CONFIRMED` con un motivo obligatorio. Es una operación de **alto riesgo** e idempotente, con encabezado `Idempotency-Key` igual que la [API 12](#12-confirmar-la-venta). Una venta anulada (`CANCELLED`) no se puede reabrir ni volver a anular.

Efectos verificados en el código:

- Orden de comprobaciones: asignación `ACTIVE` a la sucursal; repetición con la misma clave; operación en curso (`409 OPERATION_IN_PROGRESS`); estado (`409 INVALID_STATUS` si ya está `CANCELLED`); `version` (`409 VERSION_CONFLICT`). No vuelve a validar el cliente ni los productos.
- **Borrador:** pasa a `CANCELLED` de inmediato; no toca Inventory.
- **Confirmada:** registra la operación `CANCEL` en `PENDING` y pide a Inventory el **reverso exacto** de la salida `inventory_operation_id` (con el motivo); con el reverso aplicado la venta pasa a `CANCELLED` **conservando su `number`**. Si Inventory rechaza el reverso, responde `409 SALES.INVENTORY_REJECTED`, la operación queda `FAILED` y la venta sigue `CONFIRMED`. Si Inventory no responde, `503` con `operation_id` y la operación queda `PENDING` (mismo tratamiento que en la API 12).
- Guarda `cancelled_by_user_id`, `cancelled_at` y `cancellation_reason` y registra el evento de auditoría `CANCEL_SALE` (entidad `Sale`).

Antes necesita: `sale_id` y `version` actual (API 10 o API 13) y el motivo que escribe el usuario.

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a/cancellation' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Idempotency-Key: 5a8d2e3f-9b0c-4d4e-8f6a-7b8c9d0e1f2a' \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 6,
    "reason": "Cliente desistió de la compra"
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa de la venta | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `sale_id` | UUID | Sí | Venta | `9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a` | `id` de la respuesta de la [API 6](#6-crear-la-venta-en-borrador) (crea la venta; errores en §6) o `items[].id` de la [API 13](#13-listar-y-buscar-las-ventas) (lista las ventas; errores en §13) · guía [sale_id](../parametros/sale-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `Authorization` | string | Sí | `Bearer` y el Access Token | `Bearer TU_ACCESS_TOKEN` | `access_token` de la [API 1 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#1-iniciar-sesión-usuario-y-contraseña) (inicia sesión; sus errores están en esa sección) |
| `Content-Type` | string | Sí | Tipo del cuerpo | `application/json` | Fijo |
| `Idempotency-Key` | string (1–150, ASCII imprimible sin espacios) | Sí | Clave única de este intento de anulación; distinta de la usada al confirmar | `5a8d2e3f-9b0c-4d4e-8f6a-7b8c9d0e1f2a` | Interfaz: un UUID generado al pulsar «Anular» y conservado hasta recibir una respuesta definitiva |
| `X-Correlation-Id` | UUID | No | Identificador para correlacionar trazas | `4e5f6a7b-8c9d-4e0f-9a1b-2c3d4e5f6a7b` | Interfaz (opcional) |

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "version": 6,
  "reason": "Cliente desistió de la compra"
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `version` | integer ≥ 1 | Sí | Versión actual de la venta | `6` | `version` de la respuesta de la [API 10](#10-consultar-la-venta-con-sus-líneas-y-totales) (consulta la venta; errores en §10), de la [API 12](#12-confirmar-la-venta) (confirma; errores en §12) o de la [API 13](#13-listar-y-buscar-las-ventas) (lista; errores en §13) |
| `reason` | string (1–1000) | Sí | Motivo de la anulación; no puede estar vacío ni ser solo espacios | `"Cliente desistió de la compra"` | Interfaz (texto que escribe el usuario) |

### Respuesta exitosa

`200 OK` (`SaleResponse` con `lines`; una venta confirmada conserva `number` e `inventory_operation_id`):

```json
{
  "id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_customer_id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "customer_payment_condition_id": null,
  "payment_condition_code_snapshot": "CASH",
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "payment_method_code_snapshot": "CASH",
  "payment_method_name_snapshot": "Efectivo",
  "payment_terms_days_snapshot": 0,
  "due_date": "2026-10-20",
  "sale_sequence_id": "2c3d4e5f-6a7b-4c8d-9e0f-1a2b3c4d5e6f",
  "number": "V-000123",
  "sequence_value": 123,
  "status": "CANCELLED",
  "operation_date": "2026-10-20",
  "customer_name_snapshot": "Ana Pérez",
  "customer_identification_snapshot": "CC 1012345678",
  "currency_code": "COP",
  "observations": "Venta mostrador",
  "subtotal": "1600.00",
  "discount_total": "0.00",
  "tax_total": "0.00",
  "total": "1600.00",
  "inventory_operation_id": "3d4e5f6a-7b8c-4d9e-8f0a-1b2c3d4e5f6a",
  "created_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "cancelled_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "cancelled_at": "2026-10-20T17:00:00Z",
  "cancellation_reason": "Cliente desistió de la compra",
  "pending_operation_id": null,
  "version": 8,
  "created_at": "2026-10-20T15:50:00Z",
  "updated_at": "2026-10-20T17:00:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "lines": [
    {
      "id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
      "sale_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
      "line_number": 1,
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
      "price_list_item_id": "6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c",
      "price_list_requested": false,
      "price_source": "PRICE_LIST_ITEM",
      "product_code_snapshot": "PRD-0001",
      "product_name_snapshot": "Acetaminofén 500 mg",
      "presentation_code_snapshot": "UN",
      "presentation_name_snapshot": "Unidad",
      "base_quantity_factor_snapshot": "1.00000000",
      "unit_code_snapshot": "UN",
      "quantity": "2.0000",
      "base_quantity": "2.0000",
      "unit_price": "800.0000",
      "discount_amount": "0.00",
      "tax_amount": "0.00",
      "subtotal": "1600.00",
      "total": "1600.00",
      "created_at": "2026-10-20T15:50:00Z",
      "updated_at": "2026-10-20T15:50:00Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ]
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `status` | string | `CANCELLED` |
| `cancelled_by_user_id`, `cancelled_at`, `cancellation_reason` | UUID, datetime, string | Quién, cuándo y por qué se anuló; mostrarlos en el detalle |
| `number` | string \| null | Se conserva si la venta estaba confirmada; `null` si se anuló un borrador |
| `version` | integer | Nueva versión |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `403` | `SALES.BRANCH_ACCESS_DENIED` | El usuario no tiene asignación `ACTIVE` a la sucursal de la venta, o la sucursal o la empresa están inactivas | Mostrar el mensaje y pedir la asignación al administrador ([API 12 de Administración empresarial](administracion-empresarial.md#12-asignar-un-usuario-a-una-sucursal)) |
| `403` | `SALES.OPERATIONAL_ACCESS_DENIED` | Operational Context no permite al usuario consultar su acceso operativo | Pedir `perm:operational-context:application_users:read` indicando el `trace_id` |
| `404` | `SALES.NOT_FOUND` | La empresa no existe, el usuario no es miembro `ACTIVE`, la sucursal es de otra empresa o la venta no existe en la empresa | Volver a leer el contexto operativo o la lista de ventas |
| `422` | `SALES.VALIDATION_ERROR` | Falta `Idempotency-Key` (`IDEMPOTENCY_KEY_REQUIRED`) o es inválida; `reason` vacío o solo espacios (`REASON_REQUIRED`), `reason` > 1000 (`INVALID_FORMAT`); falta `version` (`REQUIRED`); campo desconocido (`UNKNOWN_FIELD`) | Corregir y repetir |
| `409` | `SALES.IDEMPOTENCY_KEY_CONFLICT` | La clave ya se usó para otra venta, otra acción u otro usuario | Generar una clave nueva |
| `409` | `SALES.OPERATION_IN_PROGRESS` | La venta tiene una confirmación o anulación en curso (extensión `operation_id`) | Esperar y volver a leer la venta con la [API 10](#10-consultar-la-venta-con-sus-líneas-y-totales) |
| `409` | `SALES.INVALID_STATUS` | La venta ya está `CANCELLED`; el campo `status` del cuerpo trae `CANCELLED`, no el número HTTP | Volver a leer la venta; no hay nada que anular |
| `409` | `SALES.VERSION_CONFLICT` | La `version` enviada no es la actual | Volver a leer la venta con la [API 10](#10-consultar-la-venta-con-sus-líneas-y-totales) y repetir con la nueva `version` |
| `409` | `SALES.INVENTORY_REJECTED` | Inventory rechazó el reverso de la salida (extensión `details`); la venta sigue `CONFIRMED` | Mostrar el mensaje con el `trace_id` |
| `409` | `SALES.OPERATION_NOT_APPLIED` | La conciliación cerró una anulación pendiente que Inventory nunca aplicó | Repetir con una clave nueva |
| `503` | `SALES.DEPENDENCY_UNAVAILABLE` | Un servicio no respondió (extensión `dependency`); con `operation_id` la anulación quedó `PENDING` | Con `operation_id`: repetir con la misma clave o consultar la venta. Sin `operation_id`: reintentar más tarde |

Ejemplo `422` sin motivo:

```json
{
  "type": "https://sio/errors/sales/validation-error",
  "title": "Solicitud inválida",
  "status": 422,
  "detail": "La solicitud contiene datos inválidos.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a/cancellation",
  "code": "SALES.VALIDATION_ERROR",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "reason",
      "message": "El motivo de la anulación es obligatorio.",
      "code": "REASON_REQUIRED"
    }
  ]
}
```

## Dependencias con otros módulos

- **[Acceso y contexto operativo](acceso-y-contexto-operativo.md):** el Access Token y la empresa y sucursal de trabajo; el vendedor debe tener asignación `ACTIVE` a la sucursal.
- **[Administración empresarial](administracion-empresarial.md):** membresías y asignaciones a sucursales, las secuencias de numeración de ventas (API 18 a 21; sin secuencia no se confirma) y la trazabilidad de la venta (API 16 y 17).
- **[Gestión de clientes](gestion-de-clientes.md):** el cliente (`company_customer_id`) debe existir, estar `ACTIVE` y tener identificación; la identificación se copia en la venta.
- **[Productos y precios](productos-y-precios.md):** productos vendibles y controlados por inventario, presentaciones vendibles, listas de precios (una por defecto) y precios vigentes por presentación. Cambiar un precio entre guardar la línea y confirmar provoca `409 SALES.PRICES_CHANGED`.
- **[Inventario](inventario.md):** la confirmación registra una salida (origen `SALE`) que descuenta las existencias de la sucursal y fija el costo FIFO; la anulación de una venta confirmada registra su reverso. Ambos movimientos se ven en el kardex de Inventario.
- **[Reportes](reportes.md):** las ventas confirmadas alimentan los reportes de productos más vendidos y de ventas por sucursal.
