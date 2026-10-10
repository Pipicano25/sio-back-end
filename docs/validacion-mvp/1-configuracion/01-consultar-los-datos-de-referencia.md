# Paso 01 de 08 — Consultar los datos de referencia

Ejercicio 1 — Configuración de la empresa: organizaciones, personas, empresas, sucursales y usuarios operativos · [Orden del ejercicio](ORDEN.md)

---

## 1. Consultar el país Colombia en Geography

Paso `C-00.1` · usuario **`admin.test`** · ítems de la FASE 10: 1

```http
GET http://127.0.0.1:8102/global-countries?iso3_code=COL
```

**Permiso que exige la URL:** `perm:geography:global_countries:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:geography:all:read`), `ventas.test` (por `perm:geography:all:read`), `supervisor.test` (por `perm:all:all:read`), `consulta.test` (por `perm:geography:global_countries:read`), `reportes.test` (por `perm:geography:global_countries:read`), `inventario.test` (por `perm:geography:all:read`)

**Por qué se hace así**

- Las identidades, empresas y sucursales guardan solo el id del país de Geography.

**Respuesta esperada:** `200`

**Guardar:** `items.0.id` → `<PAIS_CO>`

## 2. Consultar una ciudad de Colombia en Geography

Paso `C-00.2` · usuario **`admin.test`** · ítems de la FASE 10: 2

```http
GET http://127.0.0.1:8102/global-cities?country_id=<PAIS_CO>&search=Bogot
```

**Permiso que exige la URL:** `perm:geography:global_cities:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:geography:all:read`), `ventas.test` (por `perm:geography:all:read`), `supervisor.test` (por `perm:all:all:read`), `consulta.test` (por `perm:geography:global_cities:read`), `reportes.test` (por `perm:geography:global_cities:read`), `inventario.test` (por `perm:geography:all:read`)

**Por qué se hace así**

- La sucursal se ubica en una ciudad del seed de Geography (ubicación coherente país–departamento–ciudad).

**Respuesta esperada:** `200`

**Guardar:** `items.0.id` → `<CIUDAD>`, `items.0.administrative_division_id` → `<DEPARTAMENTO>`

## 3. Consultar la regla de identificación NIT de Colombia

Paso `C-00.3` · usuario **`admin.test`** · ítems de la FASE 10: 1

```http
GET http://127.0.0.1:8101/api/v1/identification-type-rules?party_kind=ORGANIZATION&country_id=<PAIS_CO>&sigla=NIT&is_active=true
```

**Permiso que exige la URL:** `perm:party-identity:identification_type_rules:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:party-identity:identification_type_rules:read`), `ventas.test` (por `perm:party-identity:identification_type_rules:read`), `supervisor.test` (por `perm:all:all:read`), `consulta.test` (por `perm:party-identity:identification_type_rules:read`), `reportes.test` (por `perm:party-identity:identification_type_rules:read`)

**Por qué se hace así**

- Los NIT ficticios se generan con el patrón de la regla vigente (nunca identificaciones reales).

**Respuesta esperada:** `200`

**Guardar:** `items.0.number_pattern` → `<PATRON_NIT>`

## 4. Consultar la regla de identificación CC de Colombia

Paso `C-00.4` · usuario **`admin.test`** · ítems de la FASE 10: 3, 5

```http
GET http://127.0.0.1:8101/api/v1/identification-type-rules?party_kind=PERSON&country_id=<PAIS_CO>&sigla=CC&is_active=true
```

**Permiso que exige la URL:** `perm:party-identity:identification_type_rules:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:party-identity:identification_type_rules:read`), `ventas.test` (por `perm:party-identity:identification_type_rules:read`), `supervisor.test` (por `perm:all:all:read`), `consulta.test` (por `perm:party-identity:identification_type_rules:read`), `reportes.test` (por `perm:party-identity:identification_type_rules:read`)

**Respuesta esperada:** `200`

**Guardar:** `items.0.number_pattern` → `<PATRON_CC>`
