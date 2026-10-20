# Permisos y contexto operativo

[← Volver al índice](../index.md) · [Autenticación](autenticacion.md) · [Primeros pasos](primeros-pasos.md) · [Errores](errores.md) · [Operational Context](../servicios/operational-context.md)

Para que una operación de SIO se ejecute deben cumplirse **dos condiciones independientes**:

1. **Permiso funcional**: el Access Token incluye un permiso `perm:*` que cubre el exigido por la operación. Lo evalúa cada microservicio con la librería común `sio-auth`. Si falta, responde `403`.
2. **Alcance de datos**: el usuario tiene acceso a la empresa (y, cuando aplica, a la sucursal) de la ruta. Lo evalúa el servicio consultando Operational Context. Si falta, responde normalmente `404`, igual que si el recurso no existiera.

Esta guía explica ambas condiciones, los grupos del realm y cómo prever desde el frontend qué puede hacer cada usuario.

## 1. Dónde están los permisos

En el Access Token, dentro de `resource_access["sio-api"].roles`. No hay otro claim con permisos: no uses `realm_access`, `groups` ni el ID Token.

```json
{
  "resource_access": {
    "sio-api": {
      "roles": [
        "inventario",
        "perm:inventory:balances:read",
        "perm:inventory:adjustments:create",
        "perm:geography:all:read",
        "perm:operational-context:all:read"
      ]
    }
  }
}
```

- Los valores sin prefijo (`administrador`, `supervisor`, `compras`, `ventas`, `inventario`, `reportes`, `consulta`) son el **perfil** del grupo: sirven para mostrar el rol del usuario, no conceden nada.
- Solo cuentan los valores con formato exacto `perm:{servicio}:{recurso}:{accion}` (cuatro segmentos). Un `perm:` con otro número de segmentos se ignora.
- Los roles son los **efectivos** de `sio-api`: los de los grupos del usuario más los asignados directamente.

## 2. Formato y evaluación

`perm:{servicio}:{recurso}:{accion}`. Cada segmento admite letras minúsculas, dígitos, `_` y `-`. El valor `all` es comodín en cualquiera de los tres segmentos.

Un permiso del token **cubre** al que exige una operación cuando cada segmento coincide o vale `all`. Es exactamente la regla de `SioGrant.allows` en `libs/sio-auth`:

```ts
const concede = (grant: string, servicio: string, recurso: string, accion: string) => {
  const p = grant.split(":");
  return p.length === 4 && p[0] === "perm"
    && [servicio, "all"].includes(p[1])
    && [recurso, "all"].includes(p[2])
    && [accion, "all"].includes(p[3]);
};

export const puede = (roles: string[], servicio: string, recurso: string, accion: string) =>
  roles.some((g) => concede(g, servicio, recurso, accion));
```

| Permiso en el token | Cubre |
|---|---|
| `perm:all:all:all` | Todo (grupo administradores) |
| `perm:all:all:read` | Toda consulta de cualquier servicio |
| `perm:inventory:all:read` (ejemplo de comodín por servicio; no está definido en la plantilla) | Toda consulta de Inventory |
| `perm:sales:sales:create` | Solo crear ventas |
| `perm:operational-context:all:read` | Todas las lecturas de Operational Context, incluido `/me/operational-context` |

**Acciones especiales.** Algunas acciones no son CRUD y los comodines `read`, `create`, `update` o `delete` **no** las cubren; solo las cubre el permiso exacto o un comodín con acción `all` (`perm:all:all:all`, `perm:{servicio}:all:all`). Ejemplos verificados en el código: `perm:operational-context:platform:administer`, `perm:operational-context:platform:lookup`, `perm:sales:sales:read-profitability`, `perm:purchase:purchase_line_taxes:override`, `perm:commercial-relationship:automatic_price_applications:resolve`, `perm:commercial-relationship:automatic_price_update_requests:submit`, `perm:product-catalog:first-use:register`.

## 3. Nombres de servicio usados en los permisos

| Servicio | Segmento `servicio` | Permisos definidos en el realm |
|---|---|---|
| Geography | `geography` | 17 |
| Party Identity | `party-identity` | 41 |
| Product Catalog | `product-catalog` | 64 |
| Operational Context | `operational-context` | 27 |
| Payment Reference | `payment-reference` | 13 |
| Commercial Relationship | `commercial-relationship` | 71 |
| Purchase | `purchase` | 26 |
| Sales | `sales` | 22 |
| Inventory | `inventory` | 15 |
| Audit | `audit` | 3 |
| Product Inventory Query | `product-inventory-query` | 6 |
| Business Reporting | `business-reporting` | 4 |
| Comodines | `all` | 5 (`perm:all:all:all`, `perm:all:all:read`, `perm:all:all:create`, `perm:all:all:update`, `perm:all:all:delete`) |

El realm define 316 roles `perm:*` en total. El permiso exacto de cada operación figura en la ficha del servicio, verificado contra el código del router.

> **Observación:** los grupos `reportes` y `consulta` incluyen además dos permisos con el segmento `payment_reference` (guion bajo). El servicio Payment Reference declara sus permisos con `payment-reference` (guion), por lo que esos dos valores **no conceden nada**; los permisos efectivos son los escritos con guion, que también están presentes en ambos grupos.

## 4. Grupos del realm y sus permisos

Los grupos y permisos provienen de la plantilla del realm del repositorio (`infrastructure/keycloak/realm-template/sio-realm.template.json`). **NO VERIFICADO:** que el realm `siodev` de Render tenga exactamente esta asignación; un administrador puede haber añadido o retirado permisos. El frontend debe leer siempre los permisos reales del token.

### Grupo `/administradores` (rol `administrador`, usuario de prueba `admin.test`)

1 permisos `perm:*`.

| Servicio | Permisos |
|---|---|
| `all` | `perm:all:all:all` |

### Grupo `/supervisores` (rol `supervisor`, usuario de prueba `supervisor.test`)

7 permisos `perm:*`.

| Servicio | Permisos |
|---|---|
| `all` | `perm:all:all:read`, `perm:all:all:create`, `perm:all:all:update` |
| `sales` | `perm:sales:sales:read-profitability` |
| `commercial-relationship` | `perm:commercial-relationship:pricing_policies:delete`, `perm:commercial-relationship:automatic_price_applications:resolve` |
| `purchase` | `perm:purchase:purchase_line_taxes:override` |

### Grupo `/compras` (rol `compras`, usuario de prueba `compras.test`)

47 permisos `perm:*`.

| Servicio | Permisos |
|---|---|
| `purchase` | `perm:purchase:purchases:create`, `perm:purchase:purchases:read`, `perm:purchase:purchases:update`, `perm:purchase:purchases:delete`, `perm:purchase:purchase_details:create`, `perm:purchase:purchase_details:read`, `perm:purchase:purchase_details:update`, `perm:purchase:purchase_details:delete`, `perm:purchase:purchase_lifecycle_events:create`, `perm:purchase:purchase_lifecycle_events:read`, `perm:purchase:purchase_lifecycle_events:update`, `perm:purchase:purchase_lifecycle_events:delete`, `perm:purchase:purchase_sequences:create`, `perm:purchase:purchase_sequences:read`, `perm:purchase:purchase_sequences:update`, `perm:purchase:purchase_sequences:delete`, `perm:purchase:purchase_operations:create`, `perm:purchase:purchase_operations:read`, `perm:purchase:purchase_operations:update`, `perm:purchase:purchase_operations:delete` |
| `geography` | `perm:geography:all:read` |
| `payment-reference` | `perm:payment-reference:all:read` |
| `product-catalog` | `perm:product-catalog:all:read` |
| `party-identity` | `perm:party-identity:identification_type_rules:read`, `perm:party-identity:person_identities:read`, `perm:party-identity:organization_identities:read`, `perm:party-identity:person_contact_profiles:read`, `perm:party-identity:organization_contact_profiles:read`, `perm:party-identity:organization_contact_persons:read`, `perm:party-identity:global_business_sectors:read`, `perm:party-identity:organization_business_sectors:read` |
| `commercial-relationship` | `perm:commercial-relationship:company_products:read`, `perm:commercial-relationship:product_pricing_policies:read`, `perm:commercial-relationship:customer_segments:read`, `perm:commercial-relationship:company_customers:read`, `perm:commercial-relationship:customer_credit_profiles:read`, `perm:commercial-relationship:customer_payment_conditions:read`, `perm:commercial-relationship:company_suppliers:read`, `perm:commercial-relationship:supplier_commercial_conditions:read`, `perm:commercial-relationship:supplier_payment_conditions:read`, `perm:commercial-relationship:supplier_products:read`, `perm:commercial-relationship:company_product_presentations:read`, `perm:commercial-relationship:price_lists:read`, `perm:commercial-relationship:price_list_items:read`, `perm:commercial-relationship:supplier_evaluations:read` |
| `operational-context` | `perm:operational-context:all:read` |
| `business-reporting` | `perm:business-reporting:purchases:read` |

### Grupo `/ventas` (rol `ventas`, usuario de prueba `ventas.test`)

34 permisos `perm:*`.

| Servicio | Permisos |
|---|---|
| `sales` | `perm:sales:all:create`, `perm:sales:all:read`, `perm:sales:all:update`, `perm:sales:all:delete` |
| `geography` | `perm:geography:all:read` |
| `payment-reference` | `perm:payment-reference:all:read` |
| `product-catalog` | `perm:product-catalog:all:read` |
| `party-identity` | `perm:party-identity:identification_type_rules:read`, `perm:party-identity:person_identities:read`, `perm:party-identity:organization_identities:read`, `perm:party-identity:person_contact_profiles:read`, `perm:party-identity:organization_contact_profiles:read`, `perm:party-identity:organization_contact_persons:read`, `perm:party-identity:global_business_sectors:read`, `perm:party-identity:organization_business_sectors:read` |
| `commercial-relationship` | `perm:commercial-relationship:company_products:read`, `perm:commercial-relationship:product_pricing_policies:read`, `perm:commercial-relationship:customer_segments:read`, `perm:commercial-relationship:company_customers:read`, `perm:commercial-relationship:customer_credit_profiles:read`, `perm:commercial-relationship:customer_payment_conditions:read`, `perm:commercial-relationship:company_suppliers:read`, `perm:commercial-relationship:supplier_commercial_conditions:read`, `perm:commercial-relationship:supplier_payment_conditions:read`, `perm:commercial-relationship:supplier_products:read`, `perm:commercial-relationship:company_product_presentations:read`, `perm:commercial-relationship:price_lists:read`, `perm:commercial-relationship:price_list_items:read`, `perm:commercial-relationship:supplier_evaluations:read` |
| `operational-context` | `perm:operational-context:all:read` |
| `product-inventory-query` | `perm:product-inventory-query:product_overviews:read`, `perm:product-inventory-query:inventory_overviews:read`, `perm:product-inventory-query:stock:read` |
| `business-reporting` | `perm:business-reporting:top_selling_products:read` |

### Grupo `/inventario` (rol `inventario`, usuario de prueba `inventario.test`)

20 permisos `perm:*`.

| Servicio | Permisos |
|---|---|
| `geography` | `perm:geography:all:read` |
| `product-catalog` | `perm:product-catalog:all:read` |
| `operational-context` | `perm:operational-context:all:read` |
| `inventory` | `perm:inventory:balances:read`, `perm:inventory:movements:read`, `perm:inventory:adjustments:create`, `perm:inventory:counts:create`, `perm:inventory:adjustments:read`, `perm:inventory:counts:read`, `perm:inventory:company-policies:read`, `perm:inventory:product-policies:read`, `perm:inventory:valuation:read`, `perm:inventory:stock_evolution:read` |
| `commercial-relationship` | `perm:commercial-relationship:company_products:read` |
| `product-inventory-query` | `perm:product-inventory-query:product_overviews:read`, `perm:product-inventory-query:inventory_overviews:read`, `perm:product-inventory-query:inventory_summary:read`, `perm:product-inventory-query:low_stock_products:read`, `perm:product-inventory-query:stock:read` |
| `business-reporting` | `perm:business-reporting:stock_evolution:read` |

### Grupo `/reportes` (rol `reportes`, usuario de prueba `reportes.test`)

59 permisos `perm:*`.

| Servicio | Permisos |
|---|---|
| `commercial-relationship` | `perm:commercial-relationship:company_customers:read`, `perm:commercial-relationship:company_products:read`, `perm:commercial-relationship:company_suppliers:read`, `perm:commercial-relationship:customer_credit_profiles:read`, `perm:commercial-relationship:customer_payment_conditions:read`, `perm:commercial-relationship:customer_segments:read`, `perm:commercial-relationship:product_pricing_policies:read`, `perm:commercial-relationship:supplier_commercial_conditions:read`, `perm:commercial-relationship:supplier_evaluations:read`, `perm:commercial-relationship:supplier_payment_conditions:read`, `perm:commercial-relationship:supplier_products:read`, `perm:commercial-relationship:company_product_presentations:read`, `perm:commercial-relationship:price_lists:read`, `perm:commercial-relationship:price_list_items:read` |
| `geography` | `perm:geography:global_administrative_divisions:read`, `perm:geography:global_cities:read`, `perm:geography:global_countries:read` |
| `operational-context` | `perm:operational-context:application_users:read`, `perm:operational-context:branches:read`, `perm:operational-context:companies:read`, `perm:operational-context:company_advisor_assignments:read`, `perm:operational-context:user_branches:read` |
| `party-identity` | `perm:party-identity:global_business_sectors:read`, `perm:party-identity:identification_type_rules:read`, `perm:party-identity:organization_business_sectors:read`, `perm:party-identity:organization_identities:read`, `perm:party-identity:person_identities:read` |
| `payment-reference` | `perm:payment-reference:global_payment_condition_types:read`, `perm:payment-reference:global_payment_methods:read` |
| `product-catalog` | `perm:product-catalog:attribute-definitions:read`, `perm:product-catalog:brands:read`, `perm:product-catalog:categories:read`, `perm:product-catalog:global_categories:read`, `perm:product-catalog:global_category_attributes:read`, `perm:product-catalog:global_product_attribute_values:read`, `perm:product-catalog:global_products:read`, `perm:product-catalog:global_units_of_measure:read`, `perm:product-catalog:group-types:read`, `perm:product-catalog:packaging-types:read`, `perm:product-catalog:product_assets:read`, `perm:product-catalog:product_attribute_definitions:read`, `perm:product-catalog:products:read`, `perm:product-catalog:units-of-measure:read` |
| `purchase` | `perm:purchase:purchase_details:read`, `perm:purchase:purchase_lifecycle_events:read`, `perm:purchase:purchase_operations:read`, `perm:purchase:purchase_sequences:read`, `perm:purchase:purchases:read` |
| `sales` | `perm:sales:sale_details:read`, `perm:sales:sale_operations:read`, `perm:sales:sale_sequences:read`, `perm:sales:sales:read` |
| `payment_reference` | `perm:payment_reference:global_payment_condition_types:read`, `perm:payment_reference:global_payment_methods:read` |
| `inventory` | `perm:inventory:stock_evolution:read` |
| `business-reporting` | `perm:business-reporting:top_selling_products:read`, `perm:business-reporting:sales_by_branch:read`, `perm:business-reporting:purchases:read`, `perm:business-reporting:stock_evolution:read` |

### Grupo `/consulta` (rol `consulta`, usuario de prueba `consulta.test`)

54 permisos `perm:*`.

| Servicio | Permisos |
|---|---|
| `commercial-relationship` | `perm:commercial-relationship:company_customers:read`, `perm:commercial-relationship:company_products:read`, `perm:commercial-relationship:company_suppliers:read`, `perm:commercial-relationship:customer_credit_profiles:read`, `perm:commercial-relationship:customer_payment_conditions:read`, `perm:commercial-relationship:customer_segments:read`, `perm:commercial-relationship:product_pricing_policies:read`, `perm:commercial-relationship:supplier_commercial_conditions:read`, `perm:commercial-relationship:supplier_evaluations:read`, `perm:commercial-relationship:supplier_payment_conditions:read`, `perm:commercial-relationship:supplier_products:read`, `perm:commercial-relationship:company_product_presentations:read`, `perm:commercial-relationship:price_lists:read`, `perm:commercial-relationship:price_list_items:read` |
| `geography` | `perm:geography:global_administrative_divisions:read`, `perm:geography:global_cities:read`, `perm:geography:global_countries:read` |
| `operational-context` | `perm:operational-context:application_users:read`, `perm:operational-context:branches:read`, `perm:operational-context:companies:read`, `perm:operational-context:company_advisor_assignments:read`, `perm:operational-context:user_branches:read` |
| `party-identity` | `perm:party-identity:global_business_sectors:read`, `perm:party-identity:identification_type_rules:read`, `perm:party-identity:organization_business_sectors:read`, `perm:party-identity:organization_identities:read`, `perm:party-identity:person_identities:read` |
| `payment-reference` | `perm:payment-reference:global_payment_condition_types:read`, `perm:payment-reference:global_payment_methods:read` |
| `product-catalog` | `perm:product-catalog:attribute-definitions:read`, `perm:product-catalog:brands:read`, `perm:product-catalog:categories:read`, `perm:product-catalog:global_categories:read`, `perm:product-catalog:global_category_attributes:read`, `perm:product-catalog:global_product_attribute_values:read`, `perm:product-catalog:global_products:read`, `perm:product-catalog:global_units_of_measure:read`, `perm:product-catalog:group-types:read`, `perm:product-catalog:packaging-types:read`, `perm:product-catalog:product_assets:read`, `perm:product-catalog:product_attribute_definitions:read`, `perm:product-catalog:products:read`, `perm:product-catalog:units-of-measure:read` |
| `purchase` | `perm:purchase:purchase_details:read`, `perm:purchase:purchase_lifecycle_events:read`, `perm:purchase:purchase_operations:read`, `perm:purchase:purchase_sequences:read`, `perm:purchase:purchases:read` |
| `sales` | `perm:sales:sale_details:read`, `perm:sales:sale_operations:read`, `perm:sales:sale_sequences:read`, `perm:sales:sales:read` |
| `payment_reference` | `perm:payment_reference:global_payment_condition_types:read`, `perm:payment_reference:global_payment_methods:read` |

## 5. Alcance de datos: plataforma, empresa y sucursal

SIO es multi-tenant. Cada operación de esta documentación indica su **alcance**:

| Alcance | Datos | Quién puede verlos | Servicios |
|---|---|---|---|
| **Global** | Catálogos compartidos por todas las empresas: países, ciudades, productos del catálogo global, marcas, unidades, tipos de identificación, tipos de condición de pago | Cualquier usuario con el permiso de lectura; la escritura suele requerir permisos de catálogo que solo tienen administradores y supervisores | Geography, Payment Reference, Product Catalog, Party Identity (catálogos), Audit (eventos de plataforma) |
| **Empresa** | Datos de una empresa cliente de SIO: clientes, proveedores, productos adoptados, precios, compras, ventas, existencias, usuarios de aplicación, reportes | Usuarios con **membresía `ACTIVE`** en esa empresa y el permiso funcional; además, los administradores de plataforma | Operational Context, Commercial Relationship, Purchase, Sales, Inventory, Audit, Product Inventory Query, Business Reporting |
| **Sucursal** | Subconjunto de los datos de empresa asociado a una sucursal: existencias, ventas, compras y reportes por sucursal | Usuarios con acceso a esa sucursal (`user_branches` activo) dentro de la membresía | Inventory, Sales, Purchase, Product Inventory Query, Business Reporting |

### 5.1. Cómo se decide el alcance

Operational Context es la **única fuente** de membresías. Al recibir una solicitud sobre `/companies/{company_id}/…`, cada servicio de negocio:

1. Valida el token y el permiso funcional (`sio-auth`).
2. Consulta a Operational Context `GET /api/v1/operational-access?company_id=…` (y `branch_id` cuando aplica) **con el mismo token del usuario**.
3. Si la respuesta es `allowed: true`, continúa. Si es `allowed: false`, responde `404` (la empresa o sucursal «no existe» para ese usuario) o, en Purchase, Sales, Inventory, Commercial Relationship y Audit, un `403` con `code` `OPERATIONAL_ACCESS_DENIED` o `BRANCH_ACCESS_DENIED` según el caso documentado en cada ficha.

Consecuencias prácticas:

- El usuario necesita el permiso `perm:operational-context:application_users:read` (o un comodín que lo cubra) para que esa consulta interna funcione. Todos los grupos de la plantilla lo incluyen. Si se retira, las operaciones de empresa fallan con `403` `OPERATIONAL_ACCESS_DENIED` aunque el usuario tenga el permiso funcional.
- Dentro de Operational Context, el alcance se calcula en cada solicitud a partir de las membresías `ACTIVE` del `sub` del token. Fuera de alcance, responde `404` con el mismo mensaje que un UUID inexistente. Así no se puede enumerar empresas ajenas.
- Un `404` en una ruta de empresa puede significar «no existe» o «no tienes membresía». El frontend debe revisar primero el contexto operativo antes de concluir que el recurso no existe.

### 5.2. Capacidades de plataforma

Dos permisos de Operational Context amplían el alcance sin necesidad de membresía:

| Permiso | Efecto | Quién lo tiene en la plantilla |
|---|---|---|
| `perm:operational-context:platform:administer` | Ve y administra **todas** las empresas y sucursales | Solo quien tenga `perm:all:all:all` (administradores) |
| `perm:operational-context:platform:lookup` | Lecturas por UUID de empresas y sucursales sin membresía; pensado para identidades técnicas entre servicios | Cuentas de servicio técnicas; también cubierto por `perm:all:all:all` |

## 6. Comprobar el acceso antes de actuar

Operational Context expone una consulta que devuelve el resultado de la evaluación **sin producir `403`** por una denegación funcional:

```http
GET https://sio-operational-context-dev.onrender.com/api/v1/operational-access?company_id=550e8400-e29b-41d4-a716-446655440000&branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7&permission=perm:sales:sales:create
Authorization: Bearer <ACCESS_TOKEN>
```

| Parámetro de consulta | Tipo | Obligatorio | Significado |
|---|---|---|---|
| `company_id` | UUID | No | Empresa a evaluar ([cómo obtenerlo](../parametros/company-id.md)) |
| `branch_id` | UUID | No | Sucursal a evaluar ([cómo obtenerlo](../parametros/branch-id.md)) |
| `permission` | string (máx. 255) | No | Permiso concreto `perm:{servicio}:{recurso}:{accion}` a evaluar junto con el alcance |
| `keycloak_user_id` | string (máx. 255) | No | Solo con `perm:operational-context:platform:lookup`: evalúa a otro usuario |

Permiso exigido: `perm:operational-context:application_users:read`.

Respuesta `200` (modelo `OperationalAccessResponse`; valores ilustrativos):

```json
{
  "allowed": false,
  "reason": "USER_BRANCH_INACTIVE",
  "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "permission": "perm:sales:sales:create"
}
```

`reason` es `null` cuando `allowed` es `true`. Cuando es `false`, contiene la **primera** condición que falla, en este orden fijo (catálogo cerrado `AccessDenialReason` del código de Operational Context):

| `reason` | Significado |
|---|---|
| `USER_NOT_MEMBER` | El usuario no tiene membresía en la empresa |
| `USER_MEMBERSHIP_INACTIVE` | Tiene membresía, pero está `INACTIVE` |
| `COMPANY_INACTIVE` | La empresa está `INACTIVE` |
| `BRANCH_INACTIVE` | La sucursal consultada está `INACTIVE` |
| `BRANCH_NOT_ASSIGNED` | El usuario no tiene asignada esa sucursal |
| `USER_BRANCH_INACTIVE` | La asignación a la sucursal está `INACTIVE` |
| `PERMISSION_DENIED` | Todo lo anterior se cumple, pero el token no cubre el `permission` indicado |

El detalle de la operación está en la ficha de [Operational Context](../servicios/operational-context.md). Esta consulta es útil para decidir qué mostrar al cambiar de empresa o sucursal; la autorización definitiva la sigue haciendo cada operación.

## 7. Uso de los permisos en la interfaz

- **Permiso por elemento**: cada módulo, menú o botón usa el mismo permiso que declara la operación que invoca (columna «Permiso» de las fichas). No inventes permisos de interfaz.
- **Módulo**: se muestra si el usuario tiene al menos uno de los permisos de sus pantallas.
- **Acción**: el botón se muestra o habilita solo con el permiso de su operación.
- **Recalcular tras renovar**: los permisos pueden cambiar entre un token y el siguiente. Vuelve a leerlos después de cada renovación.
- **Perfil del usuario**: para mostrar «Ventas» o «Supervisor» usa el rol sin prefijo del token; no lo uses para decidir permisos.
- **Respuestas del servidor**: un `403` significa que el permiso cambió o no alcanza; informa con el `trace_id` y recalcula la interfaz. Un `404` de empresa o sucursal significa, con frecuencia, que no hay membresía.

Ejemplo de uso con el helper de §2:

```ts
const roles: string[] = tokenPayload.resource_access?.["sio-api"]?.roles ?? [];

const puedeCrearVenta = puede(roles, "sales", "sales", "create");
const puedeVerInventario = puede(roles, "inventory", "balances", "read");
const esAdministrador = puede(roles, "all", "all", "all");
```

## 8. Errores relacionados

| Situación | HTTP | Cuerpo |
|---|---|---|
| Token sin el permiso de la operación | `403` | `detail` fijo que no revela el permiso ([Autenticación §8.2](autenticacion.md#82-respuestas-403)) |
| Sin membresía en la empresa o sucursal | `404` (la mayoría) o `403` `OPERATIONAL_ACCESS_DENIED` / `BRANCH_ACCESS_DENIED` (Purchase, Sales, Inventory, Commercial Relationship, Audit) | Problem Details con `code` y `trace_id` |
| Operational Context no disponible al evaluar el alcance | `503` `DEPENDENCY_UNAVAILABLE` | Problem Details con `dependency` |

Detalle de formatos en [Errores](errores.md).

## 9. Información pendiente de verificar

| Punto | Estado |
|---|---|
| Asignación real de permisos por grupo en el realm `siodev` de Render | NO VERIFICADO (se documenta la plantilla del repositorio) |
| Membresías de los usuarios de prueba en Operational Context de Render | NO VERIFICADO |
