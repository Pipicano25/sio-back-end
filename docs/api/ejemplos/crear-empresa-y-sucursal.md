# Crear una empresa, una sucursal y sus usuarios

[← Flujos](README.md) · [← Índice](../index.md) · Fichas: [Operational Context](../servicios/operational-context.md), [Party Identity](../servicios/party-identity.md) · Módulo: [Administración empresarial](../principales/administracion-empresarial.md)

Alta completa de una empresa cliente de SIO hasta que su primer usuario puede operar en una sucursal. Perfil: administrador de la plataforma (`perm:operational-context:platform:administer`, grupo `administradores` en el realm de desarrollo). Identificadores ficticios; cuerpos y respuestas según los modelos reales.

**Orden y efectos verificados en el código de Operational Context:** cada paso es explícito. Crear la empresa **no** crea sucursales ni membresías; crear la membresía **no** asigna sucursales; crear la sucursal **no** asigna usuarios. Las secuencias de numeración de ventas y compras tampoco se crean solas.

## 1. Ubicación (Geography)

`GET https://sio-geography-dev.onrender.com/global-countries?iso2_code=CO` → `items[].id` (`country_id`); `GET …/global-administrative-divisions?country_id=…` → `administrative_division_id`; `GET …/global-cities?administrative_division_id=…&search=bogot` → `city_id` ([guía](../parametros/country-id.md)). Permisos `perm:geography:global_countries:read`, `…global_administrative_divisions:read`, `…global_cities:read`. Geography no usa el prefijo `/api/v1`.

## 2. Identidad de la organización (Party Identity)

Buscar primero: `GET https://sio-party-identity-dev.onrender.com/api/v1/organization-identities?search=900123456` (permiso `perm:party-identity:organization_identities:read`). Si no existe, crearla con `POST https://sio-party-identity-dev.onrender.com/api/v1/organization-identities` ([operación 10](../servicios/party-identity.md#10-post-organization-identities)); permiso `perm:party-identity:organization_identities:create`.

```json
{
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "NIT",
  "identification_number": "900123456",
  "legal_name": "Droguería La Economía S.A.S.",
  "organization_type": "SAS"
}
```

Respuesta `201` (`OrganizationIdentityResponse`; `id` es el [organization_identity_id](../parametros/organization-identity-id.md)):

```json
{
  "id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "NIT",
  "identification_number": "900123456",
  "legal_name": "Droguería La Economía S.A.S.",
  "trade_name": null,
  "organization_type": "SAS",
  "registration_status": "VIGENTE",
  "website": null,
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

`identification_type` e `identification_number` se validan con las reglas del país (`GET …/identification-type-rules?country_id=…&party_kind=ORGANIZATION`). Error `409` si ya existe una organización con ese documento: reutiliza su `id`.

## 3. Crear la empresa (Operational Context)

`POST https://sio-operational-context-dev.onrender.com/api/v1/companies` ([operación 4](../servicios/operational-context.md#4-post-companies)); permisos `perm:operational-context:companies:create` **y** `perm:operational-context:platform:administer`.

```json
{
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "email": "contacto@laeconomia.com",
  "phone": "+57 300 123 4567",
  "address_line": "Calle 10 # 5-20",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "latitude": "4.6097",
  "longitude": "-74.0817",
  "timezone": "America/Bogota",
  "default_currency": "COP"
}
```

Respuesta `201` (`CompanyResponse`; `id` es el [company_id](../parametros/company-id.md)):

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "email": "contacto@laeconomia.com",
  "phone": "+57 300 123 4567",
  "address_line": "Calle 10 # 5-20",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "postal_code": null,
  "latitude": "4.6097",
  "longitude": "-74.0817",
  "timezone": "America/Bogota",
  "default_currency": "COP",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

Efectos: la empresa queda `ACTIVE` sin sucursales ni usuarios. El administrador de plataforma la ve por `platform:administer`; nadie más la verá hasta el paso 6. Errores: `409 DUPLICATE_ORGANIZATION_IDENTITY` (la organización ya tiene empresa), `422 ORGANIZATION_IDENTITY_NOT_FOUND` / `_INACTIVE`, `422 GEOGRAPHY_INCOHERENT` / `CITY_NOT_FOUND` / `LOCATION_INACTIVE`, `503 DEPENDENCY_UNAVAILABLE`.

## 4. Crear la sucursal

`POST https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/branches` ([operación 10](../servicios/operational-context.md#10-post-companiescompany_idbranches)); permiso `perm:operational-context:branches:create`.

```json
{
  "code": "SUC-01",
  "name": "Sucursal Centro",
  "email": "centro@laeconomia.com",
  "phone": "+57 300 123 4567",
  "address_line": "Calle 10 # 5-20",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "latitude": "4.6097",
  "longitude": "-74.0817",
  "timezone": "America/Bogota"
}
```

Respuesta `201` (`BranchResponse`; `id` es el [branch_id](../parametros/branch-id.md)):

```json
{
  "id": "b361a654-58d4-422f-8ffe-9699a87e91e3",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "company_status": "ACTIVE",
  "code": "SUC-01",
  "name": "Sucursal Centro",
  "email": "centro@laeconomia.com",
  "phone": "+57 300 123 4567",
  "address_line": "Calle 10 # 5-20",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "postal_code": null,
  "latitude": "4.6097",
  "longitude": "-74.0817",
  "timezone": "America/Bogota",
  "effective_timezone": "America/Bogota",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

`effective_timezone` muestra la zona horaria propia o la heredada de la empresa. Errores: `409 DUPLICATE_BRANCH_CODE`, `422 COMPANY_INACTIVE`, `422` de geografía. Repite este paso por cada punto de operación.

## 5. Identidad de la persona (Party Identity)

Para cada usuario que trabajará en la empresa: buscar `GET https://sio-party-identity-dev.onrender.com/api/v1/person-identities?search=1012345678` o crear con `POST https://sio-party-identity-dev.onrender.com/api/v1/person-identities` ([operación 4](../servicios/party-identity.md#4-post-person-identities)); permiso `perm:party-identity:person_identities:create`.

```json
{
  "identification_country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "CC",
  "identification_number": "1012345678",
  "first_name": "Ana",
  "last_name": "Pérez",
  "verification_status": "VERIFIED"
}
```

Respuesta `201` (`PersonIdentityResponse`; `id` es el [person_identity_id](../parametros/person-identity-id.md)):

```json
{
  "id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "identification_country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "CC",
  "identification_number": "1012345678",
  "first_name": "Ana",
  "middle_name": null,
  "last_name": "Pérez",
  "second_last_name": null,
  "birth_date": null,
  "verification_status": "VERIFIED",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

## 6. Asociar el usuario a la empresa (membresía)

Requisito previo: la cuenta del usuario debe existir y estar habilitada en Keycloak, con los roles de `sio-api` de su función (eso se configura en Keycloak, no en estas API). Luego: `POST https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/application-users` ([operación 16](../servicios/operational-context.md#16-post-companiescompany_idapplication-users)); permiso `perm:operational-context:application_users:create`; `HIGH_RISK`.

```json
{
  "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "display_name": "Ana Pérez",
  "reference_email": "ana.perez@ejemplo.com"
}
```

Se envía **exactamente uno** de `keycloak_user_id` (el `sub` de Keycloak) o `username`. Respuesta `201` (`ApplicationUserResponse`; `id` es el [application_user_id](../parametros/application-user-id.md)):

```json
{
  "id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "company_status": "ACTIVE",
  "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "display_name": "Ana Pérez",
  "reference_email": "ana.perez@ejemplo.com",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

Efecto: desde ahora el usuario ve la empresa en `GET …/me/operational-context`, con `branches: []`. Errores: `422 KEYCLOAK_USER_NOT_FOUND` / `KEYCLOAK_USER_DISABLED` / `TECHNICAL_ACCOUNT_NOT_ALLOWED`, `422 PERSON_IDENTITY_NOT_FOUND` / `_INACTIVE`, `409 DUPLICATE_MEMBERSHIP`, `503 DEPENDENCY_UNAVAILABLE`.

## 7. Asignar la sucursal al usuario

`POST https://sio-operational-context-dev.onrender.com/api/v1/application-users/{application_user_id}/user-branches` ([operación 22](../servicios/operational-context.md#22-post-application-usersapplication_user_iduser-branches)); permiso `perm:operational-context:user_branches:create`; `HIGH_RISK`.

```json
{
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7"
}
```

Respuesta `201` (`UserBranchResponse`):

```json
{
  "id": "e8c5f9de-8af8-4aa7-8f96-536c03dc33ac",
  "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "assigned_at": "2026-10-19T15:04:05Z",
  "assigned_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "deactivated_at": null,
  "membership_status": "ACTIVE",
  "branch_status": "ACTIVE",
  "company_status": "ACTIVE",
  "operational_access": {
    "allowed": true,
    "reason": "Solicitud del cliente"
  },
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

`operational_access.allowed: true` confirma que el usuario ya puede operar en la sucursal. Errores: `422 BRANCH_COMPANY_MISMATCH` (sucursal de otra empresa), `422 BRANCH_INACTIVE`, `422 MEMBERSHIP_INACTIVE`, `409 DUPLICATE_USER_BRANCH`.

## 8. Verificar desde el usuario

Con el token del usuario recién asociado: `GET https://sio-operational-context-dev.onrender.com/api/v1/me/operational-context` debe mostrar la membresía con `status: "ACTIVE"` y la sucursal con `allowed: true`. Para una acción concreta: `GET …/operational-access?company_id=…&branch_id=…&permission=perm:sales:sales:create` → `allowed: true` ([Acceso y contexto operativo](../principales/acceso-y-contexto-operativo.md)).

## 9. Configuración mínima para operar

Antes de la primera venta o compra, la empresa necesita además:

| Configuración | Operación | Módulo |
|---|---|---|
| Secuencia de numeración de ventas | `POST https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sale-sequences` (Sales 16) | [Ventas](../principales/ventas.md) |
| Secuencia de numeración de compras | `POST https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchase-sequences` (Purchase 18) | [Compras](../principales/compras.md) |
| Productos adoptados con presentaciones e impuesto de compra | Commercial Relationship 4, 27, 11 | [Productos y precios](../principales/productos-y-precios.md) |
| Lista de precios y política de ganancia | Commercial Relationship 47, 62 | [Configurar una lista de precios](configurar-lista-precios.md) |
| Clientes y proveedores | Commercial Relationship 14, 20 | [Gestión de clientes](../principales/gestion-de-clientes.md), [Gestión de proveedores](../principales/gestion-de-proveedores.md) |
