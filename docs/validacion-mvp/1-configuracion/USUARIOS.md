# Usuarios y permisos — Ejercicio 1 — Configuración de la empresa: organizaciones, personas, empresas, sucursales y usuarios operativos

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

✅ = el usuario tiene el permiso (o los permisos) de la llamada según la plantilla del realm · ❌ = recibe `403`. Tener el permiso no basta en las rutas de empresa: fuera de sus empresas el usuario recibe `404` (aislamiento).

| Paso | Id | Método y ruta | Permiso requerido | Usuario del recorrido | admin | compras | ventas | supervisor | consulta | reportes | inventario |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [01](01-consultar-los-datos-de-referencia.md) | `C-00.1` | `GET /global-countries` | `perm:geography:global_countries:read` | `admin.test` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-los-datos-de-referencia.md) | `C-00.2` | `GET /global-cities` | `perm:geography:global_cities:read` | `admin.test` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-los-datos-de-referencia.md) | `C-00.3` | `GET /identification-type-rules` | `perm:party-identity:identification_type_rules:read` | `admin.test` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| [01](01-consultar-los-datos-de-referencia.md) | `C-00.4` | `GET /identification-type-rules` | `perm:party-identity:identification_type_rules:read` | `admin.test` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| [02](02-registrar-las-organizaciones.md) | `C-01.empresa_a` | `POST /organization-identities` | `perm:party-identity:organization_identities:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [02](02-registrar-las-organizaciones.md) | `C-01.empresa_b` | `POST /organization-identities` | `perm:party-identity:organization_identities:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [02](02-registrar-las-organizaciones.md) | `C-01.proveedor` | `POST /organization-identities` | `perm:party-identity:organization_identities:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [03](03-registrar-las-personas.md) | `C-02.cliente` | `POST /person-identities` | `perm:party-identity:person_identities:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [03](03-registrar-las-personas.md) | `C-02.admin` | `POST /person-identities` | `perm:party-identity:person_identities:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [03](03-registrar-las-personas.md) | `C-02.compras` | `POST /person-identities` | `perm:party-identity:person_identities:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [03](03-registrar-las-personas.md) | `C-02.ventas` | `POST /person-identities` | `perm:party-identity:person_identities:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [03](03-registrar-las-personas.md) | `C-02.supervisor` | `POST /person-identities` | `perm:party-identity:person_identities:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [03](03-registrar-las-personas.md) | `C-02.consulta` | `POST /person-identities` | `perm:party-identity:person_identities:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [03](03-registrar-las-personas.md) | `C-02.reportes` | `POST /person-identities` | `perm:party-identity:person_identities:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [03](03-registrar-las-personas.md) | `C-02.inventario` | `POST /person-identities` | `perm:party-identity:person_identities:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [04](04-registrar-las-empresas.md) | `C-03.a` | `POST /companies` | `perm:operational-context:companies:create` + `perm:operational-context:platform:administer` | `admin.test` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-registrar-las-empresas.md) | `C-03.b` | `POST /companies` | `perm:operational-context:companies:create` + `perm:operational-context:platform:administer` | `admin.test` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [05](05-registrar-las-sucursales.md) | `C-04.a1` | `POST /companies/<EMPRESA_A>/branches` | `perm:operational-context:branches:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [05](05-registrar-las-sucursales.md) | `C-04.b1` | `POST /companies/<EMPRESA_B>/branches` | `perm:operational-context:branches:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [06](06-registrar-los-usuarios-operativos.md) | `C-05.admin` | `POST /companies/<EMPRESA_A>/application-users` | `perm:operational-context:application_users:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [06](06-registrar-los-usuarios-operativos.md) | `C-05.compras` | `POST /companies/<EMPRESA_A>/application-users` | `perm:operational-context:application_users:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [06](06-registrar-los-usuarios-operativos.md) | `C-05.ventas` | `POST /companies/<EMPRESA_A>/application-users` | `perm:operational-context:application_users:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [06](06-registrar-los-usuarios-operativos.md) | `C-05.supervisor` | `POST /companies/<EMPRESA_A>/application-users` | `perm:operational-context:application_users:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [06](06-registrar-los-usuarios-operativos.md) | `C-05.consulta` | `POST /companies/<EMPRESA_A>/application-users` | `perm:operational-context:application_users:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [06](06-registrar-los-usuarios-operativos.md) | `C-05.reportes` | `POST /companies/<EMPRESA_B>/application-users` | `perm:operational-context:application_users:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [06](06-registrar-los-usuarios-operativos.md) | `C-05.inventario` | `POST /companies/<EMPRESA_B>/application-users` | `perm:operational-context:application_users:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [07](07-asignar-sucursales.md) | `C-06.admin` | `POST /application-users/<USUARIO_ADMIN>/user-branches` | `perm:operational-context:user_branches:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [07](07-asignar-sucursales.md) | `C-06.compras` | `POST /application-users/<USUARIO_COMPRAS>/user-branches` | `perm:operational-context:user_branches:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [07](07-asignar-sucursales.md) | `C-06.ventas` | `POST /application-users/<USUARIO_VENTAS>/user-branches` | `perm:operational-context:user_branches:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [07](07-asignar-sucursales.md) | `C-06.supervisor` | `POST /application-users/<USUARIO_SUPERVISOR>/user-branches` | `perm:operational-context:user_branches:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [07](07-asignar-sucursales.md) | `C-06.inventario` | `POST /application-users/<USUARIO_INVENTARIO>/user-branches` | `perm:operational-context:user_branches:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [08](08-comprobar-el-contexto-operativo.md) | `C-07.admin` | `GET /me/operational-context` | `perm:operational-context:application_users:read` | `admin.test` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [08](08-comprobar-el-contexto-operativo.md) | `C-07.compras` | `GET /me/operational-context` | `perm:operational-context:application_users:read` | `compras.test` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [08](08-comprobar-el-contexto-operativo.md) | `C-07.ventas` | `GET /me/operational-context` | `perm:operational-context:application_users:read` | `ventas.test` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [08](08-comprobar-el-contexto-operativo.md) | `C-07.supervisor` | `GET /me/operational-context` | `perm:operational-context:application_users:read` | `supervisor.test` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [08](08-comprobar-el-contexto-operativo.md) | `C-07.consulta` | `GET /me/operational-context` | `perm:operational-context:application_users:read` | `consulta.test` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
