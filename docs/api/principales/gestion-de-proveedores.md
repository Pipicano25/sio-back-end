# 6.4 Gestión de proveedores

[← API principales](README.md) · [← Índice](../index.md)

Registrar, buscar, consultar y actualizar los proveedores a los que la empresa compra, y configurar lo que Compras necesita de ellos. Como en clientes, la **identidad** (siempre una organización) vive en [Party Identity](../servicios/party-identity.md) y la **relación comercial** (`company_supplier_id`, código, nombre, estado) en [Commercial Relationship](../servicios/commercial-relationship.md). Purchase usa siempre el `company_supplier_id` ([supplier-id](../parametros/supplier-id.md)).

| # | Funcionalidad | Método y ruta | Permiso | Ficha |
|---|---|---|---|---|
| 1 | Buscar o crear la identidad de la organización | `GET /api/v1/organization-identities` · `POST /api/v1/organization-identities` (Party Identity) | `perm:party-identity:organization_identities:read` · `…:create` | [PI 9](../servicios/party-identity.md#9-get-organization-identities) · [PI 10](../servicios/party-identity.md#10-post-organization-identities) |
| 2 | Registrar un proveedor de la empresa | `POST /api/v1/companies/{company_id}/company-suppliers` (CR) | `perm:commercial-relationship:company_suppliers:create` | [CR 20](../servicios/commercial-relationship.md#20-post-companiescompany_idcompany-suppliers) |
| 3 | Buscar y listar proveedores | `GET /api/v1/companies/{company_id}/company-suppliers` (CR) | `perm:commercial-relationship:company_suppliers:read` | [CR 19](../servicios/commercial-relationship.md#19-get-companiescompany_idcompany-suppliers) |
| 4 | Consultar un proveedor | `GET /api/v1/company-suppliers/{company_supplier_id}` (CR) | `perm:commercial-relationship:company_suppliers:read` | [CR 21](../servicios/commercial-relationship.md#21-get-company-supplierscompany_supplier_id) |
| 5 | Consultar la identidad y los contactos del proveedor | `GET /api/v1/organization-identities/{organization_identity_id}` · `…/contact-persons` (Party Identity) | `perm:party-identity:organization_identities:read` · `…organization_contact_persons:read` | [PI 11](../servicios/party-identity.md#11-get-organization-identitiesorganization_identity_id) · [PI 31](../servicios/party-identity.md#31-get-organization-identitiesorganization_identity_idcontact-persons) |
| 6 | Actualizar un proveedor | `PUT /api/v1/company-suppliers/{company_supplier_id}` (CR) | `perm:commercial-relationship:company_suppliers:update` | [CR 22](../servicios/commercial-relationship.md#22-put-company-supplierscompany_supplier_id) |
| 7 | Inactivar, reactivar, bloquear o desbloquear | `POST …/company-suppliers/{company_supplier_id}/deactivate` · `/reactivate` · `/block` · `/unblock` (CR) | `…company_suppliers:delete` (inactivar, bloquear) · `…:update` (reactivar, desbloquear) | [CR 23](../servicios/commercial-relationship.md#23-post-company-supplierscompany_supplier_iddeactivate) · [CR 24](../servicios/commercial-relationship.md#24-post-company-supplierscompany_supplier_idreactivate) · [CR 75](../servicios/commercial-relationship.md#75-post-company-supplierscompany_supplier_idblock) · [CR 76](../servicios/commercial-relationship.md#76-post-company-supplierscompany_supplier_idunblock) |
| 8 | Condiciones de pago del proveedor (opcional para Compras) | `GET` · `POST /api/v1/companies/{company_id}/supplier-payment-conditions` (CR) | `perm:commercial-relationship:supplier_payment_conditions:read` · `…:create` | [CR 40](../servicios/commercial-relationship.md#40-get-companiescompany_idsupplier-payment-conditions) · [CR 41](../servicios/commercial-relationship.md#41-post-companiescompany_idsupplier-payment-conditions) |
| 9 | Productos que suministra el proveedor (opcional para Compras) | `GET` · `POST /api/v1/companies/{company_id}/supplier-products` (CR) | `perm:commercial-relationship:supplier_products:read` · `…:create` | [CR 34](../servicios/commercial-relationship.md#34-get-companiescompany_idsupplier-products) · [CR 35](../servicios/commercial-relationship.md#35-post-companiescompany_idsupplier-products) |

Bases: Party Identity `https://sio-party-identity-dev.onrender.com/api/v1`; Commercial Relationship `https://sio-commercial-relationship-dev.onrender.com/api/v1`.

---

## 1. Buscar o crear la identidad de la organización

Igual que en [Gestión de clientes §1 y 2](gestion-de-clientes.md#1-y-2-buscar-o-crear-la-identidad): `GET https://sio-party-identity-dev.onrender.com/api/v1/organization-identities?search=<NIT o nombre>` y, si no existe, `POST …/organization-identities` con `country_id`, `identification_type`, `identification_number`, `legal_name` (+ `trade_name`, `organization_type`, `registration_status`, `website`). El identificador que se necesita es `id` ([organization_identity_id](../parametros/organization-identity-id.md)). Un proveedor **siempre** es una organización: no existen proveedores persona natural en el contrato (`CompanySupplierCreate` solo acepta `organization_identity_id`).

## 2. Registrar un proveedor de la empresa

**¿Qué puede hacer el usuario?** Incorporar una organización como proveedor de su empresa, con código interno y nombre comercial.

**¿Qué API debe consumir el frontend?** `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-suppliers`. Permiso `perm:commercial-relationship:company_suppliers:create`. Cuerpo `CompanySupplierCreate`: `organization_identity_id` (obligatorio), `internal_code` (1–60, único en la empresa), `display_name` (1–200), `preferred_contact_person_id` (opcional; persona de contacto activa de esa organización en Party Identity).

```json
{
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "internal_code": "PRV-0001",
  "display_name": "Distribuidora Farma S.A.S."
}
```

**¿Qué necesita antes?** [company_id](../parametros/company-id.md) con membresía activa y la identidad de la funcionalidad 1, `ACTIVE` y distinta de la organización de la propia empresa.

**¿Cómo sabe que funcionó?** `201` con `CompanySupplierResponse`: `id` (el [company_supplier_id](../parametros/supplier-id.md)), `organization_identity_id`, `internal_code`, `display_name`, `preferred_contact_person_id`, `status: "ACTIVE"`, `version: 1`. Errores: `409 DUPLICATE_SUPPLIER` (la organización ya es proveedor de la empresa), `409 DUPLICATE_INTERNAL_CODE`, `409 SELF_RELATIONSHIP_NOT_ALLOWED`, `422 ORGANIZATION_IDENTITY_NOT_FOUND` / `ORGANIZATION_IDENTITY_INACTIVE`, `422 CONTACT_PERSON_INVALID`, `503 DEPENDENCY_UNAVAILABLE`.

## 3. Buscar y listar proveedores

**¿Qué API debe consumir el frontend?** `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-suppliers`. Permiso `perm:commercial-relationship:company_suppliers:read`. Consulta: `page`, `page_size`, `search` (≤ 100; código y nombre), `status` (`ACTIVE`, `INACTIVE`, `BLOCKED`, `ALL`), `organization_identity_id`.

**¿Cómo sabe que funcionó?** `200` con `PaginatedResponse[CompanySupplierResponse]`; el selector de proveedor de una compra debe filtrar `status=ACTIVE`, porque Purchase rechaza los demás.

## 4 y 5. Consultar un proveedor, su identidad y sus contactos

`GET https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/{company_supplier_id}` (`200` con `CompanySupplierResponse`, `404` si es de otra empresa). Razón social, NIT y sitio web: `GET https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}`. Personas de contacto: `GET …/organization-identities/{organization_identity_id}/contact-persons` (PI 31; el `id` de cada una sirve para `preferred_contact_person_id`). Perfil de contacto vigente (teléfono, correo, dirección): `GET …/organization-identities/{organization_identity_id}/contact-profile` (PI 26).

## 6. Actualizar un proveedor

`PUT https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/{company_supplier_id}` (permiso `perm:commercial-relationship:company_suppliers:update`) con `version`, `internal_code`, `display_name`, `preferred_contact_person_id`. `organization_identity_id` y `status` son inmutables. Responde `200`; errores `409 VERSION_CONFLICT`, `409 DUPLICATE_INTERNAL_CODE`.

## 7. Inactivar, reactivar, bloquear o desbloquear

**¿Qué puede hacer el usuario?** Retirar un proveedor del uso (`INACTIVE`), suspenderlo temporalmente por un motivo (`BLOCKED`, con `block_reason`) o devolverlo a `ACTIVE`.

**¿Qué API debe consumir el frontend?** `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/{company_supplier_id}/deactivate`, `/reactivate`, `/block`, `/unblock`, con `{"version": n}` (`block` exige además `block_reason`, 1–500 caracteres). Permisos: `perm:commercial-relationship:company_suppliers:delete` para inactivar y bloquear; `…:update` para reactivar y desbloquear.

**¿Cómo sabe que funcionó?** `200` con el nuevo `status`. Efecto en Compras: un proveedor `INACTIVE` o `BLOCKED` hace fallar la creación o confirmación de compras con `409 REFERENCES_NOT_ELIGIBLE` (`SUPPLIER_NOT_ELIGIBLE`); las compras ya confirmadas no cambian.

## 8. Condiciones de pago del proveedor

**¿Qué puede hacer el usuario?** Registrar los plazos y cupos acordados con el proveedor para elegirlos al comprar.

**¿Qué API debe consumir el frontend?** `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/supplier-payment-conditions` (permiso `perm:commercial-relationship:supplier_payment_conditions:create`) con `company_supplier_id`, `payment_condition_type_id` (tipo global de Payment Reference: `GET https://sio-payment-reference-dev.onrender.com/global-payment-condition-types`), `currency_code`, `payment_terms_days` (0–3650), `credit_limit`, `interest_rate_percentage`, `cash_discount_percentage`, `is_default`, `valid_from`, `valid_to`. Consulta: `GET …/companies/{company_id}/supplier-payment-conditions?company_supplier_id=…`.

**¿Cómo sabe que funcionó?** `201` con el `id` (`supplier_payment_condition_id`), que Purchase acepta como `supplier_payment_condition_id` **opcional** en la cabecera de la compra; debe pertenecer al mismo proveedor (`409 REFERENCES_NOT_ELIGIBLE`, `PAYMENT_CONDITION_OF_OTHER_SUPPLIER`).

## 9. Productos que suministra el proveedor

**¿Qué puede hacer el usuario?** Registrar qué productos de la empresa le compra a cada proveedor, con código del proveedor, unidad de compra, costo negociado y tiempos de entrega, para sugerirlos al armar una compra.

**¿Qué API debe consumir el frontend?** `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/supplier-products` (permiso `perm:commercial-relationship:supplier_products:create`) con `company_supplier_id`, `company_product_id`, `purchase_unit_id`, `currency_code` (obligatorios) y `company_product_presentation_id`, `supplier_product_code`, `minimum_order_quantity`, `pack_quantity`, `negotiated_unit_cost`, `expected_supplier_lead_time_hours`, `priority`, `is_preferred`. Consulta: `GET …/companies/{company_id}/supplier-products?company_supplier_id=…`.

**¿Cómo sabe que funcionó?** `201` con `id` (`supplier_product_id`). Purchase lo acepta como `supplier_product_id` **opcional** en cada línea; si se envía, debe ser del mismo proveedor y producto (`SUPPLIER_PRODUCT_MISMATCH`) y estar activo (`SUPPLIER_PRODUCT_INACTIVE`). El costo de la línea (`unit_cost`) lo escribe siempre el comprador: `negotiated_unit_cost` es solo una referencia para el frontend.

## Lo que Compras exige del proveedor

| Requisito | Obligatorio | Dónde se configura |
|---|---|---|
| `company_supplier_id` con `status: ACTIVE` | Sí | Funcionalidades 2 y 7 |
| `payment_method_id` activo | Sí (cabecera de la compra) | Payment Reference ([payment_method_id](../parametros/payment-method-id.md)) |
| `supplier_payment_condition_id` del mismo proveedor | No | Funcionalidad 8 |
| `supplier_product_id` por línea | No | Funcionalidad 9 |
| Impuesto de compra y política de ganancia por producto o presentación | Sí para confirmar | [Productos y precios](productos-y-precios.md) |

## Dependencias con otros módulos

- [Compras](compras.md) consume el proveedor, sus condiciones y sus productos.
- [Productos y precios](productos-y-precios.md) define los productos empresariales a los que se asocian los productos de proveedor.
- [Gestión de clientes](gestion-de-clientes.md) y [Administración empresarial](administracion-empresarial.md) comparten las identidades de organización.
