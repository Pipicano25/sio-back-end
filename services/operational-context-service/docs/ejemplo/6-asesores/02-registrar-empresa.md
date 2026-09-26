# Paso 02 de 05 — Registrar la empresa

Ejercicio 6 — Asesores de la empresa · [← Paso anterior](01-consultar-datos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-registrar-asesores.md)

**Objetivo:** Crear la empresa asesorada.

**Necesita (de pasos anteriores):** `<ORG_EMPRESA>` — pasos [01](01-consultar-datos.md)

**Deja guardado para los siguientes pasos:** `<EMPRESA>`

---

## 1. Registrar la empresa

```http
POST /api/v1/companies
```

```json
{
  "organization_identity_id": "<ORG_EMPRESA>"
}
```

**Permisos que exige la URL (todos):** `perm:operational-context:companies:create` + `perm:operational-context:platform:administer`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `operational-context` solo tiene `create`, `read`, `update`; le falta `administer`; `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `create`
- ℹ️ Para registrar o cambiar la organización o la ubicación, el token del usuario debe poder además **leer** en Party Identity y Geography: el servicio valida esas referencias con el mismo token. `administradores` y `supervisores` tienen esa lectura.
- ℹ️ Alcance de plataforma (Fase B, DS-05): registrar, inactivar y reactivar empresas y ver todas las empresas sin ser miembro. Solo lo concede `perm:all:all:all` (`administradores`); los comodines de lectura, creación o modificación **no** lo conceden.

**Por qué se hace así**

- Solo el administrador de plataforma registra empresas.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<EMPRESA>",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<EMPRESA>`

---

[← Paso anterior](01-consultar-datos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-registrar-asesores.md)
