# 6.7 Compras

[← API principales](README.md) · [← Índice](../index.md)

Operaciones con las que el comprador de la empresa abastece una sucursal: elegir el proveedor, armar la compra en borrador con productos, cantidades y costos, revisar impuestos y totales, confirmarla (numera el documento) y registrar la recepción física completa (ingresa la mercancía al inventario y alimenta la actualización automática de precios). También se consultan y anulan compras.

Servicios implicados: [Purchase](../servicios/purchase.md) (propietario de la compra), [Commercial Relationship](../servicios/commercial-relationship.md) (proveedores, presentaciones, impuesto de compra y políticas de ganancia), [Payment Reference](../servicios/payment-reference.md) (método de pago) e [Inventory](../servicios/inventory.md) (entrada de existencias, invocada por Purchase; el frontend no la llama). Flujo completo: [Registrar una compra](../ejemplos/registrar-compra.md).

| # | API | Método y URL | Permiso | Referencia técnica |
|---|---|---|---|---|
| 1 | Buscar el proveedor | `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-suppliers` | `perm:commercial-relationship:company_suppliers:read` | [CR 19](../servicios/commercial-relationship.md#19-get-companiescompany_idcompany-suppliers) |
| 2 | Buscar las presentaciones comprables | `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-product-presentations` | `perm:commercial-relationship:company_product_presentations:read` | [CR 26](../servicios/commercial-relationship.md#26-get-companiescompany_idcompany-product-presentations) |
| 3 | Verificar la cobertura de políticas de ganancia | `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/pricing-policies/coverage` | `perm:commercial-relationship:pricing_policy_coverage:read` | [CR 60](../servicios/commercial-relationship.md#60-post-companiescompany_idpricing-policiescoverage) |
| 4 | Crear la compra en borrador | `POST https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases` | `perm:purchase:purchases:create` | [Purchase 3](../servicios/purchase.md#3-post-companiescompany_idpurchases) |
| 5 | Agregar una línea | `POST https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/details` | `perm:purchase:purchase_details:create` | [Purchase 7](../servicios/purchase.md#7-post-companiescompany_idpurchasespurchase_iddetails) |
| 6 | Modificar una línea | `PUT https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/details/{detail_id}` | `perm:purchase:purchase_details:update` | [Purchase 9](../servicios/purchase.md#9-put-companiescompany_idpurchasespurchase_iddetailsdetail_id) |
| 7 | Eliminar una línea | `DELETE https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/details/{detail_id}?version={version}` | `perm:purchase:purchase_details:delete` | [Purchase 10](../servicios/purchase.md#10-delete-companiescompany_idpurchasespurchase_iddetailsdetail_id) |
| 8 | Consultar la compra con impuestos y totales | `GET https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}` | `perm:purchase:purchases:read` | [Purchase 5](../servicios/purchase.md#5-get-companiescompany_idpurchasespurchase_id) |
| 9 | Confirmar la compra | `POST https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/confirmation` | `perm:purchase:purchases:update` | [Purchase 11](../servicios/purchase.md#11-post-companiescompany_idpurchasespurchase_idconfirmation) |
| 10 | Registrar la recepción física completa | `POST https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/receipt` | `perm:purchase:purchases:update` | [Purchase 12](../servicios/purchase.md#12-post-companiescompany_idpurchasespurchase_idreceipt) |
| 11 | Consultar el estado de las operaciones | `GET https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/operations` | `perm:purchase:purchase_operations:read` | [Purchase 14](../servicios/purchase.md#14-get-companiescompany_idpurchasespurchase_idoperations) |
| 12 | Listar compras | `GET https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases` | `perm:purchase:purchases:read` | [Purchase 4](../servicios/purchase.md#4-get-companiescompany_idpurchases) |
| 13 | Anular una compra | `POST https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/cancellation` | `perm:purchase:purchases:delete` | [Purchase 13](../servicios/purchase.md#13-post-companiescompany_idpurchasespurchase_idcancellation) |

Operaciones relacionadas que no se consideran principales (ver las fichas): editar la cabecera de un borrador (Purchase 6), listar solo las líneas (Purchase 8), consultar una operación por su `id` (Purchase 15), los hitos logísticos `ORDERED`, `SUPPLIER_DISPATCHED`, `ARRIVED`… (Purchase 16 y 17) y el reporte de compras del período (Purchase 24; ver [Reportes](reportes.md)). Las secuencias de numeración de compras (Purchase 18–23) se administran en las [API 18 a 21 de Administración empresarial](administracion-empresarial.md#numeración-de-documentos-comerciales); aquí no se repiten.

Orden habitual de una compra: [API 1](#1-buscar-el-proveedor) (proveedor `ACTIVE`) → [API 2](#2-buscar-las-presentaciones-comprables) (presentaciones comprables) → [API 3](#3-verificar-la-cobertura-de-políticas-de-ganancia) (comprobar que tienen política de ganancia) → [API 4](#4-crear-la-compra-en-borrador) (borrador) → [API 5](#5-agregar-una-línea), [6](#6-modificar-una-línea) y [7](#7-eliminar-una-línea) (ajustar líneas) → [API 8](#8-consultar-la-compra-con-impuestos-y-totales) (revisar totales) → [API 9](#9-confirmar-la-compra) (confirmar: numera, **no** mueve inventario) → [API 10](#10-registrar-la-recepción-física-completa) (recibir toda la mercancía: entra al inventario) → si una confirmación o recepción no termina, [API 11](#11-consultar-el-estado-de-las-operaciones).

### Antes de empezar: configuración obligatoria

| Requisito | Dónde se configura | Qué pasa si falta |
|---|---|---|
| Sucursal asignada al comprador (asignación `ACTIVE`) | [API 12 de Administración empresarial](administracion-empresarial.md#12-asignar-un-usuario-a-una-sucursal) | `403 PURCHASE.BRANCH_ACCESS_DENIED` en toda escritura |
| Secuencia de numeración de compras activa (sucursal o empresa) | [API 19 de Administración empresarial](administracion-empresarial.md#19-crear-una-secuencia-de-numeración) | `409 PURCHASE.SEQUENCE_NOT_CONFIGURED` al confirmar |
| Proveedor `ACTIVE` (no `INACTIVE` ni `BLOCKED`) | [Gestión de proveedores](gestion-de-proveedores.md) | `409 PURCHASE.REFERENCES_NOT_ELIGIBLE` con `errors[].code` `SUPPLIER_NOT_ELIGIBLE` |
| Producto `ACTIVE`, comprable y con control de inventario; presentación `ACTIVE` y comprable | [Productos y precios](productos-y-precios.md) | `409 PURCHASE.REFERENCES_NOT_ELIGIBLE` (`PRODUCT_NOT_PURCHASABLE`, `PRODUCT_NOT_INVENTORY_CONTROLLED`, `PRESENTATION_NOT_PURCHASABLE`…) |
| Tasa de impuesto de compra del producto configurada (`0` es válido) o tasa ajustada en la línea | [Productos y precios](productos-y-precios.md) (ficha [CR 11](../servicios/commercial-relationship.md#11-put-company-productscompany_product_idpurchase-tax)) | `409 PURCHASE.PURCHASE_TAX_NOT_CONFIGURED` al confirmar |
| Política de ganancia aplicable a cada presentación en una lista activa y vigente de la moneda de la compra (un porcentaje `0` es válido) | [Productos y precios](productos-y-precios.md) | `409 PURCHASE.PRICING_POLICY_NOT_CONFIGURED` al confirmar |
| Método de pago `ACTIVE` | Payment Reference (guía [payment_method_id](../parametros/payment-method-id.md)) | `422 VALIDATION_ERROR` (`PAYMENT_METHOD_NOT_FOUND`) o `409 REFERENCES_NOT_ELIGIBLE` (`PAYMENT_METHOD_INACTIVE`) |

Convenciones de todo el módulo:

- `TU_ACCESS_TOKEN` es el Access Token de [Acceso y contexto operativo](acceso-y-contexto-operativo.md); los UUID son ficticios.
- Todas las API de escritura con cuerpo JSON de Purchase y de Commercial Relationship **rechazan campos desconocidos** con `422 …VALIDATION_ERROR` (en Purchase con `errors[].code` `UNKNOWN_FIELD`). Purchase no acepta `tax_amount` ni totales en el cuerpo: los calcula el servidor.
- Errores comunes a todas las API de este módulo (no se repiten en cada tabla): `401` con `{"detail": "Se requiere un token de acceso Bearer"}` u otro `detail` cuando el token falta, venció o no es válido (renovar una vez y reintentar; si falla, volver al login); `403` con `code` `PURCHASE.FORBIDDEN` o `COMMERCIAL_RELATIONSHIP.FORBIDDEN` cuando el token no tiene el permiso indicado o, en Purchase, cuando es de una cuenta de servicio (mostrar que faltan permisos y el `trace_id`); `503` con `code` `…DEPENDENCY_UNAVAILABLE` y la extensión `dependency` cuando la base de datos u otro servicio no responde (reintentar más tarde). Los demás errores llegan en Problem Details (`application/problem+json`) con `code` `PURCHASE.…` o `COMMERCIAL_RELATIONSHIP.…` y `trace_id`; ver la [guía de errores](../guias/errores.md).
- **Errores de validación de Purchase.** `422 PURCHASE.VALIDATION_ERROR` trae `errors[]` con `field` (por ejemplo `lines[0].unit_cost`), `message`, `code` (`REQUIRED`, `INVALID_FORMAT`, `UNKNOWN_FIELD`, `QUANTITY_NOT_POSITIVE`, `TOO_MANY_DECIMALS`, `AMOUNT_OUT_OF_RANGE`, `UNIT_COST_NOT_POSITIVE`, `BASE_UNIT_COST_NOT_POSITIVE`, `DISCOUNT_EXCEEDS_SUBTOTAL`, `NET_COST_NOT_POSITIVE`, `TAX_PERCENTAGE_OUT_OF_RANGE`, `LINES_LIMIT_EXCEEDED`, referencias inexistentes como `SUPPLIER_NOT_FOUND`…) y, si aplica, `line_number`. Una referencia que existe pero no es apta responde `409 PURCHASE.REFERENCES_NOT_ELIGIBLE` con la misma forma de `errors[]`. Si hay errores de ambas clases, se informa primero el `422`.
- **Alcance.** Las lecturas de Purchase exigen membresía `ACTIVE` en la empresa; las escrituras exigen además asignación `ACTIVE` a la sucursal de la compra (si no, `403 PURCHASE.BRANCH_ACCESS_DENIED`). Fuera de la empresa la respuesta es `404 PURCHASE.NOT_FOUND`, igual que si no existiera. Commercial Relationship responde `404 COMMERCIAL_RELATIONSHIP.NOT_FOUND` sin membresía `ACTIVE`.
- **Control de versión.** Toda escritura sobre una compra envía su `version` actual (en el cuerpo o, al eliminar una línea, en la consulta); cada cambio la incrementa en 1. Si otra persona la cambió antes, la respuesta es `409 PURCHASE.VERSION_CONFLICT`: volver a leer la compra ([API 8](#8-consultar-la-compra-con-impuestos-y-totales)) y repetir con la nueva `version`.
- **Idempotencia.** Confirmar, recibir y anular exigen la cabecera `Idempotency-Key`: de 1 a 150 caracteres ASCII imprimibles sin espacios (por ejemplo un UUID nuevo por cada acción del usuario). Repetir la **misma** clave devuelve el resultado de la primera solicitud (o la reanuda si quedó pendiente) sin duplicar efectos; usarla para otra compra, otra acción u otro usuario responde `409 PURCHASE.IDEMPOTENCY_KEY_CONFLICT`. Sin cabecera: `422 PURCHASE.VALIDATION_ERROR` con `errors[].code` `IDEMPOTENCY_KEY_REQUIRED`; con formato inválido, `INVALID_FORMAT`. La cabecera opcional `X-Correlation-Id` (UUID) se guarda en la operación.
- **Solo contado.** En esta versión las compras son de contado: una condición de pago del proveedor cuyo tipo no es `CASH` se rechaza con `409 REFERENCES_NOT_ELIGIBLE` (`PAYMENT_CONDITION_NOT_AVAILABLE`).
- Las respuestas traen siempre `created_by`, `updated_by` (el `sub` de Keycloak de quien actuó), `created_at` y `updated_at`. Los decimales llegan como texto: cantidades y costos unitarios con 4 decimales, montos con 2.
- Toda escritura de Purchase queda registrada en [Audit](../servicios/audit.md) con las acciones `CREATE_PURCHASE`, `UPDATE_PURCHASE`, `ADD_PURCHASE_DETAIL`, `UPDATE_PURCHASE_DETAIL`, `DELETE_PURCHASE_DETAIL`, `OVERRIDE_PURCHASE_LINE_TAX`, `CONFIRM_PURCHASE`, `RECEIVE_PURCHASE` y `CANCEL_PURCHASE` (entidades `Purchase` y `PurchaseDetail`); un fallo con operación registrada genera el evento con `result` `FAILURE`. Se consultan con la [API 17 de Administración empresarial](administracion-empresarial.md#17-consultar-el-historial-de-una-venta-una-compra-o-un-producto) (historial de una compra; sus errores están en esa sección).

---

## 1. Buscar el proveedor

**Método:** `GET`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-suppliers`
**Permiso requerido:** `perm:commercial-relationship:company_suppliers:read`

### ¿Qué hace esta API?

Lista, con paginación y búsqueda por código interno o nombre, los proveedores de la empresa. En el flujo de compras se usa para elegir el proveedor del borrador: Purchase solo acepta proveedores `ACTIVE` (uno `INACTIVE` o `BLOCKED` se rechaza con `409 PURCHASE.REFERENCES_NOT_ELIGIBLE`). El alta y la administración de proveedores están en [Gestión de proveedores](gestion-de-proveedores.md).

Antes necesita: `company_id` con membresía `ACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-suppliers?search=farma&status=ACTIVE&page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa que compra | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `search` | string (≤ 100) | No | Búsqueda parcial, sin distinguir mayúsculas, en el código interno y el nombre del proveedor | Texto libre: parte del código o del nombre; p. ej. `PRV-0001` o `farma` | `?search=farma` | Interfaz (texto que escribe el usuario) |
| `status` | `ACTIVE` \| `INACTIVE` \| `BLOCKED` \| `ALL` | No; por defecto `ACTIVE` | Estado de los proveedores | Uno de: `ACTIVE` (por defecto), `INACTIVE`, `BLOCKED`, `ALL`; p. ej. `ACTIVE` | `&status=ACTIVE` | Interfaz; para compras usar `ACTIVE` |
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `&page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |
| `organization_identity_id` | UUID | No | Solo el proveedor de esa organización | UUID de una organización; p. ej. `0f1e2d3c-4b5a-4968-8776-655443322111` | `&organization_identity_id=0f1e2d3c-4b5a-4968-8776-655443322111` | `items[].id` de la [API 3 de Gestión de clientes](gestion-de-clientes.md#3-buscar-la-identidad-de-una-organización) (busca organizaciones por NIT o nombre; sus errores están en esa sección) · guía [organization_identity_id](../parametros/organization-identity-id.md) |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-suppliers?search=farma&status=ACTIVE&page=1&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[CompanySupplierResponse]`):

```json
{
  "items": [
    {
      "id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
      "internal_code": "PRV-0001",
      "display_name": "Distribuidora Farma S.A.S.",
      "preferred_contact_person_id": null,
      "block_reason": null
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
| `items[].id` | UUID | El [company_supplier_id](../parametros/supplier-id.md) que se envía en la [API 4](#4-crear-la-compra-en-borrador) |
| `items[].status` | `ACTIVE` \| `INACTIVE` \| `BLOCKED` | Solo `ACTIVE` sirve para comprar |
| `items[].internal_code`, `display_name` | string | Lo que se muestra en el selector de proveedor |
| `items[].block_reason` | string \| null | Motivo del bloqueo; solo con `BLOCKED` |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación; `items` vacío cuando no hay coincidencias (no es error) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` en ella | Volver a leer el contexto operativo |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `search` > 100, `status` fuera de la enumeración, UUID inválido, paginación fuera de rango | Corregir los filtros |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir `perm:operational-context:application_users:read` |

## 2. Buscar las presentaciones comprables

**Método:** `GET`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-product-presentations`
**Permiso requerido:** `perm:commercial-relationship:company_product_presentations:read`

### ¿Qué hace esta API?

Lista las presentaciones de producto adoptadas por la empresa (caja, blíster, unidad…) con sus banderas de compra y venta. En compras se filtra por `is_purchasable=true` para mostrar solo lo que se puede comprar; toda línea de compra exige un `company_product_id` y un `company_product_presentation_id` de ese mismo producto. La tasa de impuesto de compra del producto (`purchase_tax_percentage`) se ve en la ficha del producto (`GET https://sio-commercial-relationship-dev.onrender.com/api/v1/company-products/{company_product_id}`, ficha [CR 7](../servicios/commercial-relationship.md#7-get-company-productscompany_product_id)). La adopción de productos y presentaciones está en [Productos y precios](productos-y-precios.md).

Antes necesita: `company_id` con membresía `ACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-product-presentations?search=acet&is_purchasable=true&status=ACTIVE&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa que compra | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `search` | string (≤ 100) | No | Búsqueda parcial en código interno, SKU y código de referencia de la presentación | Texto libre; p. ej. `acet` o `ACET-500-CJ100` | `?search=acet` | Interfaz |
| `is_purchasable` | boolean | No | Solo presentaciones habilitadas para compras | Booleano: `true` o `false`; p. ej. `true` | `&is_purchasable=true` | Interfaz; en compras siempre `true` |
| `status` | `ACTIVE` \| `INACTIVE` \| `ALL` | No; por defecto `ACTIVE` | Estado de las presentaciones | Uno de: `ACTIVE` (por defecto), `INACTIVE`, `ALL`; p. ej. `ACTIVE` | `&status=ACTIVE` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `&page=1` | Interfaz |
| `company_product_id` | UUID | No | Solo las presentaciones de ese producto | UUID de un producto empresarial; p. ej. `e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `&company_product_id=e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `items[].id` de `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-products?is_purchasable=true` (lista los productos de la empresa; ficha [CR 3](../servicios/commercial-relationship.md#3-get-companiescompany_idcompany-products) con sus errores; módulo [Productos y precios](productos-y-precios.md)) · guía [company_product_id](../parametros/company-product-id.md) |
| `global_product_presentation_id` | UUID | No | Solo la adopción de esa presentación global | UUID; p. ej. `8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d` | `&global_product_presentation_id=8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d` | Guía [global_product_presentation_id](../parametros/global-product-presentation-id.md) |
| `is_sellable` | boolean | No | Solo presentaciones vendibles | Booleano: `true` o `false`; p. ej. `true` | `&is_sellable=true` | Interfaz (no se usa en compras) |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-product-presentations?search=acet&is_purchasable=true&status=ACTIVE&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[CompanyProductPresentationResponse]`):

```json
{
  "items": [
    {
      "id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
      "internal_code": "PRD-0001-CJ100",
      "sku": "ACET-500-CJ100",
      "reference_code": "REF-0001",
      "is_purchasable": true,
      "is_sellable": true,
      "is_default_purchase": true,
      "is_default_sale": true
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
| `items[].id` | UUID | El [company_product_presentation_id](../parametros/company-product-presentation-id.md) de la línea de compra (API 4 a 6) y de la [API 3](#3-verificar-la-cobertura-de-políticas-de-ganancia) |
| `items[].company_product_id` | UUID | El [company_product_id](../parametros/company-product-id.md) que acompaña a la presentación en la línea |
| `items[].is_purchasable` | boolean | Debe ser `true` para comprar |
| `items[].is_default_purchase` | boolean | Presentación sugerida para comprar ese producto |
| `items[].internal_code`, `sku`, `reference_code` | string \| null | Datos para mostrar y buscar |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` en ella | Volver a leer el contexto operativo |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `search` > 100, booleano o UUID inválidos, `status` fuera de la enumeración, paginación fuera de rango | Corregir los filtros |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir `perm:operational-context:application_users:read` |

## 3. Verificar la cobertura de políticas de ganancia

**Método:** `POST`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/pricing-policies/coverage`
**Permiso requerido:** `perm:commercial-relationship:pricing_policy_coverage:read`

### ¿Qué hace esta API?

Indica, para una lista de presentaciones, si cada una tiene una política de ganancia aplicable en alguna lista de precios activa y vigente de la moneda indicada, y en qué listas. Es una **consulta** (usa `POST` solo para enviar la lista): no crea nada y nunca devuelve porcentajes ni costos. Purchase hace esta misma comprobación al confirmar y responde `409 PRICING_POLICY_NOT_CONFIGURED` si alguna presentación no está cubierta (un porcentaje `0` cuenta como cubierta); consultarla antes evita que la confirmación falle. Además, al crear o editar líneas Purchase marca en `lines[].warnings` las presentaciones sin cobertura (`PRICING_POLICY_NOT_CONFIGURED`).

Antes necesita: la moneda de la compra (`currency_code` de la respuesta de la [API 4](#4-crear-la-compra-en-borrador); es la moneda funcional de la empresa) y los identificadores de presentación ([API 2](#2-buscar-las-presentaciones-comprables)).

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/pricing-policies/coverage' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "currency_code": "COP",
    "company_product_presentation_ids": [
      "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "b6c7d8e9-f0a1-4b2c-9d3e-4f5a6b7c8d94"
    ]
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa que compra | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "currency_code": "COP",
  "company_product_presentation_ids": [
    "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
    "b6c7d8e9-f0a1-4b2c-9d3e-4f5a6b7c8d94"
  ]
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `currency_code` | string (1–10) | Sí | Moneda ISO 4217 de la compra; se normaliza a mayúsculas y debe estar en la lista de monedas admitidas | `COP` | `currency_code` de la respuesta de la [API 4](#4-crear-la-compra-en-borrador) (crea la compra; errores en §4) o `default_currency` de la [API 3 de Administración empresarial](administracion-empresarial.md#3-consultar-una-empresa) (devuelve la ficha de la empresa; errores en esa sección) |
| `company_product_presentation_ids` | array de UUID (1–100 distintos) | Sí | Presentaciones a verificar; los duplicados se ignoran | `["a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83"]` | `items[].id` de la [API 2](#2-buscar-las-presentaciones-comprables) (lista las presentaciones comprables; errores en §2) o `lines[].company_product_presentation_id` de la [API 8](#8-consultar-la-compra-con-impuestos-y-totales) · guía [company_product_presentation_id](../parametros/company-product-presentation-id.md) |

### Respuesta exitosa

`200 OK` (`CoverageResponse`):

```json
{
  "items": [
    {
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "found": true,
      "covered": true,
      "price_list_ids": [
        "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b"
      ]
    },
    {
      "company_product_presentation_id": "b6c7d8e9-f0a1-4b2c-9d3e-4f5a6b7c8d94",
      "found": true,
      "covered": false,
      "price_list_ids": []
    }
  ]
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].company_product_presentation_id` | UUID | Presentación consultada |
| `items[].found` | boolean | `false` si no existe o es de otra empresa (nunca es error) |
| `items[].covered` | boolean | `true` si tiene política de ganancia aplicable; con `false` la confirmación fallará con `409 PRICING_POLICY_NOT_CONFIGURED` hasta que se configure en [Productos y precios](productos-y-precios.md) |
| `items[].price_list_ids` | array de UUID | Listas de precios que la cubren ([price_list_id](../parametros/price-list-id.md)) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` en ella | Volver a leer el contexto operativo |
| `422` | `COMMERCIAL_RELATIONSHIP.CURRENCY_NOT_SUPPORTED` | `currency_code` no está en la lista de monedas admitidas | Enviar la moneda de la compra |
| `422` | `COMMERCIAL_RELATIONSHIP.BATCH_LIMIT_EXCEEDED` | Más de 100 presentaciones distintas | Dividir la consulta en lotes de 100 |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | Lista vacía, UUID inválido, `currency_code` vacío o campo desconocido | Corregir la solicitud |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir `perm:operational-context:application_users:read` |

## 4. Crear la compra en borrador

**Método:** `POST`
**URL:** `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases`
**Permiso requerido:** `perm:purchase:purchases:create`; además `perm:purchase:purchase_details:create` si el cuerpo trae líneas y `perm:purchase:purchase_line_taxes:override` si alguna línea trae `tax_percentage`

### ¿Qué hace esta API?

Crea una compra en estado `DRAFT` para una sucursal y un proveedor, con su método de pago y, opcionalmente, sus primeras líneas (hasta 100). En borrador todo se puede cambiar; no hay número de documento ni movimiento de inventario. El servidor calcula por línea el subtotal, el impuesto (con la tasa de compra del producto o la tasa ajustada de la línea), el total, la cantidad en unidad base y el costo por unidad base que recibirá Inventory, y los totales de la cabecera.

Efectos verificados en el código: valida en este orden el acceso a la sucursal (`403 BRANCH_ACCESS_DENIED`), los importes de cada línea (`422`), que ninguna presentación se repita (`409 DUPLICATE_PRESENTATION_IN_PURCHASE`) y todas las referencias contra sus servicios (empresa, sucursal, proveedor y su identificación en Party Identity, condición de pago, método de pago, productos, presentaciones y productos de proveedor; primero los `422` y luego los `409`). La moneda de la compra es la moneda funcional de la empresa y queda fija. Crea la compra con `status` `DRAFT`, `version` `1`, `number` `null` y `receipt_status` `null`, y registra `CREATE_PURCHASE` (y `OVERRIDE_PURCHASE_LINE_TAX` por cada línea con tasa ajustada) en Audit. La respuesta `201` no incluye cabecera `Location`. Las líneas sin tasa de impuesto se aceptan en borrador con impuesto `0` y la advertencia `PURCHASE_TAX_NOT_CONFIGURED` en `lines[].warnings`; las presentaciones sin política de ganancia, con `PRICING_POLICY_NOT_CONFIGURED`. Ambas bloquearán la confirmación.

Antes necesita: la sucursal asignada al usuario, el proveedor `ACTIVE` ([API 1](#1-buscar-el-proveedor)), el método de pago y, si se envían líneas, los productos y presentaciones comprables ([API 2](#2-buscar-las-presentaciones-comprables)).

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
    "operation_date": "2026-10-19",
    "supplier_payment_condition_id": null,
    "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
    "promised_delivery_at": null,
    "supplier_document_number": "FV-8891",
    "observations": null,
    "lines": [
      {
        "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
        "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
        "supplier_product_id": null,
        "quantity": "10",
        "unit_cost": "50000",
        "discount_amount": "0"
      }
    ]
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa que compra | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "operation_date": "2026-10-19",
  "supplier_payment_condition_id": null,
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "promised_delivery_at": null,
  "supplier_document_number": "FV-8891",
  "observations": null,
  "lines": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "supplier_product_id": null,
      "quantity": "10",
      "unit_cost": "50000",
      "discount_amount": "0"
    }
  ]
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `branch_id` | UUID | Sí | Sucursal que recibirá la mercancía; `ACTIVE` y asignada al usuario | `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `memberships[].branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |
| `company_supplier_id` | UUID | Sí | Proveedor `ACTIVE` de la empresa con identificación tributaria en Party Identity | `d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60` | `items[].id` de la [API 1](#1-buscar-el-proveedor) (lista los proveedores; errores en §1) · guía [company_supplier_id](../parametros/supplier-id.md) |
| `operation_date` | date (`AAAA-MM-DD`) | Sí | Fecha de la compra; no puede ser futura en la zona horaria de la sucursal | `2026-10-19` | Formulario (por defecto la fecha de hoy) |
| `supplier_payment_condition_id` | UUID \| null | No; acepta `null` | Condición de pago del **mismo** proveedor, `ACTIVE`, vigente en la fecha, en la moneda de la empresa y de tipo `CASH`; con `null` la compra es de contado sin plazo | `null` | `items[].id` de `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/supplier-payment-conditions?company_supplier_id={company_supplier_id}` (lista las condiciones de pago del proveedor; permiso `perm:commercial-relationship:supplier_payment_conditions:read`; errores `404 NOT_FOUND` sin membresía y `422 VALIDATION_ERROR` por filtros inválidos; ficha [CR 40](../servicios/commercial-relationship.md#40-get-companiescompany_idsupplier-payment-conditions)) |
| `payment_method_id` | UUID | Sí | Método de pago `ACTIVE` | `b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05` | `items[].id` de `GET https://sio-payment-reference-dev.onrender.com/global-payment-methods?status=ACTIVE` (lista los métodos de pago globales; qué hace y sus errores en la guía [payment_method_id](../parametros/payment-method-id.md); ficha [Payment Reference 9](../servicios/payment-reference.md#9-get-global-payment-methods)) |
| `promised_delivery_at` | date-time con zona horaria \| null | No; acepta `null` | Fecha y hora de entrega prometida por el proveedor | `2026-10-21T10:00:00-05:00` | Formulario |
| `supplier_document_number` | string (1–100) \| null | No; acepta `null` | Número de la factura o remisión del proveedor | `FV-8891` | Formulario |
| `observations` | string (≤ 2000) \| null | No; acepta `null` | Observaciones | `null` | Formulario |
| `lines` | array (0–100) | No; por defecto `[]` | Líneas iniciales; una presentación aparece a lo sumo en una línea | ver filas siguientes | Formulario |
| `lines[].company_product_id` | UUID | Sí | Producto `ACTIVE`, comprable y con control de inventario | `e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `items[].company_product_id` de la [API 2](#2-buscar-las-presentaciones-comprables) (lista las presentaciones comprables; errores en §2) · guía [company_product_id](../parametros/company-product-id.md) |
| `lines[].company_product_presentation_id` | UUID | Sí | Presentación `ACTIVE` y comprable de ese mismo producto | `a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83` | `items[].id` de la [API 2](#2-buscar-las-presentaciones-comprables) (lista las presentaciones comprables; errores en §2) · guía [company_product_presentation_id](../parametros/company-product-presentation-id.md) |
| `lines[].supplier_product_id` | UUID \| null | No; acepta `null` | Producto de proveedor `ACTIVE` del mismo proveedor, producto y presentación (para tiempos de entrega y referencia) | `null` | `items[].id` de `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/supplier-products?company_supplier_id={company_supplier_id}` (lista los productos que suministra el proveedor; permiso `perm:commercial-relationship:supplier_products:read`; errores `404 NOT_FOUND` sin membresía y `422 VALIDATION_ERROR` por filtros inválidos; ficha [CR 34](../servicios/commercial-relationship.md#34-get-companiescompany_idsupplier-products)) |
| `lines[].quantity` | decimal (texto o número) | Sí | Cantidad de presentaciones; > 0, hasta 4 decimales; convertida a unidad base no puede necesitar más de 4 decimales | `10` | Formulario |
| `lines[].unit_cost` | decimal (texto o número) | Sí | Costo por presentación sin impuesto; > 0, hasta 4 decimales; el costo por unidad base resultante debe ser > 0 | `50000` | Formulario (factura del proveedor) |
| `lines[].discount_amount` | decimal (texto o número) | No; por defecto `0` | Descuento de la línea; ≥ 0, hasta 2 decimales, menor que el subtotal | `0` | Formulario |
| `lines[].tax_percentage` | decimal (texto o número) \| null | No; exige `perm:purchase:purchase_line_taxes:override` | Tasa de impuesto ajustada a la factura, de 0 a 100 con hasta 4 decimales; sin ella se usa la tasa del producto | `19` | Formulario (solo usuarios autorizados) |

### Respuesta exitosa

`201 Created` (`PurchaseResponse` con `lines`):

```json
{
  "id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "supplier_payment_condition_id": null,
  "payment_condition_code_snapshot": "CASH",
  "payment_terms_days_snapshot": 0,
  "due_date": "2026-10-19",
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "payment_method_code_snapshot": "TRANSFER",
  "payment_method_name_snapshot": "Transferencia bancaria",
  "purchase_sequence_id": null,
  "number": null,
  "sequence_value": null,
  "status": "DRAFT",
  "operation_date": "2026-10-19",
  "promised_delivery_at": null,
  "supplier_document_number": "FV-8891",
  "supplier_name_snapshot": "Distribuidora Farma S.A.S.",
  "supplier_identification_snapshot": "NIT 900123456",
  "currency_code": "COP",
  "observations": null,
  "subtotal": "500000.00",
  "discount_total": "0.00",
  "tax_total": "95000.00",
  "total": "595000.00",
  "inventory_operation_id": null,
  "receipt_status": null,
  "received_at": null,
  "received_by_user_id": null,
  "created_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancellation_reason": null,
  "pending_operation_id": null,
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "lines": [
    {
      "id": "b1a1e4be-5fb8-42b0-81c5-ca85b2fdcea6",
      "purchase_id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
      "line_number": 1,
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "supplier_product_id": null,
      "supplier_lead_time_snapshot_hours": null,
      "product_code_snapshot": "PRD-0001",
      "product_name_snapshot": "Acetaminofén 500 mg",
      "presentation_code_snapshot": "CJ100",
      "presentation_name_snapshot": "Caja x 100 tabletas",
      "base_quantity_factor_snapshot": "1.00000000",
      "unit_code_snapshot": "UN",
      "quantity": "10.0000",
      "unit_cost": "50000.0000",
      "discount_amount": "0.00",
      "tax_amount": "95000.00",
      "tax_percentage": "19.0000",
      "tax_percentage_source": "PRODUCT_DEFAULT",
      "warnings": [],
      "subtotal": "500000.00",
      "total": "595000.00",
      "base_quantity": "10.0000",
      "inventory_unit_cost": "50000.0000",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ]
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `id` | UUID | El [purchase_id](../parametros/purchase-id.md) que se usa en las API 5 a 13 |
| `status` | `DRAFT` \| `CONFIRMED` \| `CANCELLED` | `DRAFT` al crear |
| `receipt_status` | `PENDING` \| `RECEIVED` \| null | `null` en borrador; `PENDING` confirmada sin recibir; `RECEIVED` recibida (se conserva aunque luego se anule) |
| `number`, `sequence_value`, `purchase_sequence_id` | string, integer, UUID \| null | `null` hasta confirmar |
| `version` | integer | Valor que debe enviarse en la siguiente escritura |
| `currency_code` | string | Moneda de la compra (la funcional de la empresa) |
| `supplier_name_snapshot`, `supplier_identification_snapshot` | string | Nombre e identificación del proveedor congelados en la compra |
| `payment_condition_code_snapshot`, `payment_terms_days_snapshot`, `due_date` | string, integer, date | Contado (`CASH`, `0` días): `due_date` es la fecha de la compra |
| `payment_method_code_snapshot`, `payment_method_name_snapshot` | string | Método de pago congelado |
| `subtotal`, `discount_total`, `tax_total`, `total` | string (2 decimales) | Totales calculados por el servidor |
| `pending_operation_id` | UUID \| null | Operación de recepción o anulación en curso; consultar con la [API 11](#11-consultar-el-estado-de-las-operaciones) |
| `lines[].id` | UUID | El `detail_id` que se usa en las API 6 y 7 |
| `lines[].tax_percentage`, `tax_percentage_source` | string \| null, `PRODUCT_DEFAULT` \| `LINE_OVERRIDE` \| null | Tasa aplicada y su origen; `null` si el producto no tiene tasa configurada |
| `lines[].tax_amount`, `subtotal`, `total` | string | `subtotal` = cantidad × costo; `total` = subtotal − descuento + impuesto |
| `lines[].base_quantity`, `inventory_unit_cost` | string | Cantidad en unidad base y costo por unidad base sin impuesto que entrarán a Inventory al recibir |
| `lines[].warnings` | array de string | `PURCHASE_TAX_NOT_CONFIGURED` o `PRICING_POLICY_NOT_CONFIGURED`: mostrar aviso; bloquearán la confirmación |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `403` | `PURCHASE.BRANCH_ACCESS_DENIED` | El usuario no tiene asignación `ACTIVE` a la sucursal, o la sucursal o la empresa no están activas | Pedir la asignación al administrador ([API 12 de Administración empresarial](administracion-empresarial.md#12-asignar-un-usuario-a-una-sucursal)) |
| `403` | `PURCHASE.FORBIDDEN` | Faltan `purchase_details:create` (cuerpo con líneas) o `purchase_line_taxes:override` (línea con `tax_percentage`) | Quitar las líneas o la tasa, o pedir el permiso |
| `403` | `PURCHASE.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso para consultar su acceso operativo | Pedir acceso al administrador con el `trace_id` |
| `404` | `PURCHASE.NOT_FOUND` | La empresa no existe, el usuario no es miembro o la sucursal es de otra empresa | Volver a leer el contexto operativo |
| `409` | `PURCHASE.DUPLICATE_PRESENTATION_IN_PURCHASE` | La misma presentación aparece en dos líneas | Agrupar la cantidad en una sola línea |
| `409` | `PURCHASE.REFERENCES_NOT_ELIGIBLE` | Una referencia existe pero no es apta; `errors[].code`: `COMPANY_INACTIVE`, `BRANCH_INACTIVE`, `SUPPLIER_NOT_ELIGIBLE`, `ORGANIZATION_IDENTIFICATION_MISSING`, `PAYMENT_CONDITION_INACTIVE`, `PAYMENT_CONDITION_NOT_VALID_ON_DATE`, `PAYMENT_CONDITION_CURRENCY_MISMATCH`, `PAYMENT_CONDITION_TYPE_INACTIVE`, `PAYMENT_CONDITION_NOT_AVAILABLE`, `PAYMENT_METHOD_INACTIVE`, `PRODUCT_INACTIVE`, `PRODUCT_NOT_PURCHASABLE`, `PRODUCT_NOT_INVENTORY_CONTROLLED`, `PRESENTATION_INACTIVE`, `PRESENTATION_NOT_PURCHASABLE`, `SUPPLIER_PRODUCT_INACTIVE` | Mostrar cada error junto a su campo (`field`, `line_number`) y elegir otra referencia |
| `422` | `PURCHASE.VALIDATION_ERROR` | Formato o referencia inexistente; `errors[].code`: los de formato de las convenciones y `BRANCH_NOT_FOUND`, `OPERATION_DATE_IN_FUTURE`, `SUPPLIER_NOT_FOUND`, `ORGANIZATION_IDENTITY_NOT_FOUND`, `PAYMENT_CONDITION_NOT_FOUND`, `PAYMENT_CONDITION_OF_OTHER_SUPPLIER`, `PAYMENT_CONDITION_TYPE_NOT_FOUND`, `PAYMENT_METHOD_REQUIRED`, `PAYMENT_METHOD_NOT_FOUND`, `COMPANY_PRODUCT_NOT_FOUND`, `PRESENTATION_REQUIRED`, `PRESENTATION_NOT_FOUND`, `PRESENTATION_OF_OTHER_PRODUCT`, `SUPPLIER_PRODUCT_NOT_FOUND`, `SUPPLIER_PRODUCT_MISMATCH`, `BASE_QUANTITY_PRECISION` | Corregir el formulario según `errors[]` |
| `400` | `PURCHASE.MALFORMED_BODY` | El cuerpo no es JSON válido | Error de programación del cliente |
| `503` | `PURCHASE.DEPENDENCY_UNAVAILABLE` | Operational Context, Commercial Relationship, Party Identity, Payment Reference, Product Catalog o la base no responden (`dependency` indica cuál) | Reintentar más tarde; nada se guardó |

Ejemplo de `409` por proveedor no apto:

```json
{
  "type": "https://sio/errors/purchase/references-not-eligible",
  "title": "Referencias no aptas",
  "status": 409,
  "detail": "Una o más referencias existen, pero su estado o configuración actual impide usarlas en la compra.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases",
  "code": "PURCHASE.REFERENCES_NOT_ELIGIBLE",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "company_supplier_id",
      "message": "El proveedor no está activo (BLOCKED).",
      "code": "SUPPLIER_NOT_ELIGIBLE"
    }
  ]
}
```

Ejemplo de `422` por costo inválido en una línea:

```json
{
  "type": "https://sio/errors/purchase/validation-error",
  "title": "Solicitud inválida",
  "status": 422,
  "detail": "La solicitud contiene datos inválidos.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases",
  "code": "PURCHASE.VALIDATION_ERROR",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "lines[0].unit_cost",
      "message": "El costo unitario de adquisición debe ser mayor que cero.",
      "code": "UNIT_COST_NOT_POSITIVE"
    }
  ]
}
```

---

## 5. Agregar una línea

**Método:** `POST`
**URL:** `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/details`
**Permiso requerido:** `perm:purchase:purchase_details:create`; además `perm:purchase:purchase_line_taxes:override` si se envía `tax_percentage`

### ¿Qué hace esta API?

Agrega una línea a una compra en `DRAFT` y devuelve la compra **completa** con todas sus líneas y los totales recalculados.

Efectos verificados en el código: exige asignación a la sucursal de la compra, que no haya una operación en curso (`409 OPERATION_IN_PROGRESS`), que la compra esté en `DRAFT` (`409 INVALID_STATUS`) y que `version` coincida (`409 VERSION_CONFLICT`). Calcula los importes de la línea, valida producto, presentación y producto de proveedor (como en la [API 4](#4-crear-la-compra-en-borrador)), rechaza la presentación ya usada en otra línea (`409 DUPLICATE_PRESENTATION_IN_PURCHASE`) y el exceso de 100 líneas (`422`, `LINES_LIMIT_EXCEEDED`). Asigna el siguiente `line_number`, incrementa `version` y registra `ADD_PURCHASE_DETAIL` (y `OVERRIDE_PURCHASE_LINE_TAX` si hay tasa ajustada) en Audit.

Antes necesita: el `purchase_id` y la `version` vigente ([API 4](#4-crear-la-compra-en-borrador) u [API 8](#8-consultar-la-compra-con-impuestos-y-totales)) y la presentación comprable ([API 2](#2-buscar-las-presentaciones-comprables)).

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/details' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "company_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
    "company_product_presentation_id": "b6c7d8e9-f0a1-4b2c-9d3e-4f5a6b7c8d94",
    "supplier_product_id": null,
    "quantity": "5",
    "unit_cost": "48000",
    "discount_amount": "0",
    "version": 1
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa de la compra | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `purchase_id` | UUID | Sí | Compra en `DRAFT` | `4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e` | `id` de la [API 4](#4-crear-la-compra-en-borrador) (crea el borrador; errores en §4) o `items[].id` de la [API 12](#12-listar-compras) (lista las compras; errores en §12) · guía [purchase_id](../parametros/purchase-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "company_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "company_product_presentation_id": "b6c7d8e9-f0a1-4b2c-9d3e-4f5a6b7c8d94",
  "supplier_product_id": null,
  "quantity": "5",
  "unit_cost": "48000",
  "discount_amount": "0",
  "version": 1
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_product_id` | UUID | Sí | Producto `ACTIVE`, comprable y con control de inventario | `f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72` | `items[].company_product_id` de la [API 2](#2-buscar-las-presentaciones-comprables) (lista las presentaciones comprables; errores en §2) · guía [company_product_id](../parametros/company-product-id.md) |
| `company_product_presentation_id` | UUID | Sí | Presentación `ACTIVE` y comprable del mismo producto, no usada en otra línea de la compra | `b6c7d8e9-f0a1-4b2c-9d3e-4f5a6b7c8d94` | `items[].id` de la [API 2](#2-buscar-las-presentaciones-comprables) (lista las presentaciones comprables; errores en §2) · guía [company_product_presentation_id](../parametros/company-product-presentation-id.md) |
| `supplier_product_id` | UUID \| null | No; acepta `null` | Producto de proveedor `ACTIVE` del mismo proveedor, producto y presentación | `null` | `items[].id` de `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/supplier-products?company_supplier_id={company_supplier_id}` (lista los productos que suministra el proveedor; permiso `perm:commercial-relationship:supplier_products:read`; errores `404 NOT_FOUND` sin membresía y `422 VALIDATION_ERROR` por filtros inválidos; ficha [CR 34](../servicios/commercial-relationship.md#34-get-companiescompany_idsupplier-products)) |
| `quantity` | decimal (texto o número) | Sí | Cantidad de presentaciones; > 0, hasta 4 decimales | `5` | Formulario |
| `unit_cost` | decimal (texto o número) | Sí | Costo por presentación sin impuesto; > 0, hasta 4 decimales | `48000` | Formulario (factura del proveedor) |
| `discount_amount` | decimal (texto o número) | No; por defecto `0` | Descuento de la línea; ≥ 0, hasta 2 decimales, menor que el subtotal | `0` | Formulario |
| `tax_percentage` | decimal (texto o número) \| null | No; exige `perm:purchase:purchase_line_taxes:override` | Tasa ajustada de 0 a 100 con hasta 4 decimales; sin ella se usa la tasa de compra del producto | `19` | Formulario (solo usuarios autorizados) |
| `version` | integer ≥ 1 | Sí | Versión vigente de la compra | `1` | `version` de la [API 4](#4-crear-la-compra-en-borrador) o de la [API 8](#8-consultar-la-compra-con-impuestos-y-totales) (devuelven la compra; errores en sus secciones) |

### Respuesta exitosa

`201 Created` (la compra completa, ahora con `version` `2` y dos líneas):

```json
{
  "id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "supplier_payment_condition_id": null,
  "payment_condition_code_snapshot": "CASH",
  "payment_terms_days_snapshot": 0,
  "due_date": "2026-10-19",
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "payment_method_code_snapshot": "TRANSFER",
  "payment_method_name_snapshot": "Transferencia bancaria",
  "purchase_sequence_id": null,
  "number": null,
  "sequence_value": null,
  "status": "DRAFT",
  "operation_date": "2026-10-19",
  "promised_delivery_at": null,
  "supplier_document_number": "FV-8891",
  "supplier_name_snapshot": "Distribuidora Farma S.A.S.",
  "supplier_identification_snapshot": "NIT 900123456",
  "currency_code": "COP",
  "observations": null,
  "subtotal": "740000.00",
  "discount_total": "0.00",
  "tax_total": "140600.00",
  "total": "880600.00",
  "inventory_operation_id": null,
  "receipt_status": null,
  "received_at": null,
  "received_by_user_id": null,
  "created_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancellation_reason": null,
  "pending_operation_id": null,
  "version": 2,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:10:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "lines": [
    {
      "id": "b1a1e4be-5fb8-42b0-81c5-ca85b2fdcea6",
      "purchase_id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
      "line_number": 1,
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "supplier_product_id": null,
      "supplier_lead_time_snapshot_hours": null,
      "product_code_snapshot": "PRD-0001",
      "product_name_snapshot": "Acetaminofén 500 mg",
      "presentation_code_snapshot": "CJ100",
      "presentation_name_snapshot": "Caja x 100 tabletas",
      "base_quantity_factor_snapshot": "1.00000000",
      "unit_code_snapshot": "UN",
      "quantity": "10.0000",
      "unit_cost": "50000.0000",
      "discount_amount": "0.00",
      "tax_amount": "95000.00",
      "tax_percentage": "19.0000",
      "tax_percentage_source": "PRODUCT_DEFAULT",
      "warnings": [],
      "subtotal": "500000.00",
      "total": "595000.00",
      "base_quantity": "10.0000",
      "inventory_unit_cost": "50000.0000",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    },
    {
      "id": "c2b2f5cf-6ac9-43c1-92d6-db96c3aedfb7",
      "purchase_id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
      "line_number": 2,
      "company_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
      "company_product_presentation_id": "b6c7d8e9-f0a1-4b2c-9d3e-4f5a6b7c8d94",
      "supplier_product_id": null,
      "supplier_lead_time_snapshot_hours": null,
      "product_code_snapshot": "PRD-0002",
      "product_name_snapshot": "Ibuprofeno 400 mg",
      "presentation_code_snapshot": "CJ50",
      "presentation_name_snapshot": "Caja x 50 tabletas",
      "base_quantity_factor_snapshot": "1.00000000",
      "unit_code_snapshot": "UN",
      "quantity": "5.0000",
      "unit_cost": "48000.0000",
      "discount_amount": "0.00",
      "tax_amount": "45600.00",
      "tax_percentage": "19.0000",
      "tax_percentage_source": "PRODUCT_DEFAULT",
      "warnings": [],
      "subtotal": "240000.00",
      "total": "285600.00",
      "base_quantity": "5.0000",
      "inventory_unit_cost": "48000.0000",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:10:00Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ]
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `version` | integer | Nueva versión; usarla en la siguiente escritura |
| `lines[].id` | UUID | `detail_id` de la nueva línea (la de mayor `line_number`) |
| `subtotal`, `tax_total`, `total` | string | Totales de la cabecera recalculados |
| `lines[].warnings` | array de string | Avisos que bloquearán la confirmación (`PURCHASE_TAX_NOT_CONFIGURED`, `PRICING_POLICY_NOT_CONFIGURED`) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `403` | `PURCHASE.BRANCH_ACCESS_DENIED` | Sin asignación `ACTIVE` a la sucursal de la compra | Pedir la asignación al administrador |
| `403` | `PURCHASE.FORBIDDEN` | Se envió `tax_percentage` sin `purchase_line_taxes:override` | Quitar la tasa o pedir el permiso |
| `404` | `PURCHASE.NOT_FOUND` | La compra no existe en la empresa o el usuario no es miembro | Volver a la lista ([API 12](#12-listar-compras)) |
| `409` | `PURCHASE.INVALID_STATUS` | La compra ya no está en `DRAFT` (extensión `status`) | Recargar la compra; ya no admite cambios |
| `409` | `PURCHASE.VERSION_CONFLICT` | `version` no coincide | Volver a consultar ([API 8](#8-consultar-la-compra-con-impuestos-y-totales)) y reintentar |
| `409` | `PURCHASE.OPERATION_IN_PROGRESS` | Hay una operación en curso (extensión `operation_id`) | Esperar y consultar la [API 11](#11-consultar-el-estado-de-las-operaciones) |
| `409` | `PURCHASE.DUPLICATE_PRESENTATION_IN_PURCHASE` | La presentación ya está en otra línea | Modificar la línea existente ([API 6](#6-modificar-una-línea)) |
| `409` | `PURCHASE.REFERENCES_NOT_ELIGIBLE` | Producto, presentación o producto de proveedor no aptos (`errors[].code` como en la [API 4](#4-crear-la-compra-en-borrador)) | Elegir otra presentación |
| `422` | `PURCHASE.VALIDATION_ERROR` | Formato, importe, referencia inexistente o `LINES_LIMIT_EXCEEDED` | Corregir según `errors[]` |

Ejemplo de `409` por presentación repetida:

```json
{
  "type": "https://sio/errors/purchase/duplicate-presentation-in-purchase",
  "title": "Presentación repetida en la compra",
  "status": 409,
  "detail": "La misma presentación aparece en más de una línea: agrupe la cantidad en una sola línea.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/details",
  "code": "PURCHASE.DUPLICATE_PRESENTATION_IN_PURCHASE",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "company_product_presentation_id",
      "message": "La presentación ya está en la línea 1 de la compra.",
      "code": "DUPLICATE_PRESENTATION_IN_PURCHASE",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83"
    }
  ]
}
```

---

## 6. Modificar una línea

**Método:** `PUT`
**URL:** `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/details/{detail_id}`
**Permiso requerido:** `perm:purchase:purchase_details:update`; además `perm:purchase:purchase_line_taxes:override` si se envía `tax_percentage`

### ¿Qué hace esta API?

Reemplaza **todos** los datos de una línea de una compra en `DRAFT` (es un reemplazo completo, no parcial) y devuelve la compra completa con los totales recalculados. Conserva el `line_number`.

Efectos verificados en el código: mismas comprobaciones que la [API 5](#5-agregar-una-línea) (acceso a la sucursal, operación en curso, `DRAFT`, versión, importes, referencias y presentación no repetida en **otras** líneas). Si `detail_id` no pertenece a la compra responde `404`. Recalcula impuesto, totales, cantidad base y costo por unidad base con la tasa **actual** del producto (si no se envía `tax_percentage`), incrementa `version` y registra `UPDATE_PURCHASE_DETAIL` en Audit con los valores anteriores y nuevos. Volver a guardar una línea es la forma de resolver `PURCHASE_TAX_CHANGED` al confirmar.

Antes necesita: el `detail_id` (`lines[].id`) y la `version` vigente ([API 8](#8-consultar-la-compra-con-impuestos-y-totales)).

### ¿Cómo se realiza la solicitud?

```bash
curl -X PUT \
  'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/details/c2b2f5cf-6ac9-43c1-92d6-db96c3aedfb7' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "company_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
    "company_product_presentation_id": "b6c7d8e9-f0a1-4b2c-9d3e-4f5a6b7c8d94",
    "supplier_product_id": null,
    "quantity": "6",
    "unit_cost": "48000",
    "discount_amount": "0",
    "version": 2
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa de la compra | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `purchase_id` | UUID | Sí | Compra en `DRAFT` | `4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e` | `id` de la [API 4](#4-crear-la-compra-en-borrador) (crea el borrador; errores en §4) o `items[].id` de la [API 12](#12-listar-compras) (lista las compras; errores en §12) · guía [purchase_id](../parametros/purchase-id.md) |
| `detail_id` | UUID | Sí | Línea de esa compra | `c2b2f5cf-6ac9-43c1-92d6-db96c3aedfb7` | `lines[].id` de la [API 8](#8-consultar-la-compra-con-impuestos-y-totales) (consulta la compra con sus líneas; errores en §8) o de la respuesta de la [API 5](#5-agregar-una-línea) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "company_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "company_product_presentation_id": "b6c7d8e9-f0a1-4b2c-9d3e-4f5a6b7c8d94",
  "supplier_product_id": null,
  "quantity": "6",
  "unit_cost": "48000",
  "discount_amount": "0",
  "version": 2
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_product_id` | UUID | Sí | Producto de la línea (se puede cambiar) | `f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72` | `lines[].company_product_id` de la [API 8](#8-consultar-la-compra-con-impuestos-y-totales) o `items[].company_product_id` de la [API 2](#2-buscar-las-presentaciones-comprables) (errores en sus secciones) |
| `company_product_presentation_id` | UUID | Sí | Presentación del mismo producto, no usada en otra línea | `b6c7d8e9-f0a1-4b2c-9d3e-4f5a6b7c8d94` | `lines[].company_product_presentation_id` de la [API 8](#8-consultar-la-compra-con-impuestos-y-totales) o `items[].id` de la [API 2](#2-buscar-las-presentaciones-comprables) (errores en sus secciones) |
| `supplier_product_id` | UUID \| null | No; acepta `null` | Producto de proveedor; enviar el valor actual para conservarlo | `null` | `lines[].supplier_product_id` de la [API 8](#8-consultar-la-compra-con-impuestos-y-totales) (errores en §8) |
| `quantity` | decimal (texto o número) | Sí | Nueva cantidad; > 0, hasta 4 decimales | `6` | Formulario |
| `unit_cost` | decimal (texto o número) | Sí | Costo por presentación sin impuesto; > 0, hasta 4 decimales | `48000` | Formulario |
| `discount_amount` | decimal (texto o número) | No; por defecto `0` | Descuento; ≥ 0, hasta 2 decimales, menor que el subtotal | `0` | Formulario |
| `tax_percentage` | decimal (texto o número) \| null | No; exige `perm:purchase:purchase_line_taxes:override` | Tasa ajustada; si se omite, la línea vuelve a la tasa actual del producto | `19` | Formulario (solo usuarios autorizados) |
| `version` | integer ≥ 1 | Sí | Versión vigente de la compra | `2` | `version` de la respuesta de la [API 5](#5-agregar-una-línea) o de la [API 8](#8-consultar-la-compra-con-impuestos-y-totales) |

### Respuesta exitosa

`200 OK` (la compra completa con `version` `3`; la línea 2 tiene ahora cantidad `6.0000`):

```json
{
  "id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "supplier_payment_condition_id": null,
  "payment_condition_code_snapshot": "CASH",
  "payment_terms_days_snapshot": 0,
  "due_date": "2026-10-19",
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "payment_method_code_snapshot": "TRANSFER",
  "payment_method_name_snapshot": "Transferencia bancaria",
  "purchase_sequence_id": null,
  "number": null,
  "sequence_value": null,
  "status": "DRAFT",
  "operation_date": "2026-10-19",
  "promised_delivery_at": null,
  "supplier_document_number": "FV-8891",
  "supplier_name_snapshot": "Distribuidora Farma S.A.S.",
  "supplier_identification_snapshot": "NIT 900123456",
  "currency_code": "COP",
  "observations": null,
  "subtotal": "788000.00",
  "discount_total": "0.00",
  "tax_total": "149720.00",
  "total": "937720.00",
  "inventory_operation_id": null,
  "receipt_status": null,
  "received_at": null,
  "received_by_user_id": null,
  "created_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancellation_reason": null,
  "pending_operation_id": null,
  "version": 3,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:20:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "lines": [
    {
      "id": "b1a1e4be-5fb8-42b0-81c5-ca85b2fdcea6",
      "purchase_id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
      "line_number": 1,
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "supplier_product_id": null,
      "supplier_lead_time_snapshot_hours": null,
      "product_code_snapshot": "PRD-0001",
      "product_name_snapshot": "Acetaminofén 500 mg",
      "presentation_code_snapshot": "CJ100",
      "presentation_name_snapshot": "Caja x 100 tabletas",
      "base_quantity_factor_snapshot": "1.00000000",
      "unit_code_snapshot": "UN",
      "quantity": "10.0000",
      "unit_cost": "50000.0000",
      "discount_amount": "0.00",
      "tax_amount": "95000.00",
      "tax_percentage": "19.0000",
      "tax_percentage_source": "PRODUCT_DEFAULT",
      "warnings": [],
      "subtotal": "500000.00",
      "total": "595000.00",
      "base_quantity": "10.0000",
      "inventory_unit_cost": "50000.0000",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    },
    {
      "id": "c2b2f5cf-6ac9-43c1-92d6-db96c3aedfb7",
      "purchase_id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
      "line_number": 2,
      "company_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
      "company_product_presentation_id": "b6c7d8e9-f0a1-4b2c-9d3e-4f5a6b7c8d94",
      "supplier_product_id": null,
      "supplier_lead_time_snapshot_hours": null,
      "product_code_snapshot": "PRD-0002",
      "product_name_snapshot": "Ibuprofeno 400 mg",
      "presentation_code_snapshot": "CJ50",
      "presentation_name_snapshot": "Caja x 50 tabletas",
      "base_quantity_factor_snapshot": "1.00000000",
      "unit_code_snapshot": "UN",
      "quantity": "6.0000",
      "unit_cost": "48000.0000",
      "discount_amount": "0.00",
      "tax_amount": "54720.00",
      "tax_percentage": "19.0000",
      "tax_percentage_source": "PRODUCT_DEFAULT",
      "warnings": [],
      "subtotal": "288000.00",
      "total": "342720.00",
      "base_quantity": "6.0000",
      "inventory_unit_cost": "48000.0000",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:20:00Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ]
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `version` | integer | Nueva versión |
| `lines[].tax_percentage`, `tax_percentage_source` | string, string | `PRODUCT_DEFAULT` si se usó la tasa del producto, `LINE_OVERRIDE` si se envió `tax_percentage` |
| `subtotal`, `tax_total`, `total` | string | Totales recalculados |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `403` | `PURCHASE.BRANCH_ACCESS_DENIED` | Sin asignación `ACTIVE` a la sucursal de la compra | Pedir la asignación |
| `403` | `PURCHASE.FORBIDDEN` | Se envió `tax_percentage` sin `purchase_line_taxes:override` | Quitar la tasa o pedir el permiso |
| `404` | `PURCHASE.NOT_FOUND` | La compra o la línea no existen | Recargar la compra |
| `409` | `PURCHASE.INVALID_STATUS` | La compra no está en `DRAFT` | Recargar; ya no admite cambios |
| `409` | `PURCHASE.VERSION_CONFLICT` | `version` desactualizada | Volver a consultar y reintentar |
| `409` | `PURCHASE.OPERATION_IN_PROGRESS` | Operación en curso | Consultar la [API 11](#11-consultar-el-estado-de-las-operaciones) |
| `409` | `PURCHASE.DUPLICATE_PRESENTATION_IN_PURCHASE` | La nueva presentación ya está en otra línea | Elegir otra o unir las líneas |
| `409` | `PURCHASE.REFERENCES_NOT_ELIGIBLE` | Referencia no apta | Elegir otra referencia |
| `422` | `PURCHASE.VALIDATION_ERROR` | Formato, importe o referencia inexistente | Corregir según `errors[]` |

Ejemplo de `409` por versión desactualizada:

```json
{
  "type": "https://sio/errors/purchase/version-conflict",
  "title": "Conflicto de versión",
  "status": 409,
  "detail": "El recurso cambió desde la última consulta. Vuelva a consultarlo e intente de nuevo.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/details/c2b2f5cf-6ac9-43c1-92d6-db96c3aedfb7",
  "code": "PURCHASE.VERSION_CONFLICT",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

---

## 7. Eliminar una línea

**Método:** `DELETE`
**URL:** `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/details/{detail_id}?version={version}`
**Permiso requerido:** `perm:purchase:purchase_details:delete`

### ¿Qué hace esta API?

Elimina una línea de una compra en `DRAFT` y devuelve la compra completa (no un `204`) con los totales recalculados.

Efectos verificados en el código: exige asignación a la sucursal, ninguna operación en curso, estado `DRAFT` y `version` coincidente. Borra la línea físicamente (los `line_number` de las demás no se renumeran), incrementa `version` y registra `DELETE_PURCHASE_DETAIL` en Audit con los valores de la línea borrada. Se puede eliminar la última línea: la compra queda sin líneas y no se podrá confirmar (`422 PURCHASE_WITHOUT_LINES`) hasta agregar otra.

Antes necesita: el `detail_id` y la `version` vigente ([API 8](#8-consultar-la-compra-con-impuestos-y-totales)).

### ¿Cómo se realiza la solicitud?

```bash
curl -X DELETE \
  'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/details/c2b2f5cf-6ac9-43c1-92d6-db96c3aedfb7?version=3' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa de la compra | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `purchase_id` | UUID | Sí | Compra en `DRAFT` | `4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e` | `id` de la [API 4](#4-crear-la-compra-en-borrador) (crea el borrador; errores en §4) o `items[].id` de la [API 12](#12-listar-compras) (lista las compras; errores en §12) · guía [purchase_id](../parametros/purchase-id.md) |
| `detail_id` | UUID | Sí | Línea que se elimina | `c2b2f5cf-6ac9-43c1-92d6-db96c3aedfb7` | `lines[].id` de la [API 8](#8-consultar-la-compra-con-impuestos-y-totales) (consulta la compra con sus líneas; errores en §8) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `version` | integer | Sí | Versión vigente de la compra | Entero ≥ 1; ejemplo `3` | `?version=3` | `version` de la respuesta de la [API 6](#6-modificar-una-línea) o de la [API 8](#8-consultar-la-compra-con-impuestos-y-totales) (devuelven la compra; errores en sus secciones) |

Los parámetros de consulta se agregan al final de la URL: el primero con `?` y los siguientes con `&`. URL armada del ejemplo anterior: `https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/details/c2b2f5cf-6ac9-43c1-92d6-db96c3aedfb7?version=3`

**Encabezados:** `Authorization` (obligatorio).

**Cuerpo de la solicitud:** no lleva cuerpo.

### Cuerpo de la solicitud (Body)

No lleva cuerpo. La versión se envía en la consulta (`?version=`); sin ella responde `422 PURCHASE.VALIDATION_ERROR`.

### Respuesta exitosa

`200 OK` (la compra completa con `version` `4` y solo la línea 1):

```json
{
  "id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "supplier_payment_condition_id": null,
  "payment_condition_code_snapshot": "CASH",
  "payment_terms_days_snapshot": 0,
  "due_date": "2026-10-19",
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "payment_method_code_snapshot": "TRANSFER",
  "payment_method_name_snapshot": "Transferencia bancaria",
  "purchase_sequence_id": null,
  "number": null,
  "sequence_value": null,
  "status": "DRAFT",
  "operation_date": "2026-10-19",
  "promised_delivery_at": null,
  "supplier_document_number": "FV-8891",
  "supplier_name_snapshot": "Distribuidora Farma S.A.S.",
  "supplier_identification_snapshot": "NIT 900123456",
  "currency_code": "COP",
  "observations": null,
  "subtotal": "500000.00",
  "discount_total": "0.00",
  "tax_total": "95000.00",
  "total": "595000.00",
  "inventory_operation_id": null,
  "receipt_status": null,
  "received_at": null,
  "received_by_user_id": null,
  "created_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancellation_reason": null,
  "pending_operation_id": null,
  "version": 4,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:25:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "lines": [
    {
      "id": "b1a1e4be-5fb8-42b0-81c5-ca85b2fdcea6",
      "purchase_id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
      "line_number": 1,
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "supplier_product_id": null,
      "supplier_lead_time_snapshot_hours": null,
      "product_code_snapshot": "PRD-0001",
      "product_name_snapshot": "Acetaminofén 500 mg",
      "presentation_code_snapshot": "CJ100",
      "presentation_name_snapshot": "Caja x 100 tabletas",
      "base_quantity_factor_snapshot": "1.00000000",
      "unit_code_snapshot": "UN",
      "quantity": "10.0000",
      "unit_cost": "50000.0000",
      "discount_amount": "0.00",
      "tax_amount": "95000.00",
      "tax_percentage": "19.0000",
      "tax_percentage_source": "PRODUCT_DEFAULT",
      "warnings": [],
      "subtotal": "500000.00",
      "total": "595000.00",
      "base_quantity": "10.0000",
      "inventory_unit_cost": "50000.0000",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ]
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `version` | integer | Nueva versión |
| `lines` | array | Líneas restantes; puede quedar vacío |
| `subtotal`, `tax_total`, `total` | string | Totales recalculados |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `403` | `PURCHASE.BRANCH_ACCESS_DENIED` | Sin asignación `ACTIVE` a la sucursal de la compra | Pedir la asignación |
| `404` | `PURCHASE.NOT_FOUND` | La compra o la línea no existen (por ejemplo, ya se eliminó) | Recargar la compra |
| `409` | `PURCHASE.INVALID_STATUS` | La compra no está en `DRAFT` | Recargar; para deshacer una compra confirmada, anularla ([API 13](#13-anular-una-compra)) |
| `409` | `PURCHASE.VERSION_CONFLICT` | `version` desactualizada | Volver a consultar y reintentar |
| `409` | `PURCHASE.OPERATION_IN_PROGRESS` | Operación en curso | Consultar la [API 11](#11-consultar-el-estado-de-las-operaciones) |
| `422` | `PURCHASE.VALIDATION_ERROR` | Falta `version` o no es un entero ≥ 1 | Enviar la versión vigente |

Ejemplo de `409` por estado no permitido. Verificado en el código: la extensión `status` con el estado de la compra **sobrescribe** el campo `status` numérico del Problem Details, así que el frontend debe leer el código HTTP de la respuesta (409) y no el campo `status` del cuerpo:

```json
{
  "type": "https://sio/errors/purchase/invalid-status",
  "title": "Estado no permitido",
  "status": "CONFIRMED",
  "detail": "La acción no está permitida para una compra en estado CONFIRMED.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/details/c2b2f5cf-6ac9-43c1-92d6-db96c3aedfb7",
  "code": "PURCHASE.INVALID_STATUS",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

---

## 8. Consultar la compra con impuestos y totales

**Método:** `GET`
**URL:** `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}`
**Permiso requerido:** `perm:purchase:purchases:read`

### ¿Qué hace esta API?

Devuelve una compra con su cabecera, sus totales y **todas** sus líneas con impuesto, cantidad base y costo por unidad base. Es la consulta que se usa para revisar el borrador antes de confirmar, para obtener la `version` vigente antes de cualquier escritura y para ver el resultado de una confirmación, recepción o anulación.

Efectos verificados en el código: solo lectura. Exige membresía en la empresa (no asignación a la sucursal): una empresa inactiva también se puede consultar. Una compra de otra empresa responde `404`. En esta consulta `lines[].warnings` solo puede traer `PURCHASE_TAX_NOT_CONFIGURED`; el aviso `PRICING_POLICY_NOT_CONFIGURED` solo aparece en las respuestas de las API 4, 5 y 6 (para comprobar la cobertura usar la [API 3](#3-verificar-la-cobertura-de-políticas-de-ganancia)).

Antes necesita: el `purchase_id` ([API 4](#4-crear-la-compra-en-borrador) o [API 12](#12-listar-compras)).

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa de la compra | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `purchase_id` | UUID | Sí | Compra que se consulta | `4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e` | `id` de la [API 4](#4-crear-la-compra-en-borrador) (crea el borrador; errores en §4) o `items[].id` de la [API 12](#12-listar-compras) (lista las compras; errores en §12) · guía [purchase_id](../parametros/purchase-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio).

**Cuerpo de la solicitud:** no lleva cuerpo.

### Cuerpo de la solicitud (Body)

No lleva cuerpo.

### Respuesta exitosa

`200 OK` (el borrador tras eliminar la línea 2, `version` `4`):

```json
{
  "id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "supplier_payment_condition_id": null,
  "payment_condition_code_snapshot": "CASH",
  "payment_terms_days_snapshot": 0,
  "due_date": "2026-10-19",
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "payment_method_code_snapshot": "TRANSFER",
  "payment_method_name_snapshot": "Transferencia bancaria",
  "purchase_sequence_id": null,
  "number": null,
  "sequence_value": null,
  "status": "DRAFT",
  "operation_date": "2026-10-19",
  "promised_delivery_at": null,
  "supplier_document_number": "FV-8891",
  "supplier_name_snapshot": "Distribuidora Farma S.A.S.",
  "supplier_identification_snapshot": "NIT 900123456",
  "currency_code": "COP",
  "observations": null,
  "subtotal": "500000.00",
  "discount_total": "0.00",
  "tax_total": "95000.00",
  "total": "595000.00",
  "inventory_operation_id": null,
  "receipt_status": null,
  "received_at": null,
  "received_by_user_id": null,
  "created_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancellation_reason": null,
  "pending_operation_id": null,
  "version": 4,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:25:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "lines": [
    {
      "id": "b1a1e4be-5fb8-42b0-81c5-ca85b2fdcea6",
      "purchase_id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
      "line_number": 1,
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "supplier_product_id": null,
      "supplier_lead_time_snapshot_hours": null,
      "product_code_snapshot": "PRD-0001",
      "product_name_snapshot": "Acetaminofén 500 mg",
      "presentation_code_snapshot": "CJ100",
      "presentation_name_snapshot": "Caja x 100 tabletas",
      "base_quantity_factor_snapshot": "1.00000000",
      "unit_code_snapshot": "UN",
      "quantity": "10.0000",
      "unit_cost": "50000.0000",
      "discount_amount": "0.00",
      "tax_amount": "95000.00",
      "tax_percentage": "19.0000",
      "tax_percentage_source": "PRODUCT_DEFAULT",
      "warnings": [],
      "subtotal": "500000.00",
      "total": "595000.00",
      "base_quantity": "10.0000",
      "inventory_unit_cost": "50000.0000",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ]
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `status`, `receipt_status` | string | Estado de la compra y de la recepción (ver la [API 4](#4-crear-la-compra-en-borrador)) |
| `version` | integer | Valor para la siguiente escritura (API 5, 6, 7, 9, 10 y 13) |
| `subtotal` | string | Suma de los subtotales de las líneas (cantidad × costo) |
| `discount_total` | string | Suma de los descuentos |
| `tax_total` | string | Suma de los impuestos; cada línea: `(subtotal − descuento) × tasa / 100`, redondeado a 2 decimales (mitad hacia arriba) |
| `total` | string | `subtotal − discount_total + tax_total` |
| `lines[].tax_percentage`, `tax_percentage_source`, `tax_amount` | string | Tasa aplicada, su origen y el impuesto de la línea |
| `lines[].base_quantity_factor_snapshot`, `unit_code_snapshot` | string | Factor de la presentación a la unidad base y código de la unidad |
| `lines[].base_quantity` | string | Cantidad que entrará al inventario en unidad base |
| `lines[].inventory_unit_cost` | string | Costo neto sin impuesto por unidad base que se enviará a Inventory |
| `inventory_operation_id` | UUID \| null | Operación de entrada en Inventory, después de recibir |
| `pending_operation_id` | UUID \| null | Si no es `null`, hay una recepción o anulación sin terminar: consultar la [API 11](#11-consultar-el-estado-de-las-operaciones) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `PURCHASE.NOT_FOUND` | La compra no existe en la empresa o el usuario no es miembro | Volver a la lista ([API 12](#12-listar-compras)) |
| `403` | `PURCHASE.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso para consultar su acceso operativo | Pedir acceso con el `trace_id` |
| `422` | `PURCHASE.VALIDATION_ERROR` | Un identificador de la ruta no es un UUID | Error de programación del cliente |

Ejemplo de `404`:

```json
{
  "type": "https://sio/errors/purchase/not-found",
  "title": "Recurso no encontrado",
  "status": 404,
  "detail": "El recurso solicitado no existe o no está disponible para su usuario.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
  "code": "PURCHASE.NOT_FOUND",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

---

## 9. Confirmar la compra

**Método:** `POST`
**URL:** `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/confirmation`
**Permiso requerido:** `perm:purchase:purchases:update`

### ¿Qué hace esta API?

Confirma una compra en `DRAFT`: le asigna el número de documento de la secuencia de compras y la deja `CONFIRMED` con `receipt_status` `PENDING`. **No mueve inventario**: la mercancía entra con la [API 10](#10-registrar-la-recepción-física-completa). Está clasificada como `HIGH_RISK` en la ficha del servicio.

Efectos verificados en el código, en este orden: acceso a la sucursal (`403 BRANCH_ACCESS_DENIED`); validación de `Idempotency-Key` y repetición de una clave ya usada (devuelve el resultado anterior); operación en curso (`409 OPERATION_IN_PROGRESS`); estado `DRAFT` (`409 INVALID_STATUS`); `version` (`409 VERSION_CONFLICT`); al menos una línea (`422 PURCHASE_WITHOUT_LINES`); presentaciones no repetidas; revalidación de todas las referencias (cabecera y líneas, `422` o `409 REFERENCES_NOT_ELIGIBLE`); impuestos (primero `409 PURCHASE_TAX_NOT_CONFIGURED` si alguna línea no tiene tasa y luego `409 PURCHASE_TAX_CHANGED` si la tasa del producto cambió desde que se guardó la línea); cobertura de políticas de ganancia (`409 PRICING_POLICY_NOT_CONFIGURED`); usuario operativo activo; secuencia (`409 SEQUENCE_NOT_CONFIGURED` o `SEQUENCE_EXHAUSTED`). Si todo pasa, en **una sola transacción** asigna `number`, `sequence_value` y `purchase_sequence_id` (se usa la secuencia de la sucursal y, si no hay, la de la empresa), cambia el estado a `CONFIRMED`, incrementa `version`, registra la operación `CONFIRM` como `SUCCEEDED` y registra `CONFIRM_PURCHASE` en Audit. Un rechazo no consume número ni deja la clave usada: se puede corregir y repetir con la misma clave.

Antes necesita: la `version` vigente ([API 8](#8-consultar-la-compra-con-impuestos-y-totales)), una secuencia de compras activa ([API 19 de Administración empresarial](administracion-empresarial.md#19-crear-una-secuencia-de-numeración)), tasa de impuesto en cada línea y política de ganancia en cada presentación ([API 3](#3-verificar-la-cobertura-de-políticas-de-ganancia)).

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/confirmation' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: 0d9c8b7a-6f5e-4d3c-9b2a-1f0e9d8c7b6a' \
  -d '{
    "version": 4
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa de la compra | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `purchase_id` | UUID | Sí | Compra en `DRAFT` | `4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e` | `id` de la [API 4](#4-crear-la-compra-en-borrador) (crea el borrador; errores en §4) o `items[].id` de la [API 12](#12-listar-compras) (lista las compras; errores en §12) · guía [purchase_id](../parametros/purchase-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:**

- `Authorization` (obligatorio).
- `Content-Type: application/json` (obligatorio).
- `Idempotency-Key` (obligatorio): de 1 a 150 caracteres ASCII imprimibles sin espacios; generar uno nuevo (por ejemplo un UUID) cuando el usuario pulsa «Confirmar» y reutilizarlo solo para reintentar esa misma acción.
- `X-Correlation-Id` (opcional): UUID que se guarda en la operación.

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "version": 4
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `version` | integer ≥ 1 | Sí | Versión vigente de la compra | `4` | `version` de la [API 8](#8-consultar-la-compra-con-impuestos-y-totales) (consulta la compra; errores en §8) o de la última escritura |

### Respuesta exitosa

`200 OK` (la compra confirmada, `number` `C-000045`, `version` `5`):

```json
{
  "id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "supplier_payment_condition_id": null,
  "payment_condition_code_snapshot": "CASH",
  "payment_terms_days_snapshot": 0,
  "due_date": "2026-10-19",
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "payment_method_code_snapshot": "TRANSFER",
  "payment_method_name_snapshot": "Transferencia bancaria",
  "purchase_sequence_id": "4e5f6a7b-8c9d-4e0f-9a1b-2c3d4e5f6a7b",
  "number": "C-000045",
  "sequence_value": 45,
  "status": "CONFIRMED",
  "operation_date": "2026-10-19",
  "promised_delivery_at": null,
  "supplier_document_number": "FV-8891",
  "supplier_name_snapshot": "Distribuidora Farma S.A.S.",
  "supplier_identification_snapshot": "NIT 900123456",
  "currency_code": "COP",
  "observations": null,
  "subtotal": "500000.00",
  "discount_total": "0.00",
  "tax_total": "95000.00",
  "total": "595000.00",
  "inventory_operation_id": null,
  "receipt_status": "PENDING",
  "received_at": null,
  "received_by_user_id": null,
  "created_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancellation_reason": null,
  "pending_operation_id": null,
  "version": 5,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:30:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "lines": [
    {
      "id": "b1a1e4be-5fb8-42b0-81c5-ca85b2fdcea6",
      "purchase_id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
      "line_number": 1,
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "supplier_product_id": null,
      "supplier_lead_time_snapshot_hours": null,
      "product_code_snapshot": "PRD-0001",
      "product_name_snapshot": "Acetaminofén 500 mg",
      "presentation_code_snapshot": "CJ100",
      "presentation_name_snapshot": "Caja x 100 tabletas",
      "base_quantity_factor_snapshot": "1.00000000",
      "unit_code_snapshot": "UN",
      "quantity": "10.0000",
      "unit_cost": "50000.0000",
      "discount_amount": "0.00",
      "tax_amount": "95000.00",
      "tax_percentage": "19.0000",
      "tax_percentage_source": "PRODUCT_DEFAULT",
      "warnings": [],
      "subtotal": "500000.00",
      "total": "595000.00",
      "base_quantity": "10.0000",
      "inventory_unit_cost": "50000.0000",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ]
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `status` | string | `CONFIRMED` |
| `receipt_status` | string | `PENDING`: falta registrar la recepción ([API 10](#10-registrar-la-recepción-física-completa)) |
| `number`, `sequence_value`, `purchase_sequence_id` | string, integer, UUID | Número de documento asignado y su secuencia |
| `inventory_operation_id` | null | Todavía no hay entrada en Inventory |
| `version` | integer | Nueva versión; usarla para recibir o anular |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `403` | `PURCHASE.BRANCH_ACCESS_DENIED` | Sin asignación `ACTIVE` a la sucursal, o sucursal o empresa inactivas | Pedir la asignación al administrador |
| `404` | `PURCHASE.NOT_FOUND` | La compra no existe o el usuario no es miembro | Volver a la lista |
| `409` | `PURCHASE.INVALID_STATUS` | La compra no está en `DRAFT` | Recargar la compra |
| `409` | `PURCHASE.VERSION_CONFLICT` | `version` desactualizada | Consultar la [API 8](#8-consultar-la-compra-con-impuestos-y-totales) y reintentar con una clave nueva |
| `409` | `PURCHASE.OPERATION_IN_PROGRESS` | Hay una recepción o anulación en curso (`operation_id`) | Consultar la [API 11](#11-consultar-el-estado-de-las-operaciones) |
| `409` | `PURCHASE.IDEMPOTENCY_KEY_CONFLICT` | La clave ya se usó para otra compra, otra acción u otro usuario | Generar una clave nueva |
| `409` | `PURCHASE.DUPLICATE_PRESENTATION_IN_PURCHASE` | Dos líneas con la misma presentación | Unir las líneas |
| `409` | `PURCHASE.REFERENCES_NOT_ELIGIBLE` | Una referencia dejó de ser apta desde que se guardó el borrador | Corregir la cabecera o la línea indicada |
| `409` | `PURCHASE.PURCHASE_TAX_NOT_CONFIGURED` | Líneas sin tasa de impuesto (`errors[]` con `line_number` y `company_product_id`) | Configurar la tasa del producto en [Productos y precios](productos-y-precios.md) o ajustar la tasa de la línea ([API 6](#6-modificar-una-línea)) |
| `409` | `PURCHASE.PURCHASE_TAX_CHANGED` | La tasa del producto cambió (`errors[]` con `saved` y `current`) | Volver a guardar la línea ([API 6](#6-modificar-una-línea)) o ajustar su tasa |
| `409` | `PURCHASE.PRICING_POLICY_NOT_CONFIGURED` | Presentaciones sin política de ganancia (`errors[]` con `line_number` y `company_product_presentation_id`) | Configurar la política en [Productos y precios](productos-y-precios.md) |
| `409` | `PURCHASE.SEQUENCE_NOT_CONFIGURED` | No hay secuencia de compras activa | Crearla ([API 19 de Administración empresarial](administracion-empresarial.md#19-crear-una-secuencia-de-numeración)) |
| `409` | `PURCHASE.SEQUENCE_EXHAUSTED` | La secuencia llegó a su máximo (`period_key`) | Crear o ampliar la secuencia |
| `422` | `PURCHASE.PURCHASE_WITHOUT_LINES` | La compra no tiene líneas | Agregar al menos una ([API 5](#5-agregar-una-línea)) |
| `422` | `PURCHASE.VALIDATION_ERROR` | Falta `Idempotency-Key` (`IDEMPOTENCY_KEY_REQUIRED`), su formato es inválido, falta `version` o una referencia ya no existe | Corregir según `errors[]` |
| `503` | `PURCHASE.DEPENDENCY_UNAVAILABLE` | Un servicio de referencia no responde (`dependency`) | Reintentar con la **misma** clave |

Ejemplo de `409` por línea sin tasa de impuesto:

```json
{
  "type": "https://sio/errors/purchase/purchase-tax-not-configured",
  "title": "Impuesto de compra sin configurar",
  "status": 409,
  "detail": "Una o más líneas no tienen tasa de impuesto de compra: configure la tasa del producto (0 es válido) o ajuste la de la línea antes de confirmar.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/confirmation",
  "code": "PURCHASE.PURCHASE_TAX_NOT_CONFIGURED",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "lines[0].tax_percentage",
      "message": "El producto no tiene tasa de impuesto de compra configurada.",
      "code": "PURCHASE_TAX_NOT_CONFIGURED",
      "line_number": 1,
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61"
    }
  ]
}
```

Ejemplo de `409` por presentación sin política de ganancia:

```json
{
  "type": "https://sio/errors/purchase/pricing-policy-not-configured",
  "title": "Política de ganancia sin configurar",
  "status": 409,
  "detail": "Una o más presentaciones no tienen una política de ganancia aplicable en una lista activa y vigente de la moneda de la compra: configúrela en Commercial Relationship antes de confirmar.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/confirmation",
  "code": "PURCHASE.PRICING_POLICY_NOT_CONFIGURED",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "lines[0].company_product_presentation_id",
      "message": "La presentación no tiene una política de ganancia aplicable en una lista activa y vigente de la moneda.",
      "code": "PRICING_POLICY_NOT_CONFIGURED",
      "line_number": 1,
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83"
    }
  ]
}
```

Ejemplo de `409` por secuencia sin configurar:

```json
{
  "type": "https://sio/errors/purchase/sequence-not-configured",
  "title": "Secuencia no configurada",
  "status": 409,
  "detail": "No hay una secuencia de numeración activa para la sucursal ni para la empresa. Configure una secuencia de compras antes de confirmar.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/confirmation",
  "code": "PURCHASE.SEQUENCE_NOT_CONFIGURED",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

Ejemplo de `403` por falta de asignación a la sucursal:

```json
{
  "type": "https://sio/errors/purchase/branch-access-denied",
  "title": "Acceso a la sucursal denegado",
  "status": 403,
  "detail": "No tiene una asignación activa a la sucursal de la compra, o la sucursal o la empresa no están activas. Solicite la asignación al administrador de la empresa.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/confirmation",
  "code": "PURCHASE.BRANCH_ACCESS_DENIED",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

---

## 10. Registrar la recepción física completa

**Método:** `POST`
**URL:** `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/receipt`
**Permiso requerido:** `perm:purchase:purchases:update`

### ¿Qué hace esta API?

Registra que se recibió **toda** la mercancía de una compra `CONFIRMED` y la ingresa al inventario de la sucursal. No existen recepciones parciales: el usuario debe confirmarlo con `full_receipt_confirmed: true`. Una compra se recibe una sola vez. Está clasificada como `HIGH_RISK` en la ficha del servicio: pedir confirmación al usuario.

Efectos verificados en el código: valida el acceso a la sucursal y la `Idempotency-Key` (una clave repetida devuelve el resultado anterior), luego `full_receipt_confirmed`, que no haya otra operación en curso, que la compra esté `CONFIRMED` (`409 INVALID_STATUS`) y no recibida (`409 PURCHASE_ALREADY_RECEIVED`), la `version`, los costos de las líneas y el usuario operativo. **No** vuelve a validar proveedor ni productos. Registra una operación `RECEIVE` en `PENDING` (visible en `pending_operation_id`) y pide a Inventory una entrada con `origin_type` `PURCHASE` por cada línea, con `base_quantity` y `inventory_unit_cost` (costo sin impuesto). Al responder Inventory, en una sola transacción fija `inventory_operation_id`, `received_at` y `received_by_user_id`, deja `receipt_status` en `RECEIVED`, incrementa `version`, cierra la operación como `SUCCEEDED`, registra `RECEIVE_PURCHASE` en Audit y deja los costos recibidos para que Commercial Relationship recalcule los precios de venta de forma **asíncrona** (los precios pueden tardar unos segundos en cambiar). Si Inventory no responde, responde `503` con `operation_id` y la operación queda `PENDING`: repetir con la **misma** clave la reanuda sin duplicar la entrada. Si Inventory la rechaza, responde `409 INVENTORY_REJECTED` y la operación queda `FAILED`.

Antes necesita: la compra confirmada ([API 9](#9-confirmar-la-compra)) y su `version` vigente.

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/receipt' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: 1e0d9c8b-7a6f-4e5d-8c3b-2a1f0e9d8c7b' \
  -d '{
    "version": 5,
    "full_receipt_confirmed": true
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa de la compra | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `purchase_id` | UUID | Sí | Compra `CONFIRMED` sin recibir | `4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e` | `id` de la [API 9](#9-confirmar-la-compra) (confirma la compra; errores en §9) o `items[].id` de la [API 12](#12-listar-compras) con `?status=CONFIRMED` (lista las compras; errores en §12) · guía [purchase_id](../parametros/purchase-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:**

- `Authorization` (obligatorio).
- `Content-Type: application/json` (obligatorio).
- `Idempotency-Key` (obligatorio): clave nueva para esta recepción; reutilizarla solo para reintentarla.
- `X-Correlation-Id` (opcional): UUID que se guarda en la operación.

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "version": 5,
  "full_receipt_confirmed": true
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `version` | integer ≥ 1 | Sí | Versión vigente de la compra | `5` | `version` de la [API 9](#9-confirmar-la-compra) o de la [API 8](#8-consultar-la-compra-con-impuestos-y-totales) (devuelven la compra; errores en sus secciones) |
| `full_receipt_confirmed` | boolean | Sí | Debe ser `true`: el usuario declara que recibió toda la mercancía | `true` | Casilla del formulario («Recibí toda la mercancía») |

### Respuesta exitosa

`200 OK` (la compra recibida, `version` `6`):

```json
{
  "id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "supplier_payment_condition_id": null,
  "payment_condition_code_snapshot": "CASH",
  "payment_terms_days_snapshot": 0,
  "due_date": "2026-10-19",
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "payment_method_code_snapshot": "TRANSFER",
  "payment_method_name_snapshot": "Transferencia bancaria",
  "purchase_sequence_id": "4e5f6a7b-8c9d-4e0f-9a1b-2c3d4e5f6a7b",
  "number": "C-000045",
  "sequence_value": 45,
  "status": "CONFIRMED",
  "operation_date": "2026-10-19",
  "promised_delivery_at": null,
  "supplier_document_number": "FV-8891",
  "supplier_name_snapshot": "Distribuidora Farma S.A.S.",
  "supplier_identification_snapshot": "NIT 900123456",
  "currency_code": "COP",
  "observations": null,
  "subtotal": "500000.00",
  "discount_total": "0.00",
  "tax_total": "95000.00",
  "total": "595000.00",
  "inventory_operation_id": "5f6a7b8c-9d0e-4f1a-8b2c-3d4e5f6a7b8c",
  "receipt_status": "RECEIVED",
  "received_at": "2026-10-19T16:30:00Z",
  "received_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "created_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancellation_reason": null,
  "pending_operation_id": null,
  "version": 6,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T16:30:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "lines": [
    {
      "id": "b1a1e4be-5fb8-42b0-81c5-ca85b2fdcea6",
      "purchase_id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
      "line_number": 1,
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "supplier_product_id": null,
      "supplier_lead_time_snapshot_hours": null,
      "product_code_snapshot": "PRD-0001",
      "product_name_snapshot": "Acetaminofén 500 mg",
      "presentation_code_snapshot": "CJ100",
      "presentation_name_snapshot": "Caja x 100 tabletas",
      "base_quantity_factor_snapshot": "1.00000000",
      "unit_code_snapshot": "UN",
      "quantity": "10.0000",
      "unit_cost": "50000.0000",
      "discount_amount": "0.00",
      "tax_amount": "95000.00",
      "tax_percentage": "19.0000",
      "tax_percentage_source": "PRODUCT_DEFAULT",
      "warnings": [],
      "subtotal": "500000.00",
      "total": "595000.00",
      "base_quantity": "10.0000",
      "inventory_unit_cost": "50000.0000",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ]
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `receipt_status` | string | `RECEIVED` |
| `received_at`, `received_by_user_id` | date-time, UUID | Cuándo y quién recibió |
| `inventory_operation_id` | UUID | Operación de entrada en Inventory; ver [Inventario](inventario.md) |
| `pending_operation_id` | null | La operación terminó |
| `version` | integer | Nueva versión; usarla para anular |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `403` | `PURCHASE.BRANCH_ACCESS_DENIED` | Sin asignación `ACTIVE` a la sucursal | Pedir la asignación |
| `404` | `PURCHASE.NOT_FOUND` | La compra no existe o el usuario no es miembro | Volver a la lista |
| `409` | `PURCHASE.INVALID_STATUS` | La compra no está `CONFIRMED` (borrador o anulada) | Confirmarla primero ([API 9](#9-confirmar-la-compra)) o recargar |
| `409` | `PURCHASE.PURCHASE_ALREADY_RECEIVED` | La compra ya fue recibida | Recargar; no se repite |
| `409` | `PURCHASE.VERSION_CONFLICT` | `version` desactualizada | Consultar y reintentar con una clave nueva |
| `409` | `PURCHASE.OPERATION_IN_PROGRESS` | Hay una operación en curso (`operation_id`) | Repetir con la misma clave o consultar la [API 11](#11-consultar-el-estado-de-las-operaciones) |
| `409` | `PURCHASE.IDEMPOTENCY_KEY_CONFLICT` | La clave ya se usó en otra solicitud | Generar una clave nueva |
| `409` | `PURCHASE.INVENTORY_REJECTED` | Inventory rechazó la entrada (`details.inventory_code`, `details.inventory_status`); la operación queda `FAILED` | Mostrar el motivo y reintentar con una clave nueva tras corregir |
| `409` | `PURCHASE.OPERATION_NOT_APPLIED` | La conciliación comprobó que Inventory nunca aplicó la operación | Repetir con una clave nueva |
| `422` | `PURCHASE.VALIDATION_ERROR` | `full_receipt_confirmed` es `false` (`FULL_RECEIPT_NOT_CONFIRMED`), falta la clave o tiene formato inválido, o un costo de línea no es válido | Corregir según `errors[]` |
| `503` | `PURCHASE.DEPENDENCY_UNAVAILABLE` | Inventory no respondió (`dependency` `inventory`, `operation_id`); la operación queda `PENDING` | Reintentar con la **misma** clave o consultar la [API 11](#11-consultar-el-estado-de-las-operaciones) |

Ejemplo de `422` sin confirmación de recepción completa:

```json
{
  "type": "https://sio/errors/purchase/validation-error",
  "title": "Solicitud inválida",
  "status": 422,
  "detail": "La solicitud contiene datos inválidos.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/receipt",
  "code": "PURCHASE.VALIDATION_ERROR",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "full_receipt_confirmed",
      "message": "Confirme que recibió toda la mercancía de la compra: no existen recepciones parciales.",
      "code": "FULL_RECEIPT_NOT_CONFIRMED"
    }
  ]
}
```

Ejemplo de `503` con la operación pendiente:

```json
{
  "type": "https://sio/errors/purchase/dependency-unavailable",
  "title": "Dependencia no disponible",
  "status": 503,
  "detail": "Un servicio requerido no está disponible temporalmente. Intente de nuevo más tarde.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/receipt",
  "code": "PURCHASE.DEPENDENCY_UNAVAILABLE",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "operation_id": "6a7b8c9d-0e1f-4a2b-9c3d-4e5f6a7b8c9d",
  "dependency": "inventory"
}
```

---

## 11. Consultar el estado de las operaciones

**Método:** `GET`
**URL:** `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/operations`
**Permiso requerido:** `perm:purchase:purchase_operations:read`

### ¿Qué hace esta API?

Devuelve las operaciones de confirmación (`CONFIRM`), recepción (`RECEIVE`) y anulación (`CANCEL`) de una compra, ordenadas por `started_at`. Sirve para saber en qué terminó una acción cuando la respuesta no llegó, fue `503` o la compra muestra `pending_operation_id`.

Efectos verificados en el código: solo lectura; exige membresía en la empresa. Cada operación pasa por `PENDING` → `SUCCEEDED` o `FAILED`. Una operación `FAILED` guarda en `error_code` y `error_details` el error original, que se repite si se reintenta con la misma `Idempotency-Key`; para volver a intentar la acción hay que usar una clave nueva. Una operación `PENDING` se reanuda repitiendo la solicitud original con la **misma** clave. No incluye la clave de idempotencia. Para consultar una sola operación por su `id` existe `GET https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchase-operations/{operation_id}` (ficha [Purchase 15](../servicios/purchase.md#15-get-companiescompany_idpurchase-operationsoperation_id)).

Antes necesita: el `purchase_id`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/operations' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa de la compra | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `purchase_id` | UUID | Sí | Compra cuyas operaciones se consultan | `4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e` | `id` de la [API 4](#4-crear-la-compra-en-borrador) (crea el borrador; errores en §4) o `items[].id` de la [API 12](#12-listar-compras) (lista las compras; errores en §12) · guía [purchase_id](../parametros/purchase-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio).

**Cuerpo de la solicitud:** no lleva cuerpo.

### Cuerpo de la solicitud (Body)

No lleva cuerpo.

### Respuesta exitosa

`200 OK` (arreglo de operaciones, sin paginación):

```json
[
  {
    "id": "7b8c9d0e-1f2a-4b3c-8d4e-5f6a7b8c9d0e",
    "purchase_id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
    "operation_type": "CONFIRM",
    "status": "SUCCEEDED",
    "correlation_id": "8c9d0e1f-2a3b-4c4d-9e5f-6a7b8c9d0e1f",
    "error_code": null,
    "error_details": null,
    "inventory_operation_id": null,
    "started_at": "2026-10-19T15:30:00Z",
    "updated_at": "2026-10-19T15:30:00Z",
    "completed_at": "2026-10-19T15:30:00Z"
  },
  {
    "id": "6a7b8c9d-0e1f-4a2b-9c3d-4e5f6a7b8c9d",
    "purchase_id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
    "operation_type": "RECEIVE",
    "status": "SUCCEEDED",
    "correlation_id": "9d0e1f2a-3b4c-4d5e-8f6a-7b8c9d0e1f2a",
    "error_code": null,
    "error_details": null,
    "inventory_operation_id": "5f6a7b8c-9d0e-4f1a-8b2c-3d4e5f6a7b8c",
    "started_at": "2026-10-19T16:29:58Z",
    "updated_at": "2026-10-19T16:30:00Z",
    "completed_at": "2026-10-19T16:30:00Z"
  }
]
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `operation_type` | `CONFIRM` \| `RECEIVE` \| `CANCEL` | Acción registrada |
| `status` | `PENDING` \| `SUCCEEDED` \| `FAILED` | `PENDING`: repetir la solicitud original con la misma clave; `FAILED`: ver `error_code` y reintentar con una clave nueva |
| `correlation_id` | UUID | El `X-Correlation-Id` enviado o uno generado por el servidor |
| `error_code`, `error_details` | string \| null, object \| null | Error de una operación `FAILED` |
| `inventory_operation_id` | UUID \| null | Entrada (en `RECEIVE`) o reverso (en `CANCEL`) aplicados en Inventory |
| `completed_at` | date-time \| null | `null` mientras está `PENDING` |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `PURCHASE.NOT_FOUND` | La compra no existe en la empresa o el usuario no es miembro | Volver a la lista |
| `403` | `PURCHASE.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso para consultar su acceso operativo | Pedir acceso con el `trace_id` |
| `422` | `PURCHASE.VALIDATION_ERROR` | Un identificador de la ruta no es un UUID | Error de programación del cliente |

Ejemplo de `404`:

```json
{
  "type": "https://sio/errors/purchase/not-found",
  "title": "Recurso no encontrado",
  "status": 404,
  "detail": "El recurso solicitado no existe o no está disponible para su usuario.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/operations",
  "code": "PURCHASE.NOT_FOUND",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

---

## 12. Listar compras

**Método:** `GET`
**URL:** `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases`
**Permiso requerido:** `perm:purchase:purchases:read`

### ¿Qué hace esta API?

Lista las compras de la empresa con filtros y paginación. Cada ítem trae la cabecera y los totales, pero **no** las líneas (`"lines": null`); para verlas usar la [API 8](#8-consultar-la-compra-con-impuestos-y-totales). Para la bandeja «pendientes de recibir» filtrar `status=CONFIRMED` y mostrar las que tengan `receipt_status` `PENDING`.

Efectos verificados en el código: solo lectura; exige membresía en la empresa. Orden fijo: `operation_date` descendente, luego `created_at` descendente y por último `id`. El filtro `number` es de coincidencia exacta. Un parámetro de consulta desconocido se rechaza con `422`.

Antes necesita: el `company_id`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases?status=CONFIRMED&branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7&operation_date_from=2026-10-01&operation_date_to=2026-10-31&page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa cuyas compras se listan | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `status` | string | No | Estado de la compra | `DRAFT`, `CONFIRMED`, `CANCELLED`; ejemplo `CONFIRMED` | `?status=CONFIRMED` | Selector del filtro |
| `branch_id` | UUID | No | Sucursal de la compra | UUID; ejemplo `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `&branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7` | `memberships[].branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |
| `company_supplier_id` | UUID | No | Proveedor | UUID; ejemplo `d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60` | `&company_supplier_id=d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60` | `items[].id` de la [API 1](#1-buscar-el-proveedor) (lista los proveedores; errores en §1) · guía [company_supplier_id](../parametros/supplier-id.md) |
| `operation_date_from` | date (`AAAA-MM-DD`) | No | Fecha de compra desde (incluida) | Fecha; ejemplo `2026-10-01` | `&operation_date_from=2026-10-01` | Selector de fechas |
| `operation_date_to` | date (`AAAA-MM-DD`) | No | Fecha de compra hasta (incluida); no anterior a `operation_date_from` (`INVALID_DATE_RANGE`) | Fecha; ejemplo `2026-10-31` | `&operation_date_to=2026-10-31` | Selector de fechas |
| `number` | string (1–80) | No | Número de documento exacto | Texto; ejemplo `C-000045` | `&number=C-000045` | `number` de una compra confirmada (esta API o la [API 9](#9-confirmar-la-compra)) |
| `page` | integer | No; por defecto `1` | Página | Entero ≥ 1; ejemplo `1` | `&page=1` | Paginador |
| `page_size` | integer | No; por defecto `20` | Tamaño de página | Entero de 1 a 100; ejemplo `20` | `&page_size=20` | Paginador |

Los parámetros de consulta se agregan al final de la URL: el primero con `?` y los siguientes con `&`. URL armada del ejemplo anterior: `https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases?status=CONFIRMED&branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7&operation_date_from=2026-10-01&operation_date_to=2026-10-31&page=1&page_size=20`

**Encabezados:** `Authorization` (obligatorio).

**Cuerpo de la solicitud:** no lleva cuerpo.

### Cuerpo de la solicitud (Body)

No lleva cuerpo.

### Respuesta exitosa

`200 OK`:

```json
{
  "items": [
    {
      "id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
      "supplier_payment_condition_id": null,
      "payment_condition_code_snapshot": "CASH",
      "payment_terms_days_snapshot": 0,
      "due_date": "2026-10-19",
      "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
      "payment_method_code_snapshot": "TRANSFER",
      "payment_method_name_snapshot": "Transferencia bancaria",
      "purchase_sequence_id": "4e5f6a7b-8c9d-4e0f-9a1b-2c3d4e5f6a7b",
      "number": "C-000045",
      "sequence_value": 45,
      "status": "CONFIRMED",
      "operation_date": "2026-10-19",
      "promised_delivery_at": null,
      "supplier_document_number": "FV-8891",
      "supplier_name_snapshot": "Distribuidora Farma S.A.S.",
      "supplier_identification_snapshot": "NIT 900123456",
      "currency_code": "COP",
      "observations": null,
      "subtotal": "500000.00",
      "discount_total": "0.00",
      "tax_total": "95000.00",
      "total": "595000.00",
      "inventory_operation_id": null,
      "receipt_status": "PENDING",
      "received_at": null,
      "received_by_user_id": null,
      "created_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "cancelled_by_user_id": null,
      "cancelled_at": null,
      "cancellation_reason": null,
      "pending_operation_id": null,
      "version": 5,
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:30:00Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "lines": null
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
| `items[]` | array | Compras de la página, con los mismos campos de la [API 8](#8-consultar-la-compra-con-impuestos-y-totales) salvo `lines` (`null`) |
| `items[].id` | UUID | [purchase_id](../parametros/purchase-id.md) para abrir el detalle |
| `items[].receipt_status` | string \| null | `PENDING` identifica las compras por recibir |
| `page`, `page_size` | integer | Página y tamaño solicitados |
| `total_records`, `total_pages` | integer | Total de compras que cumplen los filtros y número de páginas (`0` si no hay ninguna) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `PURCHASE.NOT_FOUND` | La empresa no existe o el usuario no es miembro | Volver a leer el contexto operativo |
| `403` | `PURCHASE.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso para consultar su acceso operativo | Pedir acceso con el `trace_id` |
| `422` | `PURCHASE.VALIDATION_ERROR` | Filtro con formato inválido, `status` fuera de los valores, `page_size` fuera de 1–100, rango de fechas invertido (`INVALID_DATE_RANGE`) o parámetro desconocido (`UNKNOWN_FIELD`) | Corregir los filtros |

Ejemplo de `422` por rango de fechas invertido:

```json
{
  "type": "https://sio/errors/purchase/validation-error",
  "title": "Solicitud inválida",
  "status": 422,
  "detail": "La solicitud contiene datos inválidos.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases",
  "code": "PURCHASE.VALIDATION_ERROR",
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

---

## 13. Anular una compra

**Método:** `POST`
**URL:** `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/cancellation`
**Permiso requerido:** `perm:purchase:purchases:delete`

### ¿Qué hace esta API?

Deja sin efecto una compra en `DRAFT`, `CONFIRMED` sin recibir o `CONFIRMED` ya recibida, con un motivo obligatorio. Si estaba recibida, la mercancía sale del inventario de la sucursal. Está clasificada como `HIGH_RISK` en la ficha del servicio: el frontend debe pedir confirmación explícita al usuario antes de enviarla.

Efectos verificados en el código: valida el acceso a la sucursal y la `Idempotency-Key` (una clave repetida devuelve el resultado anterior), que no haya otra operación en curso, que la compra no esté ya `CANCELLED` (`409 INVALID_STATUS`) y la `version`. No revalida proveedor ni productos (pueden estar inactivos). Según el estado:

- `DRAFT` o `CONFIRMED` sin recibir: se anula en una transacción local, sin tocar Inventory; la operación `CANCEL` queda `SUCCEEDED`.
- `CONFIRMED` recibida: registra la operación `CANCEL` en `PENDING` y pide a Inventory el reverso **exacto** de la entrada `inventory_operation_id`. Si se aplica, la compra pasa a `CANCELLED` y la operación a `SUCCEEDED` con el `inventory_operation_id` del reverso (en el kardex aparece como reverso de entrada con `origin_type` `PURCHASE`). Si el reverso falla, la operación queda `FAILED` y la compra **sigue `CONFIRMED`**.
- Si parte de la mercancía ya se vendió o se ajustó (sus capas de costo fueron consumidas), Inventory rechaza el reverso y Purchase responde `409 INVENTORY_ALREADY_CONSUMED`: la compra no se puede anular y la corrección se hace con un ajuste de inventario ([Inventario](inventario.md)).

En todos los casos se conservan el `number` y los datos de la recepción (`receipt_status` sigue `RECEIVED` si se había recibido), se fijan `cancelled_at`, `cancelled_by_user_id` y `cancellation_reason`, se incrementa `version` y se registra `CANCEL_PURCHASE` en Audit (consultable con la [API 17 de Administración empresarial](administracion-empresarial.md#17-consultar-el-historial-de-una-venta-una-compra-o-un-producto)). Los precios de venta recalculados por la recepción **no** se revierten al anular.

Antes necesita: la `version` vigente ([API 8](#8-consultar-la-compra-con-impuestos-y-totales)) y el motivo escrito por el usuario.

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/cancellation' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: 2f1e0d9c-8b7a-4f6e-9d4c-3b2a1f0e9d8c' \
  -d '{
    "version": 6,
    "reason": "Mercancía devuelta al proveedor por error de pedido"
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa de la compra | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `purchase_id` | UUID | Sí | Compra que se anula (no `CANCELLED`) | `4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e` | `id` de la [API 4](#4-crear-la-compra-en-borrador) (crea el borrador; errores en §4) o `items[].id` de la [API 12](#12-listar-compras) (lista las compras; errores en §12) · guía [purchase_id](../parametros/purchase-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:**

- `Authorization` (obligatorio).
- `Content-Type: application/json` (obligatorio).
- `Idempotency-Key` (obligatorio): clave nueva para esta anulación; reutilizarla solo para reintentarla.
- `X-Correlation-Id` (opcional): UUID que se guarda en la operación.

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "version": 6,
  "reason": "Mercancía devuelta al proveedor por error de pedido"
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `version` | integer ≥ 1 | Sí | Versión vigente de la compra | `6` | `version` de la [API 8](#8-consultar-la-compra-con-impuestos-y-totales) (consulta la compra; errores en §8) o de la última escritura |
| `reason` | string (1–1000 tras recortar espacios) | Sí | Motivo de la anulación | `Mercancía devuelta al proveedor por error de pedido` | Formulario (texto escrito por el usuario) |

### Respuesta exitosa

`200 OK` (la compra recibida y luego anulada, `version` `7`):

```json
{
  "id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "supplier_payment_condition_id": null,
  "payment_condition_code_snapshot": "CASH",
  "payment_terms_days_snapshot": 0,
  "due_date": "2026-10-19",
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "payment_method_code_snapshot": "TRANSFER",
  "payment_method_name_snapshot": "Transferencia bancaria",
  "purchase_sequence_id": "4e5f6a7b-8c9d-4e0f-9a1b-2c3d4e5f6a7b",
  "number": "C-000045",
  "sequence_value": 45,
  "status": "CANCELLED",
  "operation_date": "2026-10-19",
  "promised_delivery_at": null,
  "supplier_document_number": "FV-8891",
  "supplier_name_snapshot": "Distribuidora Farma S.A.S.",
  "supplier_identification_snapshot": "NIT 900123456",
  "currency_code": "COP",
  "observations": null,
  "subtotal": "500000.00",
  "discount_total": "0.00",
  "tax_total": "95000.00",
  "total": "595000.00",
  "inventory_operation_id": "5f6a7b8c-9d0e-4f1a-8b2c-3d4e5f6a7b8c",
  "receipt_status": "RECEIVED",
  "received_at": "2026-10-19T16:30:00Z",
  "received_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "created_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "cancelled_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "cancelled_at": "2026-10-19T17:00:00Z",
  "cancellation_reason": "Mercancía devuelta al proveedor por error de pedido",
  "pending_operation_id": null,
  "version": 7,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T17:00:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "lines": [
    {
      "id": "b1a1e4be-5fb8-42b0-81c5-ca85b2fdcea6",
      "purchase_id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
      "line_number": 1,
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "supplier_product_id": null,
      "supplier_lead_time_snapshot_hours": null,
      "product_code_snapshot": "PRD-0001",
      "product_name_snapshot": "Acetaminofén 500 mg",
      "presentation_code_snapshot": "CJ100",
      "presentation_name_snapshot": "Caja x 100 tabletas",
      "base_quantity_factor_snapshot": "1.00000000",
      "unit_code_snapshot": "UN",
      "quantity": "10.0000",
      "unit_cost": "50000.0000",
      "discount_amount": "0.00",
      "tax_amount": "95000.00",
      "tax_percentage": "19.0000",
      "tax_percentage_source": "PRODUCT_DEFAULT",
      "warnings": [],
      "subtotal": "500000.00",
      "total": "595000.00",
      "base_quantity": "10.0000",
      "inventory_unit_cost": "50000.0000",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ]
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `status` | string | `CANCELLED` |
| `cancelled_at`, `cancelled_by_user_id`, `cancellation_reason` | date-time, UUID, string | Cuándo, quién y por qué se anuló |
| `number`, `receipt_status`, `received_at`, `inventory_operation_id` | | Se conservan; `inventory_operation_id` sigue siendo la entrada original (el reverso está en la operación `CANCEL` de la [API 11](#11-consultar-el-estado-de-las-operaciones)) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `403` | `PURCHASE.BRANCH_ACCESS_DENIED` | Sin asignación `ACTIVE` a la sucursal | Pedir la asignación |
| `404` | `PURCHASE.NOT_FOUND` | La compra no existe o el usuario no es miembro | Volver a la lista |
| `409` | `PURCHASE.INVALID_STATUS` | La compra ya está `CANCELLED` | Recargar |
| `409` | `PURCHASE.VERSION_CONFLICT` | `version` desactualizada | Consultar y reintentar con una clave nueva |
| `409` | `PURCHASE.OPERATION_IN_PROGRESS` | Hay otra operación en curso (`operation_id`) | Consultar la [API 11](#11-consultar-el-estado-de-las-operaciones) |
| `409` | `PURCHASE.IDEMPOTENCY_KEY_CONFLICT` | La clave ya se usó en otra solicitud | Generar una clave nueva |
| `409` | `PURCHASE.INVENTORY_ALREADY_CONSUMED` | Parte de la mercancía ya se consumió en Inventory | Informar que no se puede anular; corregir con un ajuste de inventario |
| `409` | `PURCHASE.INVENTORY_REJECTED` | Inventory rechazó el reverso por otro motivo (`details.inventory_code`, `details.inventory_status`) | Mostrar el motivo |
| `409` | `PURCHASE.OPERATION_NOT_APPLIED` | La conciliación comprobó que Inventory nunca aplicó el reverso | Repetir con una clave nueva |
| `422` | `PURCHASE.VALIDATION_ERROR` | Motivo vacío (`REASON_REQUIRED`) o de más de 1000 caracteres (`INVALID_FORMAT`), falta la clave (`IDEMPOTENCY_KEY_REQUIRED`) o falta `version` | Corregir según `errors[]` |
| `503` | `PURCHASE.DEPENDENCY_UNAVAILABLE` | Inventory no respondió (`dependency` `inventory`, `operation_id`); la operación queda `PENDING` | Reintentar con la **misma** clave o consultar la [API 11](#11-consultar-el-estado-de-las-operaciones) |

Ejemplo de `409` por mercancía ya consumida:

```json
{
  "type": "https://sio/errors/purchase/inventory-already-consumed",
  "title": "Inventario ya consumido",
  "status": 409,
  "detail": "La compra no se puede anular porque sus unidades ya fueron consumidas en Inventory. Anule antes las ventas que las consumieron o solicite un ajuste.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/cancellation",
  "code": "PURCHASE.INVENTORY_ALREADY_CONSUMED",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

Ejemplo de `422` por motivo vacío:

```json
{
  "type": "https://sio/errors/purchase/validation-error",
  "title": "Solicitud inválida",
  "status": 422,
  "detail": "La solicitud contiene datos inválidos.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/cancellation",
  "code": "PURCHASE.VALIDATION_ERROR",
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

---

## Dependencias con otros módulos

- [Acceso y contexto operativo](acceso-y-contexto-operativo.md): Access Token, empresas y sucursales del usuario (`company_id`, `branch_id`).
- [Administración empresarial](administracion-empresarial.md): asignación del comprador a la sucursal, secuencias de numeración de compras e historial de auditoría.
- [Gestión de proveedores](gestion-de-proveedores.md): proveedor `ACTIVE`, condiciones de pago y productos de proveedor.
- [Productos y precios](productos-y-precios.md): presentaciones comprables, tasa de impuesto de compra y políticas de ganancia; la recepción alimenta los precios automáticos.
- [Inventario](inventario.md): la recepción crea la entrada (`origin_type` `PURCHASE` en el kardex) y las capas de costo; la anulación de una compra recibida las revierte si no se consumieron.
- [Reportes](reportes.md): compras del período.
