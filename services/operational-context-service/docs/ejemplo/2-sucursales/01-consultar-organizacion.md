# Paso 01 de 05 — Consultar la organización

Ejercicio 2 — Sucursales de una empresa · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](02-consultar-ubicacion.md)

**Objetivo:** Obtener `<ORG_EMPRESA>`.

**Deja guardado para los siguientes pasos:** `<ORG_EMPRESA>`

---

## 1. Consultar la organización DISTRIBUIDORA EJEMPLO FICTICIA S.A.S. en Party Identity Service

> **Otro servicio:** esta llamada va a **Party Identity Service**, no a Operational Context. No se ejecuta en la validación automática: su resultado se simula.

```http
GET http://localhost:8002/api/v1/organization-identities?search=900
```

**Permiso que exige la URL:** `perm:party-identity:organization_identities:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:organization_identities:read`), `ventas.test` (por `perm:party-identity:organization_identities:read`), `reportes.test` (por `perm:party-identity:organization_identities:read`), `consulta.test` (por `perm:party-identity:organization_identities:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Operational Context **no guarda** la razón social, el nombre comercial ni el NIT de la empresa: solo el `id` de su identidad legal en **Party Identity Service** (DS-01, DS-13).
- Si la organización todavía no existe, se registra primero en Party Identity (`POST /api/v1/organization-identities`) con sus datos legales oficiales.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<ORG_EMPRESA>",
      "identification_type": "NIT",
      "identification_number": "<NIT obtenido del RUT; dato ficticio aquí>",
      "legal_name": "DISTRIBUIDORA EJEMPLO FICTICIA S.A.S.",
      "status": "ACTIVE"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Guardar:** `items[0].id` → `<ORG_EMPRESA>`

---

[Orden del ejercicio](ORDEN.md) · [Paso siguiente →](02-consultar-ubicacion.md)
