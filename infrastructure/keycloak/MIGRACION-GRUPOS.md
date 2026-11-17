# Migración a los tres grupos (spec 026)

Pasa un realm que ya existe (VPS, entornos persistentes) de los 7 grupos anteriores a `superadmin`, `admin` y
`empleado`. Un realm nuevo no la necesita: lo crea la plantilla (`realm-template/sio-realm.template.json`).

`--import-realm` no modifica un realm existente, por eso la migración se hace con la API de administración de
Keycloak mediante `migrar_grupos_026.py` (solo biblioteca estándar de Python). Las membresías de Operational Context
no cambian: dependen del `sub` del usuario, que no cambia.

## Correspondencia

| Grupo anterior | Grupo nuevo | Nota |
| --- | --- | --- |
| `administradores` | `superadmin` | Igual que hoy (`perm:all:all:all`) |
| `supervisores` | `admin` | Pierde `perm:all:all:read` sobre la auditoría de plataforma; gana `delete` en servicios de empresa |
| `ventas`, `compras`, `inventario` | `empleado` | Gana lo de los otros dos y crear/modificar personas y organizaciones |
| `reportes`, `consulta` | `empleado` | **Ganan escritura** (decisión del negocio, aclaración P2 de la spec) |

Si un usuario estaba en varios grupos, queda en el de más alcance (`superadmin` > `admin` > `empleado`).

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

1. **Plan.** No cambia nada; muestra los roles de perfil y grupos que se crearían y a qué grupo pasa cada usuario.

   ```bash
   python infrastructure/keycloak/migrar_grupos_026.py plan
   ```

2. **Aplicar.** Crea los roles de perfil y los tres grupos con los roles exactos de la plantilla y agrega a cada
   usuario a su grupo nuevo. Los grupos anteriores quedan intactos (vuelta atrás inmediata). Se puede repetir.

   ```bash
   python infrastructure/keycloak/migrar_grupos_026.py aplicar
   ```

   Mientras el usuario siga también en su grupo anterior, sus permisos son la suma de ambos.

3. **Comprobar.** Pida un token de un usuario de cada grupo nuevo y revise `resource_access.sio-api.roles`. Por
   ejemplo, con un usuario de prueba (en un entorno de desarrollo):

   ```bash
   TOKEN=$(curl -s -X POST "$KC_URL/realms/$KC_REALM/protocol/openid-connect/token" \
     -d grant_type=password -d client_id=sio-web -d scope=openid \
     -d username=ventas.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
     | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
   python -c "import sys, json, base64; p = sys.argv[1].split('.')[1]; p += '=' * (-len(p) % 4); \
   print(sorted(json.loads(base64.urlsafe_b64decode(p))['resource_access']['sio-api']['roles']))" "$TOKEN"
   ```

   Mientras no se ejecute el paso 4, el token incluye todavía los roles del grupo anterior.

4. **Retirar los grupos anteriores.** Saca a los usuarios de los grupos anteriores y elimina esos grupos y los roles
   de perfil `administrador`, `supervisor`, `compras`, `ventas`, `inventario`, `reportes` y `consulta`. Se niega si
   algún miembro aún no tiene grupo nuevo.

   ```bash
   python infrastructure/keycloak/migrar_grupos_026.py plan-retirar   # sin cambios
   python infrastructure/keycloak/migrar_grupos_026.py retirar
   ```

5. **Usuarios de prueba eliminados.** En un entorno de desarrollo creado con la plantilla anterior existen
   `reportes.test` y `consulta.test`. El paso 2 los pasa a `empleado`; si no se usan, elimínelos desde la consola
   (*Users* → usuario → *Delete*).

Los permisos nuevos aparecen en el siguiente token de cada usuario (a lo sumo 300 s después, o al renovar).

## Vuelta atrás

- **Antes del paso 4:** quite a los usuarios de los grupos nuevos (consola: *Groups* → grupo → *Members* → *Leave*)
  o elimine los tres grupos nuevos; los anteriores siguen intactos.
- **Después del paso 4:** recree los grupos anteriores importando la plantilla del commit previo a la spec 026 en un
  realm de prueba y copiando sus roles, o reasigne a mano. Por eso conviene esperar a comprobar el paso 3.

## Verificado

Probado en la pila aislada `sio-it-*` partiendo de un realm con la plantilla anterior (ver
`specs/026-three-permission-groups/baseline/migracion.md`).
