# Migración a los grupos de la spec 026 (versión del servidor OCI)

Lleva un realm que ya existe a los cinco grupos `superadmin`, `admin`, `Compras`, `Ventas` e `Inventario`. Un realm
nuevo no la necesita: lo crea la plantilla (`realm-template/sio-realm.template.json`).

`--import-realm` no modifica un realm existente, por eso la migración se hace con la API de administración de
Keycloak mediante `migrar_grupos_026.py` (solo biblioteca estándar de Python). Las membresías de Operational Context
no cambian: dependen del `sub` del usuario, que no cambia.

## Estados de partida

| Estado | Dónde | Qué hace la migración |
| --- | --- | --- |
| Servidor OCI: `superadmin`, `admin` y áreas **vacías** | Servidor OCI | Carga en `Compras`, `Ventas` e `Inventario` los permisos de su área. Los usuarios no se mueven |
| `superadmin`, `admin`, `empleado` (commit `236acbb`) | Entornos locales de la 026 | Crea las áreas, pone a los miembros de `empleado` en las tres y, al retirar, elimina `empleado` |
| Siete grupos anteriores a la 026 | VPS | Crea los cinco grupos y pasa a cada usuario según la tabla siguiente |

## Correspondencia

| Grupo anterior | Grupos nuevos | Nota |
| --- | --- | --- |
| `administradores` | `superadmin` | Igual que hoy (`perm:all:all:all`) |
| `supervisores` | `admin` | Pierde `perm:all:all:read` sobre la auditoría de plataforma; gana `delete` en servicios de empresa |
| `compras` | `Compras` | Gana crear y modificar personas y organizaciones |
| `ventas` | `Ventas` | Gana crear y modificar personas y organizaciones |
| `inventario` | `Inventario` | |
| `reportes`, `consulta`, `empleado` | `Compras`, `Ventas`, `Inventario` | `reportes` y `consulta` **ganan escritura** (decisión del negocio) |

Un usuario puede quedar en varios grupos: sus permisos se suman. El script solo agrega grupos; nunca saca a nadie de
un grupo nuevo.

## Requisitos

- Acceso de administrador al realm `master` de Keycloak.
- Python 3.10 o superior en la máquina que ejecuta el script, con acceso HTTP a Keycloak.
- La plantilla de este repositorio en la versión de la spec 026 (el script lee de ella los roles exactos).

Variables de entorno (no escriba la contraseña en la línea de comandos ni en archivos versionados):

```bash
export KC_URL=http://localhost:8081   # URL de Keycloak
export KC_REALM=sio
export KC_ADMIN_USER=<administrador>
read -rs KC_ADMIN_PASSWORD && export KC_ADMIN_PASSWORD
```

## Pasos

1. **Plan.** No cambia nada; muestra los grupos que se crearían o completarían y a qué grupos pasa cada usuario.

   ```bash
   python infrastructure/keycloak/migrar_grupos_026.py plan
   ```

2. **Aplicar.** Crea o completa los cinco grupos con los roles exactos de la plantilla y agrega a cada usuario de un
   grupo anterior a sus grupos nuevos. Los grupos anteriores quedan intactos (vuelta atrás inmediata). Se puede
   repetir.

   ```bash
   python infrastructure/keycloak/migrar_grupos_026.py aplicar
   ```

   En el servidor OCI este paso solo agrega los permisos a `Compras` (58), `Ventas` (46) e `Inventario` (20).

3. **Comprobar.** Pida un token de un usuario de cada grupo y revise `resource_access.sio-api.roles`:

   ```bash
   TOKEN=$(curl -s -X POST "$KC_URL/realms/$KC_REALM/protocol/openid-connect/token" \
     -d grant_type=password -d client_id=sio-web -d scope=openid \
     -d username=operario.dao -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
     | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
   python -c "import sys, json, base64; p = sys.argv[1].split('.')[1]; p += '=' * (-len(p) % 4); \
   print(len([r for r in json.loads(base64.urlsafe_b64decode(p))['resource_access']['sio-api']['roles'] if r.startswith('perm:')]))" "$TOKEN"
   ```

   Un usuario en las tres áreas debe tener 80 permisos (los del antiguo `empleado`).

4. **Retirar los grupos anteriores.** Elimina los siete grupos anteriores a la 026 y `empleado`, y los roles de perfil
   `administrador`, `supervisor`, `compras`, `ventas`, `inventario`, `reportes` y `consulta`. El rol `empleado` se
   conserva en el catálogo (como en el servidor OCI). Se niega si algún miembro aún no está en sus grupos nuevos.

   ```bash
   python infrastructure/keycloak/migrar_grupos_026.py plan-retirar   # sin cambios
   python infrastructure/keycloak/migrar_grupos_026.py retirar
   ```

5. **Usuarios.** El script no crea usuarios. La plantilla trae `admin.sio`, `admin.dao`, `operario.dao`, `alex`,
   `manuel`, `pedro` y `tomas`; en un realm existente que no los tenga, créelos en la consola si los necesita.

Los permisos nuevos aparecen en el siguiente token de cada usuario (a lo sumo 300 s después, o al renovar).

## Vuelta atrás

- **Antes del paso 4:** quite a los usuarios de los grupos nuevos o vacíe sus roles; los anteriores siguen intactos.
  En el servidor OCI, vaciar los roles de las áreas lo devuelve a su estado inicial.
- **Después del paso 4:** recree los grupos anteriores importando la plantilla del commit previo en un realm de
  prueba y copiando sus roles, o reasigne a mano. Por eso conviene esperar a comprobar el paso 3.

## Verificado

Probado en la pila aislada `sio-it-*` desde los tres estados de partida (ver
`specs/026-three-permission-groups/baseline/migracion.md`).
