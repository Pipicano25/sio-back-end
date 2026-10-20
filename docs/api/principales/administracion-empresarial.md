# 6.2 Administración empresarial

[← API principales](README.md) · [← Índice](../index.md)

Operaciones con las que un administrador configura una empresa cliente de SIO: la empresa misma, sus sucursales, las personas que trabajan en ella (membresías), las sucursales a las que cada una puede acceder, la trazabilidad de lo que ocurre en la empresa (auditoría) y la numeración de los documentos comerciales.

Servicios implicados: [Operational Context](../servicios/operational-context.md) (propietario de empresas, sucursales, membresías y asignaciones), [Party Identity](../servicios/party-identity.md) (identidad legal de la empresa y de cada usuario), [Geography](../servicios/geography.md) (ubicación), Keycloak (la cuenta con la que el usuario inicia sesión), [Audit](../servicios/audit.md) (trazabilidad) y las secuencias de [Sales](../servicios/sales.md) y [Purchase](../servicios/purchase.md) (numeración). Flujo completo con JSON: [Crear una empresa y una sucursal](../ejemplos/crear-empresa-y-sucursal.md).

| # | Funcionalidad | Método y ruta (Operational Context, base `https://sio-operational-context-dev.onrender.com/api/v1`) | Permiso (`perm:operational-context:…`) | Ficha |
|---|---|---|---|---|
| 1 | Crear empresa | `POST /companies` | `companies:create` **y** `platform:administer` | [OC 4](../servicios/operational-context.md#4-post-companies) |
| 2 | Consultar empresas del alcance | `GET /companies` | `companies:read` | [OC 3](../servicios/operational-context.md#3-get-companies) |
| 3 | Consultar una empresa | `GET /companies/{company_id}` | `companies:read` | [OC 5](../servicios/operational-context.md#5-get-companiescompany_id) |
| 4 | Actualizar empresa | `PUT /companies/{company_id}` | `companies:update` | [OC 6](../servicios/operational-context.md#6-put-companiescompany_id) |
| 5 | Crear sucursal | `POST /companies/{company_id}/branches` | `branches:create` | [OC 10](../servicios/operational-context.md#10-post-companiescompany_idbranches) |
| 6 | Consultar sucursales de la empresa | `GET /companies/{company_id}/branches` | `branches:read` | [OC 9](../servicios/operational-context.md#9-get-companiescompany_idbranches) |
| 7 | Consultar una sucursal | `GET /branches/{branch_id}` | `branches:read` | [OC 11](../servicios/operational-context.md#11-get-branchesbranch_id) |
| 8 | Actualizar sucursal | `PUT /branches/{branch_id}` | `branches:update` | [OC 12](../servicios/operational-context.md#12-put-branchesbranch_id) |
| 9 | Consultar usuarios de la empresa | `GET /companies/{company_id}/application-users` | `application_users:read` | [OC 15](../servicios/operational-context.md#15-get-companiescompany_idapplication-users) |
| 10 | Asociar un usuario a la empresa (crear membresía) | `POST /companies/{company_id}/application-users` | `application_users:create` | [OC 16](../servicios/operational-context.md#16-post-companiescompany_idapplication-users) |
| 11 | Consultar sucursales permitidas de un usuario | `GET /application-users/{application_user_id}/user-branches` | `user_branches:read` | [OC 21](../servicios/operational-context.md#21-get-application-usersapplication_user_iduser-branches) |
| 12 | Asignar un usuario a una sucursal | `POST /application-users/{application_user_id}/user-branches` | `user_branches:create` | [OC 22](../servicios/operational-context.md#22-post-application-usersapplication_user_iduser-branches) |
| 13 | Consultar usuarios asignados a una sucursal | `GET /branches/{branch_id}/user-branches` | `user_branches:read` | [OC 23](../servicios/operational-context.md#23-get-branchesbranch_iduser-branches) |
| 14 | Inactivar una membresía | `POST /application-users/{application_user_id}/deactivate` | `application_users:delete` | [OC 19](../servicios/operational-context.md#19-post-application-usersapplication_user_iddeactivate) |
| 15 | Reactivar una membresía | `POST /application-users/{application_user_id}/reactivate` | `application_users:update` | [OC 20](../servicios/operational-context.md#20-post-application-usersapplication_user_idreactivate) |
| 16 | Consultar la trazabilidad de la empresa (auditoría) | `GET /companies/{company_id}/audit-events` · `…/audit-events/{audit_id}` (Audit, base `https://sio-audit-dev.onrender.com/api/v1`) | `perm:audit:audit-events:read` | [Audit 5](../servicios/audit.md#5-get-companiescompany_idaudit-events) · [Audit 6](../servicios/audit.md#6-get-companiescompany_idaudit-eventsaudit_id) |
| 17 | Consultar el historial de una venta, una compra o un producto | `GET /companies/{company_id}/entity-history/{entity_type}/{entity_id}` (Audit) | `perm:audit:audit-events:read` | [Audit 7](../servicios/audit.md#7-get-companiescompany_identity-historyentity_typeentity_id) |
| 18–21 | Numeración de documentos comerciales: consultar, crear, activar o desactivar y modificar secuencias | `GET` · `POST /companies/{company_id}/sale-sequences[/{sequence_id}[/deactivate\|/reactivate]]` (Sales) y `…/purchase-sequences…` (Purchase) | `perm:sales:sale_sequences:read` · `…:create` · `…:update`; `perm:purchase:purchase_sequences:read` · `…:create` · `…:update` | Ver la [sección de numeración](#numeración-de-documentos-comerciales) |

Operaciones relacionadas que no se consideran principales (ver la ficha): inactivar o reactivar empresas y sucursales (OC 7, 8, 13, 14), retirar o reactivar una asignación de sucursal (OC 25, 26), modificar los datos de referencia de un usuario (OC 18), la gestión de asesores (OC 27–31) y los eventos de auditoría de plataforma (Audit 8–10).

---

## 1. Crear empresa

**¿Qué puede hacer el usuario?** Un administrador de la plataforma da de alta una nueva empresa cliente.

**¿Qué API debe consumir el frontend?** `POST https://sio-operational-context-dev.onrender.com/api/v1/companies`. Permisos: `perm:operational-context:companies:create` **y** `perm:operational-context:platform:administer` (en el realm de desarrollo solo el grupo `administradores` lo tiene). Cuerpo `CompanyCreate`: `organization_identity_id` (obligatorio), `email`, `phone`, `address_line`, `country_id`, `administrative_division_id`, `city_id`, `postal_code`, `latitude`, `longitude`, `timezone` (por defecto `America/Bogota`), `default_currency` (por defecto `COP`). No tiene `name`: la razón social vive en Party Identity.

**¿Qué necesita antes?**

1. La **identidad de la organización** en Party Identity: `POST https://sio-party-identity-dev.onrender.com/api/v1/organization-identities` (permiso `perm:party-identity:organization_identities:create`) o búsqueda con `GET …/organization-identities?search=` ([organization_identity_id](../parametros/organization-identity-id.md)). Debe estar `ACTIVE` y no estar ya vinculada a otra empresa.
2. Si se envía dirección, los tres identificadores geográficos coherentes entre sí ([country_id, administrative_division_id, city_id](../parametros/country-id.md)).

**¿Cómo sabe que funcionó?** `201` con `CompanyResponse`: `id` (el nuevo [company_id](../parametros/company-id.md)), `status: "ACTIVE"`, `version: 1`. Efectos verificados en el código (`company_service.py`): **no se crea ninguna membresía ni sucursal**. El administrador que la creó la ve gracias a `platform:administer`; el primer usuario de la empresa se incorpora con la funcionalidad 10. Errores: `422 ORGANIZATION_IDENTITY_NOT_FOUND` / `ORGANIZATION_IDENTITY_INACTIVE`, `409 DUPLICATE_ORGANIZATION_IDENTITY`, `422 COUNTRY_NOT_FOUND` / `ADMINISTRATIVE_DIVISION_NOT_FOUND` / `CITY_NOT_FOUND` / `GEOGRAPHY_INCOHERENT` / `LOCATION_INACTIVE`, `403` sin `platform:administer`, `503 DEPENDENCY_UNAVAILABLE` si Party Identity o Geography no responden.

## 2. Consultar empresas del alcance

**¿Qué puede hacer el usuario?** Ver las empresas en las que tiene membresía (o todas, si administra la plataforma) con sus datos de contacto y estado.

**¿Qué API debe consumir el frontend?** `GET https://sio-operational-context-dev.onrender.com/api/v1/companies`. Permiso `perm:operational-context:companies:read`. Consulta: `page`, `page_size` (1–100), `status` (`ACTIVE` por defecto; `INACTIVE`), `organization_identity_id`, `country_id`, `city_id`.

**¿Qué necesita antes?** Nada más que el token. Para un usuario normal el resultado coincide con las empresas de `memberships[]` de [Acceso y contexto operativo](acceso-y-contexto-operativo.md); para `platform:administer` incluye todas.

**¿Cómo sabe que funcionó?** `200` con `PaginatedResponse[CompanyResponse]` (`items[]`, `total`, `page`, `page_size`). Cada elemento trae `id`, `organization_identity_id`, dirección, `timezone`, `default_currency`, `status`, `version`.

## 3. Consultar una empresa

**¿Qué puede hacer el usuario?** Ver la ficha completa de una empresa (por ejemplo, la seleccionada en la sesión) para mostrar sus datos en la cabecera de la aplicación.

**¿Qué API debe consumir el frontend?** `GET https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}`. Permiso `perm:operational-context:companies:read`.

**¿Qué necesita antes?** [company_id](../parametros/company-id.md). Para mostrar la razón social: `GET https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}` (permiso `perm:party-identity:organization_identities:read`).

**¿Cómo sabe que funcionó?** `200` con `CompanyResponse`. `404 NOT_FOUND` si la empresa no está en el alcance (sin membresía y sin `platform:administer`); también se admite `perm:operational-context:platform:lookup` para lecturas por UUID sin membresía.

## 4. Actualizar empresa

**¿Qué puede hacer el usuario?** Corregir datos de contacto, dirección, zona horaria o moneda por defecto.

**¿Qué API debe consumir el frontend?** `PUT https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}`. Permiso `perm:operational-context:companies:update` (no exige `platform:administer`). Cuerpo `CompanyUpdate`: los campos editables de la creación más `version`. `organization_identity_id` es **inmutable** (`422 IMMUTABLE_FIELD`).

**¿Qué necesita antes?** La versión actual (`version` de la última lectura) y, si cambia la ubicación, identificadores geográficos coherentes.

**¿Cómo sabe que funcionó?** `200` con `CompanyResponse` y `version` incrementada. `409 VERSION_CONFLICT` si alguien la modificó antes; `422 COMPANY_INACTIVE` si la empresa está inactiva.

## 5. Crear sucursal

**¿Qué puede hacer el usuario?** Registrar un punto de operación (tienda, bodega, farmacia) donde se venderá, comprará y controlará inventario.

**¿Qué API debe consumir el frontend?** `POST https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/branches`. Permiso `perm:operational-context:branches:create`. Cuerpo `BranchCreate`: `code` (único por empresa) y `name` obligatorios; `email`, `phone`, `address_line`, `country_id`, `administrative_division_id`, `city_id`, `postal_code`, `latitude`, `longitude`, `timezone` (si se omite, hereda la de la empresa; la respuesta lo muestra en `effective_timezone`).

**¿Qué necesita antes?** [company_id](../parametros/company-id.md) de una empresa `ACTIVE`, membresía activa del administrador en ella (o `platform:administer`) y, opcionalmente, la ubicación ([country-id](../parametros/country-id.md)).

**¿Cómo sabe que funcionó?** `201` con `BranchResponse` (`id` = [branch_id](../parametros/branch-id.md), `status: "ACTIVE"`, `version: 1`). Efecto verificado: crear la sucursal **no asigna a ningún usuario**; cada usuario que deba operar en ella se asigna con la funcionalidad 12. Errores: `409 DUPLICATE_BRANCH_CODE`, `422 COMPANY_INACTIVE`, `422` de geografía, `404` si la empresa está fuera del alcance.

## 6. Consultar sucursales de la empresa

**¿Qué puede hacer el usuario?** Listar las sucursales para administrarlas o para mostrar su nombre junto al `branch_id` del contexto operativo.

**¿Qué API debe consumir el frontend?** `GET https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/branches`. Permiso `perm:operational-context:branches:read`. Consulta: `page`, `page_size`, `search` (≤ 160; código y nombre), `status` (`ACTIVE` por defecto), `city_id`.

**¿Qué necesita antes?** [company_id](../parametros/company-id.md) y membresía en la empresa.

**¿Cómo sabe que funcionó?** `200` con `PaginatedResponse[BranchResponse]`. Esta lista muestra **todas** las sucursales de la empresa, no solo las que el usuario tiene asignadas; para el acceso efectivo usa `memberships[].branches[]` de `/me/operational-context`.

## 7. Consultar una sucursal

**¿Qué API debe consumir el frontend?** `GET https://sio-operational-context-dev.onrender.com/api/v1/branches/{branch_id}`. Permiso `perm:operational-context:branches:read`. Responde `200` con `BranchResponse` (incluye `company_id` y `company_status`) o `404` fuera del alcance. Necesita [branch_id](../parametros/branch-id.md).

## 8. Actualizar sucursal

**¿Qué API debe consumir el frontend?** `PUT https://sio-operational-context-dev.onrender.com/api/v1/branches/{branch_id}`. Permiso `perm:operational-context:branches:update`. Cuerpo `BranchUpdate`: los campos de la creación más `version`. La empresa de la sucursal es inmutable. Responde `200` con `BranchResponse`; errores `409 VERSION_CONFLICT`, `409 DUPLICATE_BRANCH_CODE`, `422` de geografía.

## 9. Consultar usuarios de la empresa

**¿Qué puede hacer el usuario?** Ver quiénes tienen membresía en la empresa, su estado y buscar por nombre o correo.

**¿Qué API debe consumir el frontend?** `GET https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/application-users`. Permiso `perm:operational-context:application_users:read`. Consulta: `page`, `page_size`, `status` (`ACTIVE` por defecto; `INACTIVE`), `search` (≤ 160; `display_name` y `reference_email`), `keycloak_user_id`, `person_identity_id`.

**¿Qué necesita antes?** [company_id](../parametros/company-id.md) y membresía en la empresa (o `platform:administer`).

**¿Cómo sabe que funcionó?** `200` con `PaginatedResponse[ApplicationUserResponse]`: `id` ([application_user_id](../parametros/application-user-id.md)), `company_id`, `keycloak_user_id`, `person_identity_id`, `display_name`, `reference_email`, `status`, `version`. Las sucursales de cada usuario no vienen aquí: se consultan con la funcionalidad 11.

## 10. Asociar un usuario a la empresa (crear membresía)

**¿Qué puede hacer el usuario?** Dar acceso a la empresa a una persona que ya tiene cuenta en Keycloak.

**¿Qué API debe consumir el frontend?** `POST https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/application-users`. Permiso `perm:operational-context:application_users:create` (operación `HIGH_RISK`). Cuerpo `ApplicationUserCreate` (rechaza campos adicionales):

| Campo | Obligatorio | Significado |
|---|---|---|
| `keycloak_user_id` **o** `username` | Exactamente uno | `sub` del usuario en Keycloak, o su nombre de usuario (Operational Context lo resuelve en Keycloak) |
| `person_identity_id` | Sí | Persona en Party Identity ([cómo obtenerlo](../parametros/person-identity-id.md)) |
| `display_name` | Sí | Nombre a mostrar en la empresa |
| `reference_email` | No | Correo de referencia |

```json
{
  "username": "ana.perez",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "display_name": "Ana Pérez",
  "reference_email": "ana.perez@example.com"
}
```

**¿Qué necesita antes?**

1. La cuenta del usuario en Keycloak, habilitada y con los roles de `sio-api` que correspondan a su función (la asignación de roles se hace en Keycloak, no en estas API).
2. La **identidad de la persona** en Party Identity: `POST https://sio-party-identity-dev.onrender.com/api/v1/person-identities` o búsqueda con `GET …/person-identities?search=` ([person_identity_id](../parametros/person-identity-id.md)).
3. Que el administrador vea la empresa: membresía activa en ella o `platform:administer`. Por eso la **primera membresía** de una empresa recién creada la registra el administrador de plataforma.

**¿Cómo sabe que funcionó?** `201` con `ApplicationUserResponse` (`id` = [application_user_id](../parametros/application-user-id.md), `status: "ACTIVE"`). Desde ese momento el usuario verá la empresa en `/me/operational-context`, pero **sin sucursales** hasta la funcionalidad 12. Errores: `422 KEYCLOAK_USER_NOT_FOUND`, `422 KEYCLOAK_USER_DISABLED`, `422 TECHNICAL_ACCOUNT_NOT_ALLOWED` (cuentas de servicio), `422 PERSON_IDENTITY_NOT_FOUND` / `PERSON_IDENTITY_INACTIVE`, `409 DUPLICATE_MEMBERSHIP` (la cuenta o la persona ya tiene membresía en la empresa), `422 COMPANY_INACTIVE`, `503 DEPENDENCY_UNAVAILABLE` (Keycloak o Party Identity no disponibles).

## 11. Consultar sucursales permitidas de un usuario

**¿Qué API debe consumir el frontend?** `GET https://sio-operational-context-dev.onrender.com/api/v1/application-users/{application_user_id}/user-branches`. Permiso `perm:operational-context:user_branches:read`. Consulta: `page`, `page_size`, `status`. Responde `200` con `PaginatedResponse[UserBranchResponse]`: `id` (`user_branch_id`), `application_user_id`, `branch_id`, `status`, `version` y `operational_access` (`allowed`, `reason`) calculado con las mismas reglas del contexto operativo. Necesita [application_user_id](../parametros/application-user-id.md).

## 12. Asignar un usuario a una sucursal

**¿Qué puede hacer el usuario?** Autorizar a un miembro de la empresa a operar en una sucursal concreta (vender, comprar, ajustar inventario).

**¿Qué API debe consumir el frontend?** `POST https://sio-operational-context-dev.onrender.com/api/v1/application-users/{application_user_id}/user-branches`. Permiso `perm:operational-context:user_branches:create` (`HIGH_RISK`). Cuerpo `UserBranchCreate`: `{"branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7"}`.

**¿Qué necesita antes?** [application_user_id](../parametros/application-user-id.md) de una membresía `ACTIVE` y [branch_id](../parametros/branch-id.md) de una sucursal `ACTIVE` **de la misma empresa**.

**¿Cómo sabe que funcionó?** `201` con `UserBranchResponse` y `operational_access.allowed: true`. A partir de aquí el usuario ve la sucursal con `allowed: true` en `/me/operational-context`. Errores: `422 MEMBERSHIP_INACTIVE`, `422 BRANCH_INACTIVE`, `422 BRANCH_COMPANY_MISMATCH` (la sucursal es de otra empresa), `409 DUPLICATE_USER_BRANCH` (ya existe la asignación; si está inactiva, reactívala con OC 26 en lugar de crearla de nuevo).

## 13. Consultar usuarios asignados a una sucursal

**¿Qué API debe consumir el frontend?** `GET https://sio-operational-context-dev.onrender.com/api/v1/branches/{branch_id}/user-branches`. Permiso `perm:operational-context:user_branches:read`. Consulta: `page`, `page_size`, `status`. Responde `200` con `PaginatedResponse[UserBranchResponse]`. Útil para la pantalla de administración de una sucursal. Necesita [branch_id](../parametros/branch-id.md).

## 14 y 15. Cambiar el estado de una membresía

**¿Qué puede hacer el usuario?** Retirar temporal o definitivamente el acceso de una persona a la empresa, o devolvérselo.

**¿Qué API debe consumir el frontend?** `POST https://sio-operational-context-dev.onrender.com/api/v1/application-users/{application_user_id}/deactivate` (permiso `perm:operational-context:application_users:delete`) y `…/reactivate` (permiso `perm:operational-context:application_users:update`). Ambas `HIGH_RISK`, con cuerpo `{"version": n}`.

**¿Qué necesita antes?** [application_user_id](../parametros/application-user-id.md) y su `version` actual.

**¿Cómo sabe que funcionó?** `200` con `ApplicationUserResponse` y el nuevo `status`. Efectos verificados: con la membresía `INACTIVE`, todas las sucursales del usuario pasan a `allowed: false` con `reason: USER_MEMBERSHIP_INACTIVE` y las API de negocio le responden `404`/`403`; las asignaciones de sucursal se conservan y vuelven a ser efectivas al reactivar. Errores: `409 INVALID_STATUS_TRANSITION` (ya estaba en ese estado), `409 VERSION_CONFLICT`, `422 COMPANY_INACTIVE` al reactivar en una empresa inactiva.

## 16. Consultar la trazabilidad de la empresa (auditoría)

**¿Qué puede hacer el usuario?** Ver quién hizo qué y cuándo en la empresa: creación y confirmación de ventas y compras, cambios de líneas, recepciones, anulaciones, altas y cambios de clientes, proveedores, productos adoptados, precios, políticas, sucursales y membresías.

**¿Qué API debe consumir el frontend?** `GET https://sio-audit-dev.onrender.com/api/v1/companies/{company_id}/audit-events` ([Audit 5](../servicios/audit.md#5-get-companiescompany_idaudit-events)). Permiso `perm:audit:audit-events:read`. Consulta: `page`, `page_size` (1–100), `occurred_at_from`, `occurred_at_to` (con zona horaria), `result` (`SUCCESS`, `FAILURE`), `action`, `entity_type`, `entity_id`, `source_service`, `keycloak_user_id`, `application_user_id`, `event_id`, `correlation_id`, `request_id`, `branch_id`.

```bash
curl -sS 'https://sio-audit-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/audit-events?entity_type=Sale&action=CONFIRM_SALE&occurred_at_from=2026-10-01T00:00:00Z' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**¿Qué necesita antes?** Membresía `ACTIVE` en la empresa (Audit la comprueba en Operational Context en cada solicitud; sin ella responde `404`). Los filtros nunca amplían el alcance: solo se devuelven eventos de ese `company_id`.

**¿Cómo sabe que funcionó?** `200` con `PaginatedResponse[AuditEventResponse]`, ordenado del más reciente al más antiguo (`occurred_at` descendente). Cada evento trae `action`, `entity_type`, `entity_id`, `previous_values`, `new_values`, `redacted_paths[]`, `result`, `reason`, `application_user_id`, `keycloak_user_id`, `username_snapshot`, `branch_id`, `source_service`, `correlation_id`, `request_id`, `occurred_at`. Un evento concreto: `GET https://sio-audit-dev.onrender.com/api/v1/companies/{company_id}/audit-events/{audit_id}` ([Audit 6](../servicios/audit.md#6-get-companiescompany_idaudit-eventsaudit_id)).

Valores de `entity_type` y `action` que emiten hoy los servicios (verificados en el código de cada emisor; Audit solo valida el formato):

| Servicio emisor (`source_service`) | `entity_type` | `action` |
|---|---|---|
| Sales | `Sale`, `SaleDetail`, `SaleSequence` | `CREATE_SALE`, `UPDATE_SALE`, `ADD_SALE_DETAIL`, `UPDATE_SALE_DETAIL`, `DELETE_SALE_DETAIL`, `CONFIRM_SALE`, `CANCEL_SALE`, `CREATE_SALE_SEQUENCE`, `UPDATE_SALE_SEQUENCE`, `DEACTIVATE_SALE_SEQUENCE`, `REACTIVATE_SALE_SEQUENCE` |
| Purchase | `Purchase`, `PurchaseDetail`, `PurchaseLifecycleEvent`, `PurchaseSequence` | `CREATE_PURCHASE`, `UPDATE_PURCHASE`, `ADD_PURCHASE_DETAIL`, `UPDATE_PURCHASE_DETAIL`, `DELETE_PURCHASE_DETAIL`, `CONFIRM_PURCHASE`, `CANCEL_PURCHASE`, `RECEIVE_PURCHASE`, `RECORD_PURCHASE_LIFECYCLE_EVENT`, `CREATE_PURCHASE_SEQUENCE`, `UPDATE_PURCHASE_SEQUENCE`, `DEACTIVATE_PURCHASE_SEQUENCE`, `REACTIVATE_PURCHASE_SEQUENCE`, `OVERRIDE_PURCHASE_LINE_TAX` |
| Commercial Relationship | `CompanyCustomer`, `CompanySupplier`, `CompanyProduct`, `CompanyProductPresentation`, `PriceList`, `PriceListItem`, `PricingPolicy` | `CREATE_/UPDATE_/DEACTIVATE_/REACTIVATE_COMPANY_CUSTOMER`, `…_COMPANY_SUPPLIER` (más `BLOCK_`/`UNBLOCK_`), `ADOPT_COMPANY_PRODUCT`, `…_COMPANY_PRODUCT_PRESENTATION`, `…_SUPPLIER_PRODUCT`, `…_SUPPLIER_PAYMENT_CONDITION`, `…_PRICE_LIST`, `…_PRICE_LIST_ITEM`, `CHANGE_PRICE_LIST_ITEM_PRICE`, `CREATE_/UPDATE_PRICING_POLICY`, `CHANGE_PRICING_POLICY_PERCENTAGE`, `ASSIGN_/UNASSIGN_PRICING_POLICY_PRESENTATION` |
| Operational Context | `Company`, `Branch`, `ApplicationUser`, `UserBranch`, `CompanyAdvisorAssignment` | Altas, modificaciones y cambios de estado de esas entidades |
| Inventory | `InventoryAdjustment`, `InventoryCount`, `InventoryOperation` | `CREATE_INVENTORY_ADJUSTMENT` y las transiciones de conteos y operaciones |

Los eventos del catálogo global de Product Catalog (`Product`, `ProductPresentation`, `ProductIdentifier`, …) no pertenecen a una empresa: se consultan en `GET https://sio-audit-dev.onrender.com/api/v1/platform-audit-events` con `perm:audit:platform-events:read` (Audit 8–10), reservado a la administración de la plataforma.

## 17. Consultar el historial de una venta, una compra o un producto

**¿Qué puede hacer el usuario?** Abrir la línea de tiempo completa de un documento o de un registro de la empresa, en orden cronológico.

**¿Qué API debe consumir el frontend?** `GET https://sio-audit-dev.onrender.com/api/v1/companies/{company_id}/entity-history/{entity_type}/{entity_id}` ([Audit 7](../servicios/audit.md#7-get-companiescompany_identity-historyentity_typeentity_id); la ruta real cuelga de `/companies/{company_id}/entity-history/…`, no de `/audit-events/`). Permiso `perm:audit:audit-events:read`. `entity_type` va en PascalCase; consulta: `page`, `page_size`, `occurred_at_from`, `occurred_at_to`, `result`.

| Qué rastrear | `entity_type` | `entity_id` |
|---|---|---|
| Una venta (creación, líneas, confirmación, anulación) | `Sale` | [sale_id](../parametros/sale-id.md) |
| Una línea de venta | `SaleDetail` | `lines[].id` de la venta |
| Una compra (creación, líneas, confirmación, recepción, anulación, hitos) | `Purchase` | [purchase_id](../parametros/purchase-id.md) |
| Un producto adoptado por la empresa | `CompanyProduct` | [company_product_id](../parametros/company-product-id.md) |
| Una presentación de la empresa | `CompanyProductPresentation` | [company_product_presentation_id](../parametros/company-product-presentation-id.md) |
| Un precio, una lista o una política | `PriceListItem`, `PriceList`, `PricingPolicy` | su `id` |
| Un cliente o un proveedor | `CompanyCustomer`, `CompanySupplier` | [company_customer_id](../parametros/customer-id.md), [company_supplier_id](../parametros/supplier-id.md) |
| Una sucursal o una membresía | `Branch`, `ApplicationUser` | [branch_id](../parametros/branch-id.md), [application_user_id](../parametros/application-user-id.md) |

```bash
curl -sS 'https://sio-audit-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/entity-history/Sale/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**¿Cómo sabe que funcionó?** `200` con la misma paginación de eventos, en orden **ascendente** por `occurred_at` (del primero al último). Los eventos de inventario de una venta o compra no aparecen bajo `Sale`/`Purchase`: se consultan con `entity_type=InventoryOperation` y el `inventory_operation_id` del documento, o en el kardex ([Inventario §6](inventario.md#6-kardex-de-un-producto)). Un documento sin eventos responde `200` con `items: []`.

## Numeración de documentos comerciales

Las ventas y las compras reciben su número (`V-000123`, `C-000045`) al **confirmarse**, tomándolo de una **secuencia** del servicio correspondiente. Sin secuencia activa aplicable, la confirmación falla con `409 SEQUENCE_NOT_CONFIGURED`. Reglas verificadas (`sequence_service.py` y `sequence_repository.py` de Sales; Purchase es simétrico):

- Una secuencia pertenece a la empresa y, opcionalmente, a una sucursal (`branch_id`). Al confirmar se usa la secuencia **activa de la sucursal** del documento y, si no hay, la **activa de la empresa** (`branch_id: null`).
- A lo sumo **una secuencia activa** por empresa, sucursal (o ninguna) y tipo documental; activar otra en el mismo alcance responde `409 SEQUENCE_ALREADY_ACTIVE`.
- El número se compone de `prefix` + `separator` + consecutivo rellenado a `number_length` dígitos, desde `initial_number`, con reinicio `NEVER`, `YEARLY` o `MONTHLY` (`reset_policy`) y tope opcional `maximum_number` (`409 SEQUENCE_EXHAUSTED` al superarlo).
- Tras asignar el primer número, `prefix`, `separator`, `number_length`, `series_code`, `reset_policy`, `initial_number` y `branch_id` son inmutables (`409 SEQUENCE_IN_USE`); solo `maximum_number` puede ampliarse.

| # | Funcionalidad | Sales (base `https://sio-sales-dev.onrender.com/api/v1`) | Purchase (base `https://sio-purchase-dev.onrender.com/api/v1`) |
|---|---|---|---|
| 18 | Consultar las secuencias configuradas | `GET /companies/{company_id}/sale-sequences` · `perm:sales:sale_sequences:read` · [Sales 17](../servicios/sales.md#17-get-companiescompany_idsale-sequences) | `GET /companies/{company_id}/purchase-sequences` · `perm:purchase:purchase_sequences:read` · [Purchase 19](../servicios/purchase.md#19-get-companiescompany_idpurchase-sequences) |
| 19 | Crear una secuencia (queda activa) | `POST /companies/{company_id}/sale-sequences` · `perm:sales:sale_sequences:create` · [Sales 16](../servicios/sales.md#16-post-companiescompany_idsale-sequences) | `POST /companies/{company_id}/purchase-sequences` · `perm:purchase:purchase_sequences:create` · [Purchase 18](../servicios/purchase.md#18-post-companiescompany_idpurchase-sequences) |
| 20 | Desactivar o reactivar la secuencia activa | `POST …/sale-sequences/{sequence_id}/deactivate` · `…/reactivate` · `perm:sales:sale_sequences:update` · [Sales 20](../servicios/sales.md#20-post-companiescompany_idsale-sequencessequence_iddeactivate) · [Sales 21](../servicios/sales.md#21-post-companiescompany_idsale-sequencessequence_idreactivate) | `POST …/purchase-sequences/{sequence_id}/deactivate` · `…/reactivate` · `perm:purchase:purchase_sequences:update` · [Purchase 22](../servicios/purchase.md#22-post-companiescompany_idpurchase-sequencessequence_iddeactivate) · [Purchase 23](../servicios/purchase.md#23-post-companiescompany_idpurchase-sequencessequence_idreactivate) |
| 21 | Consultar y modificar una secuencia | `GET` · `PUT /companies/{company_id}/sale-sequences/{sequence_id}` · `perm:sales:sale_sequences:read` · `…:update` · [Sales 18](../servicios/sales.md#18-get-companiescompany_idsale-sequencessequence_id) · [Sales 19](../servicios/sales.md#19-put-companiescompany_idsale-sequencessequence_id) | `GET` · `PUT /companies/{company_id}/purchase-sequences/{sequence_id}` · `perm:purchase:purchase_sequences:read` · `…:update` · [Purchase 20](../servicios/purchase.md#20-get-companiescompany_idpurchase-sequencessequence_id) · [Purchase 21](../servicios/purchase.md#21-put-companiescompany_idpurchase-sequencessequence_id) |

### 18. Consultar las secuencias configuradas

`GET …/sale-sequences` y `GET …/purchase-sequences` (sin parámetros) responden `200` con `items[]`: `id` (`sequence_id`), `branch_id` (`null` = secuencia de la empresa), `document_kind` (`SALE` / `PURCHASE`), `series_code`, `prefix`, `separator`, `initial_number`, `maximum_number`, `number_length`, `reset_policy`, `is_active`, `version` y `counters[]` (`period_key`, `current_number`, `next_number_preview`). Es la pantalla de configuración: muestra qué sucursales tienen secuencia propia, cuál es la de la empresa y cuál será el próximo número.

### 19. Crear una secuencia

`POST https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sale-sequences` (o `…/purchase-sequences` en Purchase). Cuerpo `SequenceIn`:

```json
{
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "series_code": "POS-01",
  "prefix": "V",
  "separator": "-",
  "initial_number": 1,
  "maximum_number": 999999,
  "number_length": 6,
  "reset_policy": "NEVER"
}
```

`branch_id` en `null` (u omitido) crea la secuencia de la empresa, que sirve de respaldo a todas las sucursales sin secuencia propia; `separator` admite `-`, `/`, `.`, `_` o vacío. Responde `201` con la secuencia (`is_active: true`). Errores: `409 SEQUENCE_ALREADY_ACTIVE` (ya hay una activa en ese alcance: desactívala primero o modifica la existente), `422 VALIDATION_ERROR`, `404` si la sucursal no es de la empresa.

### 20. Desactivar o reactivar la secuencia activa

`POST …/{sequence_id}/deactivate` (`HIGH_RISK`: desde ese momento las confirmaciones de ese alcance fallan con `409 SEQUENCE_NOT_CONFIGURED`, salvo que exista la secuencia de respaldo de la empresa) y `POST …/{sequence_id}/reactivate`, ambos con `{"version": n}`. Responden `200` con la secuencia y su nuevo `is_active`. Reactivar una secuencia cuando otra ya está activa en el mismo alcance responde `409 SEQUENCE_ALREADY_ACTIVE`. Los contadores no se reinician al desactivar y reactivar.

### 21. Consultar y modificar una secuencia

`GET …/{sequence_id}` devuelve la secuencia con sus contadores. `PUT …/{sequence_id}` (`SequenceUpdateIn`: los mismos campos de la creación más `version`) permite ajustar el formato **solo mientras no se haya asignado ningún número**; después únicamente `maximum_number` (`409 SEQUENCE_IN_USE` en caso contrario, `409 VERSION_CONFLICT` si la versión no es la actual).

### Requisitos previos para confirmar documentos

| Documento | Requisito | Dónde se verifica |
|---|---|---|
| Venta y compra | Secuencia activa de la sucursal **o** de la empresa para ese tipo documental | Funcionalidad 18 (`is_active: true` y `branch_id` igual al de la sucursal o `null`) |
| Venta y compra | Sucursal asignada al usuario que confirma | Funcionalidad 12 de este módulo ([Acceso y contexto operativo](acceso-y-contexto-operativo.md)) |
| Venta | Existencias y precios vigentes | [Ventas](ventas.md) |
| Compra | Impuesto de compra y política de ganancia por presentación | [Compras](compras.md) |

**Cómo resolver `409 SEQUENCE_NOT_CONFIGURED`:** (1) consultar las secuencias (funcionalidad 18) y comprobar si existe una para la `branch_id` del documento o una de empresa (`branch_id: null`) con `is_active: true`; (2) si existe pero está inactiva, reactivarla (funcionalidad 20); (3) si no existe, crearla (funcionalidad 19) con los permisos `perm:sales:sale_sequences:create` o `perm:purchase:purchase_sequences:create` (grupos `administradores` y `supervisores` en el realm de desarrollo); (4) repetir la confirmación con la misma `Idempotency-Key` y la `version` actual del documento. No hace falta recrear el borrador.

## Orden recomendado y efectos automáticos

1. Identidad de la organización (Party Identity) → 2. Empresa (OC 4) → 3. Sucursales (OC 10) → 4. Identidad de cada persona (Party Identity) → 5. Membresía (OC 16) → 6. Asignación de sucursales (OC 22).

Ningún paso crea automáticamente el siguiente: crear la empresa no crea sucursales ni membresías; crear la membresía no asigna sucursales. Las secuencias de numeración de ventas y compras tampoco se crean solas y son obligatorias para confirmar documentos (funcionalidades 18 a 21). El ejemplo [Crear una empresa y una sucursal](../ejemplos/crear-empresa-y-sucursal.md) recorre la cadena completa con cuerpos y respuestas reales.

## Dependencias con otros módulos

- [Acceso y contexto operativo](acceso-y-contexto-operativo.md) refleja al instante las membresías y asignaciones creadas aquí.
- [Gestión de clientes](gestion-de-clientes.md) y [Gestión de proveedores](gestion-de-proveedores.md) usan las mismas identidades de Party Identity que este módulo.
- Sales, Purchase e Inventory exigen que el usuario tenga asignada la sucursal sobre la que opera (`403 BRANCH_ACCESS_DENIED` en caso contrario).
