# Paso 07 de 12 — Permisos: el empleado no crea empresas

Ejercicio 7 — Seguridad entre empresas y permisos · [Orden del ejercicio](ORDEN.md)

---

## 1. operario.dao (Empleado) intenta crear una empresa

Paso `S-01` · usuario **`operario.dao`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8104/api/v1/companies
```

```json
{}
```

**Permiso que exige la URL:** `perm:operational-context:companies:create`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:operational-context:all:create`)

**Respuesta esperada:** `403`
