# Usuarios y permisos — Ejercicio 6 — Auditoría del recorrido

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

✅ = el usuario tiene el permiso (o los permisos) de la llamada según la plantilla del realm · ❌ = recibe `403`. Tener el permiso no basta en las rutas de empresa: fuera de sus empresas el usuario recibe `404` (aislamiento).

| Paso | Id | Método y ruta | Permiso requerido | Usuario del recorrido | admin | compras | ventas | supervisor | consulta | reportes | inventario |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [01](01-consultar-el-historial-de-auditoria.md) | `U-01.empresa` | `GET /companies/<EMPRESA_A>/entity-history/<TIPO_ENTIDAD>/<ID_ENTIDAD>` | `perm:audit:audit-events:read` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [01](01-consultar-el-historial-de-auditoria.md) | `U-01.plataforma` | `GET /platform-entity-history/<TIPO_ENTIDAD>/<ID_ENTIDAD>` | `perm:audit:platform-events:read` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [02](02-datos-protegidos-y-permiso-de-auditoria.md) | `U-02.vendedor` | `GET /companies/<EMPRESA_A>/audit-events` | `perm:audit:audit-events:read` | `ventas.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
