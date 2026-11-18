# Usuarios y permisos — Ejercicio 1 — Configuración de la empresa: organizaciones, personas, empresas, sucursales y usuarios operativos

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

✅ = el usuario tiene el permiso (o los permisos) de la llamada según la plantilla del realm · ❌ = recibe `403`. Tener el permiso no basta en las rutas de empresa: fuera de sus empresas el usuario recibe `404` (aislamiento).

| Paso | Id | Método y ruta | Permiso requerido | Usuario del recorrido | admin | admin | operario |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [01](01-consultar-los-datos-de-referencia.md) | `C-00.1` | `GET /global-countries` | `perm:geography:global_countries:read` | `admin.sio` | ✅ | ✅ | ✅ |
| [01](01-consultar-los-datos-de-referencia.md) | `C-00.2` | `GET /global-cities` | `perm:geography:global_cities:read` | `admin.sio` | ✅ | ✅ | ✅ |
| [01](01-consultar-los-datos-de-referencia.md) | `C-00.3` | `GET /identification-type-rules` | `perm:party-identity:identification_type_rules:read` | `admin.sio` | ✅ | ✅ | ✅ |
| [01](01-consultar-los-datos-de-referencia.md) | `C-00.4` | `GET /identification-type-rules` | `perm:party-identity:identification_type_rules:read` | `admin.sio` | ✅ | ✅ | ✅ |
| [02](02-registrar-las-organizaciones.md) | `C-01.empresa_a` | `POST /organization-identities` | `perm:party-identity:organization_identities:create` | `admin.sio` | ✅ | ✅ | ✅ |
| [02](02-registrar-las-organizaciones.md) | `C-01.empresa_b` | `POST /organization-identities` | `perm:party-identity:organization_identities:create` | `admin.sio` | ✅ | ✅ | ✅ |
| [02](02-registrar-las-organizaciones.md) | `C-01.proveedor` | `POST /organization-identities` | `perm:party-identity:organization_identities:create` | `admin.sio` | ✅ | ✅ | ✅ |
| [03](03-registrar-las-personas.md) | `C-02.cliente` | `POST /person-identities` | `perm:party-identity:person_identities:create` | `admin.sio` | ✅ | ✅ | ✅ |
| [03](03-registrar-las-personas.md) | `C-02.admin` | `POST /person-identities` | `perm:party-identity:person_identities:create` | `admin.sio` | ✅ | ✅ | ✅ |
| [03](03-registrar-las-personas.md) | `C-02.operario` | `POST /person-identities` | `perm:party-identity:person_identities:create` | `admin.sio` | ✅ | ✅ | ✅ |
| [03](03-registrar-las-personas.md) | `C-02.admin_dao` | `POST /person-identities` | `perm:party-identity:person_identities:create` | `admin.sio` | ✅ | ✅ | ✅ |
| [04](04-registrar-las-empresas.md) | `C-03.a` | `POST /companies` | `perm:operational-context:companies:create` + `perm:operational-context:platform:administer` | `admin.sio` | ✅ | ❌ | ❌ |
| [04](04-registrar-las-empresas.md) | `C-03.b` | `POST /companies` | `perm:operational-context:companies:create` + `perm:operational-context:platform:administer` | `admin.sio` | ✅ | ❌ | ❌ |
| [05](05-registrar-las-sucursales.md) | `C-04.a1` | `POST /companies/<EMPRESA_A>/branches` | `perm:operational-context:branches:create` | `admin.sio` | ✅ | ✅ | ❌ |
| [05](05-registrar-las-sucursales.md) | `C-04.b1` | `POST /companies/<EMPRESA_B>/branches` | `perm:operational-context:branches:create` | `admin.sio` | ✅ | ✅ | ❌ |
| [06](06-registrar-los-usuarios-operativos.md) | `C-05.admin` | `POST /companies/<EMPRESA_A>/application-users` | `perm:operational-context:application_users:create` | `admin.sio` | ✅ | ✅ | ❌ |
| [06](06-registrar-los-usuarios-operativos.md) | `C-05.operario` | `POST /companies/<EMPRESA_A>/application-users` | `perm:operational-context:application_users:create` | `admin.sio` | ✅ | ✅ | ❌ |
| [06](06-registrar-los-usuarios-operativos.md) | `C-05.admin_dao` | `POST /companies/<EMPRESA_B>/application-users` | `perm:operational-context:application_users:create` | `admin.sio` | ✅ | ✅ | ❌ |
| [07](07-asignar-sucursales.md) | `C-06.admin` | `POST /application-users/<USUARIO_ADMIN>/user-branches` | `perm:operational-context:user_branches:create` | `admin.sio` | ✅ | ✅ | ❌ |
| [07](07-asignar-sucursales.md) | `C-06.operario` | `POST /application-users/<USUARIO_OPERARIO>/user-branches` | `perm:operational-context:user_branches:create` | `admin.sio` | ✅ | ✅ | ❌ |
| [07](07-asignar-sucursales.md) | `C-06.admin_dao` | `POST /application-users/<USUARIO_ADMIN_DAO>/user-branches` | `perm:operational-context:user_branches:create` | `admin.sio` | ✅ | ✅ | ❌ |
| [08](08-comprobar-el-contexto-operativo.md) | `C-07.admin` | `GET /me/operational-context` | `perm:operational-context:application_users:read` | `admin.sio` | ✅ | ✅ | ✅ |
| [08](08-comprobar-el-contexto-operativo.md) | `C-07.operario` | `GET /me/operational-context` | `perm:operational-context:application_users:read` | `operario.dao` | ✅ | ✅ | ✅ |
