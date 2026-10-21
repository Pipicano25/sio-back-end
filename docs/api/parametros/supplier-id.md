# Parámetro `company_supplier_id`

[← Parámetros](README.md) · [← Índice](../index.md) · Servicio propietario: [Commercial Relationship](../servicios/commercial-relationship.md)

> El nombre exacto del parámetro en las rutas y cuerpos es **`company_supplier_id`** (proveedor de la empresa). El archivo se llama `supplier-id` por brevedad.

| Propiedad | Valor |
|---|---|
| Qué representa | Un **proveedor de una empresa**: la relación comercial entre la empresa y una organización identificada en Party Identity. Las compras se registran contra este identificador |
| Nombre en las rutas y cuerpos | `company_supplier_id` (en Purchase: campo del cuerpo y filtro `?company_supplier_id=`; en Commercial Relationship: ruta `/company-suppliers/{company_supplier_id}`) |
| Tipo | UUID (texto) |
| Obligatorio | Sí al crear una compra |
| Ejemplo (ficticio) | `d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60` |
| Quién lo genera | Commercial Relationship, al seleccionar el proveedor (`id` de la respuesta) |
| Alcance | Empresa |

## Cómo obtenerlo

**¿Qué hace?** Lista, con paginación y búsqueda, los proveedores de la empresa con su código interno, nombre para mostrar, organización en Party Identity y estado (`ACTIVE`, `INACTIVE` o `BLOCKED`). Por defecto solo `ACTIVE`. Es el buscador de proveedores al registrar una compra y la fuente de `company_supplier_id`. Ficha técnica: [Commercial Relationship 19](../servicios/commercial-relationship.md#19-get-companiescompany_idcompany-suppliers); guía principal: [Gestión de proveedores, API 2](../principales/gestion-de-proveedores.md#2-buscar-y-listar-los-proveedores-de-la-empresa).

| | |
|---|---|
| Método y ruta | `GET /api/v1/companies/{company_id}/company-suppliers` |
| URL completa | `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-suppliers` |
| Parámetros de ruta | `company_id` (UUID) — [cómo obtenerlo](company-id.md) |
| Parámetros de consulta | `page` (≥1), `page_size` (1–100, por defecto 20), `search` (máx. 100), `status` (`ACTIVE`, `INACTIVE`, `BLOCKED`, `ALL`), `organization_identity_id` (UUID) |
| Permiso | `perm:commercial-relationship:company_suppliers:read` |
| Clasificación | `READ` |

```bash
curl -X GET \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-suppliers?status=ACTIVE' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Respuesta `200` (modelo `PaginatedResponse[CompanySupplierResponse]`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "version": 2,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-02-01T10:10:00Z",
      "updated_at": "2026-03-01T09:00:00Z",
      "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
      "internal_code": "PRV-000045",
      "display_name": "Distribuidora Ejemplo S.A.S.",
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

**Campo exacto:** `items[].id`. Un proveedor `BLOCKED` tiene `block_reason` informado y no es elegible para compras.

**Posibles errores de esta API:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `COMMERCIAL_RELATIONSHIP.FORBIDDEN` | Falta `perm:commercial-relationship:company_suppliers:read` | Mostrar que faltan permisos y el `trace_id` |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | Operational Context rechazó la comprobación de membresía (suele faltar `perm:operational-context:application_users:read`) | Revisar los permisos del usuario |
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | Sin membresía `ACTIVE` en la empresa, o empresa inexistente | Volver a leer el contexto operativo |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | Paginación fuera de rango, `search` > 100, `status` u otro filtro inválido, UUID mal formado | Corregir los parámetros |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Operational Context, Party Identity o Product Catalog no responden (`dependency` lo indica) | Reintentar más tarde |

## Si el proveedor no existe todavía (operación `WRITE`)

1. Obtén o crea la identidad de la organización en Party Identity: [organization_identity_id](organization-identity-id.md).
2. Selecciónalo como proveedor de la empresa:

**¿Qué hace la API de creación?** Crea la relación comercial «proveedor» entre la empresa y una organización existente y activa de Party Identity (distinta de la propia empresa), con código interno único y nombre para mostrar. Devuelve `201` con el proveedor creado; su `id` es el `company_supplier_id`. Ficha técnica: [Commercial Relationship 20](../servicios/commercial-relationship.md#20-post-companiescompany_idcompany-suppliers).

| | |
|---|---|
| Método y ruta | `POST /api/v1/companies/{company_id}/company-suppliers` |
| URL completa | `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-suppliers` |
| Permiso | `perm:commercial-relationship:company_suppliers:create` |
| Clasificación | `WRITE` |

Cuerpo (modelo `CompanySupplierCreate`; no admite campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `organization_identity_id` | UUID | Sí | Debe existir y estar `ACTIVE` en Party Identity |
| `internal_code` | string | Sí | 1 a 60 caracteres; único por empresa |
| `display_name` | string | Sí | 1 a 200 caracteres |
| `preferred_contact_person_id` | UUID \| null | No | Persona de contacto de la organización |

```json
{
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "internal_code": "PRV-000045",
  "display_name": "Distribuidora Ejemplo S.A.S.",
  "preferred_contact_person_id": null
}
```

La respuesta `201` devuelve el proveedor; el `company_supplier_id` es su campo `id`.

**Posibles errores al crear:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `COMMERCIAL_RELATIONSHIP.FORBIDDEN` | Falta `perm:commercial-relationship:company_suppliers:create` | Mostrar que faltan permisos y el `trace_id` |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | Operational Context rechazó la comprobación de membresía (suele faltar `perm:operational-context:application_users:read`) | Revisar los permisos del usuario |
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | Sin membresía `ACTIVE` en la empresa, o empresa inexistente | Volver a leer el contexto operativo |
| `409` | `COMMERCIAL_RELATIONSHIP.DUPLICATE_SUPPLIER` | Esa organización ya es proveedor de la empresa | Buscar el proveedor existente |
| `409` | `COMMERCIAL_RELATIONSHIP.DUPLICATE_INTERNAL_CODE` | Ya existe un proveedor con ese `internal_code` | Pedir otro código |
| `422` | `COMMERCIAL_RELATIONSHIP.SELF_RELATIONSHIP_NOT_ALLOWED` | La organización es la identidad de la propia empresa | Elegir otra organización |
| `422` | `COMMERCIAL_RELATIONSHIP.ORGANIZATION_IDENTITY_NOT_FOUND` / `ORGANIZATION_IDENTITY_INACTIVE` | La organización no existe o está `INACTIVE` en Party Identity | Volver a buscarla o reactivar la identidad |
| `422` | `COMMERCIAL_RELATIONSHIP.CONTACT_PERSON_INVALID` | `preferred_contact_person_id` no es un contacto activo de la organización | Elegir un contacto activo |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden registrar proveedores en ella |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | Campo obligatorio ausente, formato inválido o campo desconocido | Corregir el formulario |
| `403` | `COMMERCIAL_RELATIONSHIP.PARTY_IDENTITY_ACCESS_DENIED` | Falta permiso de lectura en Party Identity para validar la organización o el contacto | Pedir los permisos de lectura de Party Identity |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Operational Context o Party Identity no responden (`dependency` lo indica) | Reintentar más tarde |

Documentación completa con cURL, cuerpo y ejemplos de error: [Gestión de proveedores, API 1](../principales/gestion-de-proveedores.md#1-registrar-un-proveedor-de-la-empresa).

## Cómo usarlo después

- En [Administración empresarial](../principales/administracion-empresarial.md#17-consultar-el-historial-de-una-venta-una-compra-o-un-producto): `{entity_id}` de la ruta de la API 17 con `entity_type=CompanySupplier`.
- `POST https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases` → campo `company_supplier_id` (proveedor `ACTIVE`; ver [Compras](../principales/compras.md)).
- [Gestión de proveedores, API 3](../principales/gestion-de-proveedores.md#3-consultar-un-proveedor) (consulta la ficha del proveedor) y API [5 a 9](../principales/gestion-de-proveedores.md#5-actualizar-un-proveedor) (actualizar, inactivar, reactivar, bloquear y desbloquear): ruta `/company-suppliers/{company_supplier_id}`.
- [API 11](../principales/gestion-de-proveedores.md#11-consultar-las-condiciones-de-pago-de-los-proveedores) y [API 13](../principales/gestion-de-proveedores.md#13-consultar-los-productos-que-suministran-los-proveedores): filtro `?company_supplier_id=` para listar condiciones de pago y productos del proveedor.
- [API 12](../principales/gestion-de-proveedores.md#12-registrar-una-condición-de-pago-del-proveedor) y [API 14](../principales/gestion-de-proveedores.md#14-registrar-un-producto-que-suministra-el-proveedor): campo `company_supplier_id` del cuerpo (proveedor `ACTIVE`; si no, `422 COMPANY_SUPPLIER_INACTIVE` o `COMPANY_SUPPLIER_BLOCKED`).

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `404 COMMERCIAL_RELATIONSHIP.NOT_FOUND` | El proveedor no pertenece a la empresa o el usuario no tiene membresía |
| `409 PURCHASE.REFERENCES_NOT_ELIGIBLE` | El proveedor está `INACTIVE` o `BLOCKED` |
