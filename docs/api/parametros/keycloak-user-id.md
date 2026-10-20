# Parámetro `keycloak_user_id`

[← Parámetros](README.md) · [← Índice](../index.md) · Lo emite Keycloak; lo exponen [Operational Context](../servicios/operational-context.md) y [Audit](../servicios/audit.md)

| Propiedad | Valor |
|---|---|
| Qué representa | El identificador de la **cuenta del usuario en Keycloak**: es el claim `sub` del Access Token. Es único por persona en todo el realm y no cambia entre empresas; por eso las membresías ([application_user_id](application-user-id.md)) y la auditoría lo usan para enlazar con la cuenta |
| Nombre en las rutas y cuerpos | `keycloak_user_id` (cuerpo de creación de membresía, filtro `?keycloak_user_id=` en Operational Context y Audit, campo `keycloak_user_id` en las respuestas) |
| Tipo | UUID (texto). Operational Context lo acepta en el cuerpo y el filtro como texto de hasta 255 caracteres; Audit lo valida como UUID |
| Obligatorio | Al crear una membresía se envía `keycloak_user_id` **o** `username`, exactamente uno |
| Ejemplo (ficticio) | `3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c` |
| Quién lo genera | Keycloak, al crear la cuenta del usuario |
| Alcance | Global (realm `siodev`) |

## Cómo obtenerlo

**El propio usuario:** es el `sub` del Access Token; la [API 4 de Acceso y contexto operativo](../principales/acceso-y-contexto-operativo.md#4-identificar-al-usuario-y-sus-permisos) explica cómo decodificar el token para leerlo sin llamar a ningún servicio. También lo devuelve el contexto operativo:

**¿Qué hace?** Devuelve la identidad operativa del usuario del token: su `keycloak_user_id` y sus membresías con las sucursales asignadas y el acceso efectivo en cada una. No pagina ni filtra. Descrita en [Acceso y contexto operativo, API 5](../principales/acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario).

| | |
|---|---|
| Método y ruta | `GET /api/v1/me/operational-context` |
| URL completa | `https://sio-operational-context-dev.onrender.com/api/v1/me/operational-context` |
| Parámetros | Ninguno |
| Permiso | `perm:operational-context:application_users:read` |
| Clasificación | `READ` |

```bash
curl -X GET \
  'https://sio-operational-context-dev.onrender.com/api/v1/me/operational-context' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Respuesta `200` (fragmento; el documento completo está en [company_id](company-id.md)):

```json
{
  "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "memberships": []
}
```

**Campo exacto:** `keycloak_user_id` (raíz del documento).

**Posibles errores de esta API:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `OPERATIONAL_CONTEXT.FORBIDDEN` | Falta `perm:operational-context:application_users:read` | Mostrar que faltan permisos y el `trace_id` |
| `503` | `OPERATIONAL_CONTEXT.DEPENDENCY_UNAVAILABLE` | La base de datos no responde | Reintentar más tarde |

**Otro usuario de la empresa (administración):** `GET https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/application-users` lista, con paginación y búsqueda, las membresías de la empresa (permiso `perm:operational-context:application_users:read`; cURL y respuesta en [application_user_id](application-user-id.md)) y devuelve en cada una el campo **`items[].keycloak_user_id`**. Sus errores: `401`; `403 OPERATIONAL_CONTEXT.FORBIDDEN`; `404 OPERATIONAL_CONTEXT.NOT_FOUND` si la empresa está fuera del alcance del usuario; `422 OPERATIONAL_CONTEXT.VALIDATION_ERROR` si un parámetro es inválido; `503 OPERATIONAL_CONTEXT.DEPENDENCY_UNAVAILABLE`. Descrita en [Administración empresarial, API 9](../principales/administracion-empresarial.md#9-consultar-los-usuarios-de-una-empresa).

**Un usuario que aún no tiene membresía:** no hay una API de SIO que liste cuentas de Keycloak. El administrador de Keycloak toma el **ID** del usuario en la consola del realm, o bien la membresía se crea con `username` en lugar de `keycloak_user_id` y Operational Context resuelve el `sub` por sí mismo.

## Cómo usarlo después

- En [Administración empresarial](../principales/administracion-empresarial.md): campo `keycloak_user_id` del cuerpo de la [API 10 (crear membresía)](../principales/administracion-empresarial.md#10-asociar-un-usuario-a-una-empresa-crear-membresía), alternativo a `username`; filtro `keycloak_user_id` de la API 9 (usuarios de una empresa) y de la [API 16 (auditoría)](../principales/administracion-empresarial.md#16-consultar-la-trazabilidad-de-la-empresa-auditoría).
- En las respuestas de Sales, Purchase, Inventory y Audit aparece como `created_by`, `updated_by`, `assigned_by` o `keycloak_user_id` para identificar quién actuó.
- No lo uses como clave de datos de la empresa: para eso está `application_user_id`, que es distinto por empresa.

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `422 OPERATIONAL_CONTEXT.KEYCLOAK_USER_NOT_FOUND` | No existe una cuenta con ese `sub` (o ese `username`) en el realm |
| `422 OPERATIONAL_CONTEXT.KEYCLOAK_USER_DISABLED` | La cuenta existe pero está deshabilitada en Keycloak |
| `422 OPERATIONAL_CONTEXT.TECHNICAL_ACCOUNT_NOT_ALLOWED` | El `sub` corresponde a una cuenta de servicio, no a una persona |
| `422 AUDIT.VALIDATION_ERROR` | El filtro `keycloak_user_id` no es un UUID |
