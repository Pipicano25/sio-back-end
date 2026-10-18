# Pila de integración aislada `sio-it`

Entorno efímero para las pruebas que escriben en servicios reales: integración, seguridad y rendimiento de la
spec 022, y las suites `integration` de Purchase, Sales y Commercial Relationship. Nace del incidente del
2026-10-16, cuando una guía E2E escribió en el entorno persistente. **Nunca comparte nada con ese entorno.**

## Qué garantiza

`stack.sh verificar` lo comprueba sobre la configuración renderizada antes de cualquier operación de Docker:

| Garantía | Cómo |
|---|---|
| Proyecto propio | `sio-it`; ningún contenedor `sio-it-*` puede ser de otro proyecto |
| Contenedores identificables | Prefijo `sio-it-` y etiqueta `sio.integration.isolated=true` en todos |
| Red propia | Solo `sio-it-network`; no se une a `sio-network` |
| Sin datos persistentes | Ningún volumen con nombre: las bases y el almacenamiento de objetos van en `tmpfs` |
| Puertos que no colisionan | Solo `127.0.0.1:18000-18999` (los persistentes usan 81xx, 54xx, 8081 y 9000 a 9003) |
| Imágenes propias | `sio-it/<servicio>:spec022`; nunca reemplaza `sio/<servicio>:<versión>` del entorno persistente |
| Secretos propios | `validation/isolated-stack/.env`, generado con valores aleatorios y no versionado (`**/.env`) |

Las pruebas solo envían solicitudes después de `validation/isolation_guard.py`: cada URL, incluido Keycloak, debe
llegar a un puerto publicado por exactamente un contenedor con la etiqueta. `docker stop`, `start`, `pause` y
`exec` solo se aplican a contenedores aislados.

## Componentes y puertos

| Servicio | Puerto | Servicio | Puerto |
|---|---|---|---|
| Keycloak (realm de la plantilla) | 18081 | Commercial Relationship | 18106 |
| Party Identity | 18101 | Purchase | 18107 |
| Geography | 18102 | Sales | 18108 |
| Product Catalog (con la ruta pública de imágenes) | 18103 | Inventory | 18109 |
| Operational Context | 18104 | Audit | 18110 |
| Payment Reference | 18105 | product-inventory-query-service | 18112 |
| Almacenamiento de objetos (API S3) | 18902 | | |

Además: una base PostgreSQL por servicio y por Keycloak, y los trabajadores de auditoría, precios y conciliación.
La ruta pública de imágenes de Product Catalog solo está habilitada aquí; el entorno persistente sigue sin ella
(FR-022-99).

## Procedimiento

Desde la raíz del repositorio (con permiso para usar Docker):

```bash
bash validation/isolated-stack/stack.sh verificar     # solo valida; no crea nada
bash validation/isolated-stack/stack.sh levantar      # construye, levanta, migra y carga los datos de referencia
eval "$(bash validation/isolated-stack/stack.sh entorno)"   # URL de la pila (sin secretos)
export SIO_IT_STATE_DIR=/tmp/sio-it-state                    # manifiestos de los datos sembrados

# Datos ficticios de la spec 022 (empresa, sucursales, catálogo, precios, saldos y políticas)
services/product-catalog-service/.venv/bin/python validation/isolated-stack/seed.py

# Integración y seguridad del servicio nuevo
(cd services/product-inventory-query-service && .venv/bin/pytest -m integration -o addopts="" tests/integration)

# Rendimiento: juegos sintéticos y medición
services/product-catalog-service/.venv/bin/python validation/isolated-stack/synthetic.py --perfil dao
services/product-catalog-service/.venv/bin/python validation/isolated-stack/synthetic.py --perfil sesgado
(cd services/product-inventory-query-service && .venv/bin/pytest -m performance -o addopts="" tests/performance)
(cd services/product-catalog-service && .venv/bin/pytest -m performance -o addopts="" tests/performance/test_public_image_304.py)

bash validation/isolated-stack/stack.sh retirar       # elimina SOLO los contenedores y la red del proyecto sio-it
```

`levantar` aplica las migraciones de cada servicio y sus seeds (Geography, Product Catalog, Payment Reference y
Party Identity), en el mismo orden que `infrastructure/scripts/rebuild-all.sh`, pero solo dentro de la pila.

## Prohibiciones

- No levantar la pila con `docker compose` sin `--project-name sio-it` y `--env-file validation/isolated-stack/.env`.
- No apuntar las pruebas a puertos 81xx, 8081 ni 54xx: la barrera lo rechaza.
- No usar datos de DAO ni copiar secretos de `infrastructure/.env`.
- No detener las bases ni el almacenamiento aislados con `docker stop`: están en `tmpfs` y perderían los datos.
  Para simular caídas del almacenamiento se usa `docker pause`. Las pruebas de caída de base de Purchase y Sales
  necesitan bases persistentes entre reinicios y no se ejecutan en esta pila.
- No ejecutar `docker volume rm` ni `docker system prune`: `retirar` es suficiente y no toca nada fuera de `sio-it`.
