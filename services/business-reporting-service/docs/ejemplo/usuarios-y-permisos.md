# Usuarios y permisos de business-reporting-service

- Cada reporte exige su permiso `perm:business-reporting:<reporte>:read`, evaluado por `sio-auth`; el `403` nunca revela el permiso.
- El servicio consulta Sales, Purchase, Inventory, Operational Context, Commercial Relationship y Product Catalog **con el token del usuario** (DR-07): el usuario necesita además el permiso de lectura de cada propietario. Si el propietario responde `403`, el reporte responde el mismo `403` genérico.
- `reportes` consulta la evolución de existencias con `perm:inventory:stock_evolution:read`, que **no** abre el kardex ni los costos (DR-11).
- Sin costos ni márgenes: el margen bruto es de la fase 2 de la spec 023.

## Usuarios de prueba

| Usuario | Grupo |
| --- | --- |
| `admin.test` | `administradores` |
| `supervisor.test` | `supervisores` |
| `compras.test` | `compras` |
| `ventas.test` | `ventas` |
| `inventario.test` | `inventario` |
| `reportes.test` | `reportes` |
| `consulta.test` | `consulta` |

## Cómo obtener el token

```bash
curl -s -X POST "$KEYCLOAK_TOKEN_URL" \
  -d grant_type=password -d client_id=sio-web \
  -d username=reportes.test -d password="$KEYCLOAK_TEST_USER_PASSWORD"
```

## Matriz de las URL

| Ejercicio | Paso | URL | Permiso | `admin.test` | `supervisor.test` | `compras.test` | `ventas.test` | `inventario.test` | `reportes.test` | `consulta.test` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | `GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/top-selling-products?date_from=2026-10-01&date_to=2026-10-15` | `perm:business-reporting:top_selling_products:read` | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ |
| 1 | 2 | `GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/top-selling-products?date_from=2026-10-01&date_to=2026-10-15&rank_by=amount&include_presentations=true&limit=2` | `perm:business-reporting:top_selling_products:read` | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ |
| 2 | 1 | `GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/sales-by-branch?date_from=2026-10-01&date_to=2026-10-15` | `perm:business-reporting:sales_by_branch:read` | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| 3 | 1 | `GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/purchases?date_from=2026-10-01&date_to=2026-10-15` | `perm:business-reporting:purchases:read` | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
| 3 | 2 | `GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/purchases?date_from=2026-10-01&date_to=2026-10-15&category=PENDING_RECEIPT` | `perm:business-reporting:purchases:read` | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
| 4 | 1 | `GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/branches/d23b0000-0000-4000-8000-000000000001/reports/stock-evolution?date_from=2026-10-01&date_to=2026-10-15` | `perm:business-reporting:stock_evolution:read` | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ |
| 4 | 2 | `GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/stock-evolution?date_from=2026-10-01&date_to=2026-10-15` | `perm:business-reporting:stock_evolution:read` | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ |
| 5 | 1 | `GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/purchases?date_from=2026-10-01&date_to=2026-10-15&format=csv` | `perm:business-reporting:purchases:read` | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
| 6 | 1 | `GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/branches/d23b0000-0000-4000-8000-000000000002/reports/sales-by-branch?date_from=2026-10-01&date_to=2026-10-15` | `perm:business-reporting:sales_by_branch:read` | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| 6 | 2 | `GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/branches/d23b0000-0000-4000-8000-000000000002/reports/purchases?date_from=2026-10-01&date_to=2026-10-15` | `perm:business-reporting:purchases:read` | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
