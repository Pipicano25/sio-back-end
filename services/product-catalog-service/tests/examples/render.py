"""Genera los documentos de docs/ejemplo/ a partir de los ejercicios y de las respuestas reales.

`render_exercise` y `render_general_document` devuelven {ruta relativa: contenido}. La prueba
`test_examples.py` compara ese resultado con los archivos versionados y, con
`PRODUCT_CATALOG_EXAMPLES_WRITE=1`, los reescribe.
`README.md` y `mapeo-campos-excel.md` se escriben a mano y no se generan.
"""

import json
import re
from collections import OrderedDict

from tests.examples.exercises import EXERCISES
from tests.examples.render_users import permission_lines, render_general, render_users

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
PLACEHOLDER = re.compile(r"<([A-Z0-9_]+)>")
AUDIT = {"created_at", "updated_at", "created_by", "updated_by", "trace_id", "type", "instance", "title"}
STATUS_TEXT = {200: "200 OK", 201: "201 Created", 204: "204 No Content", 409: "409 Conflict", 422: "422 Unprocessable Content"}


# ------------------------------------------------------------------ utilidades

def tokens(path):
    return [t for t in re.split(r"\.(?![^\[]*\])", path) if t]


def pick(obj, paths):
    if not paths or any(not p for p in paths):
        return strip_audit(obj)
    if isinstance(obj, list):
        sub = [p[1:] for p in paths if p and p[0] == "[]"]
        return [pick(item, sub) for item in obj]
    if not isinstance(obj, dict):
        return obj
    groups = OrderedDict()
    for p in paths:
        groups.setdefault(p[0], []).append(p[1:])
    result = {}
    for tok, subs in groups.items():
        is_list = tok.endswith("[]")
        key = tok[:-2] if is_list else tok
        if key not in obj:
            continue
        value = obj[key]
        if is_list and isinstance(value, list):
            result[key] = [pick(item, subs) for item in value]
        else:
            result[key] = pick(value, subs)
    return result


def strip_audit(obj):
    if isinstance(obj, dict):
        return {k: strip_audit(v) for k, v in obj.items() if k not in AUDIT}
    if isinstance(obj, list):
        return [strip_audit(v) for v in obj]
    return obj


def mask(obj, reverse):
    if isinstance(obj, dict):
        return {k: mask(v, reverse) for k, v in obj.items()}
    if isinstance(obj, list):
        masked = [mask(v, reverse) for v in obj]
        # Una lista de solo identificadores la ordena el servicio por UUID, que cambia en cada
        # ejecución; se ordena por nombre de variable para que el documento sea estable.
        if obj and all(isinstance(v, str) and UUID_RE.match(v) for v in obj):
            masked.sort()
        return masked
    if isinstance(obj, str) and UUID_RE.match(obj):
        return f"<{reverse[obj]}>" if obj in reverse else "<id generado>"
    if isinstance(obj, str) and "/" in obj:  # rutas con ids (p. ej. `content_url`, spec 024)
        return "/".join(mask(part, reverse) if UUID_RE.match(part) else part for part in obj.split("/"))
    return obj


def dumps(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2)


def placeholders_in(value):
    found = []
    if isinstance(value, str):
        found += PLACEHOLDER.findall(value)
    elif isinstance(value, dict):
        for v in value.values():
            found += placeholders_in(v)
    elif isinstance(value, list):
        for v in value:
            found += placeholders_in(v)
    return found


def uniq(seq):
    return list(OrderedDict.fromkeys(seq))


def code_list(names):
    return ", ".join(f"`<{n}>`" for n in names)


def is_internal(var):
    return var.startswith("Q_")


# ------------------------------------------------------------------ análisis

def analyze(ex):
    """Qué variables deja y necesita cada paso."""
    produced_by = {}
    info = []
    for index, s in enumerate(ex["steps"]):
        saves, needs = [], []
        for c in s["calls"]:
            for var in placeholders_in(c["path"]) + placeholders_in(c["body"]):
                if var.startswith("DATO_"):
                    continue
                if var not in saves and var not in needs:
                    needs.append(var)
            saves += [v for v in c["save"] if not is_internal(v)]
        saves = uniq(saves)
        external_needs = [v for v in needs if v not in saves]
        from_steps = sorted(set(produced_by[v] for v in external_needs if v in produced_by))
        for v in saves:
            produced_by.setdefault(v, index)
        info.append(dict(saves=saves, needs=external_needs, from_steps=from_steps))
    used_in = OrderedDict()
    for index, s in enumerate(ex["steps"]):
        for v in info[index]["needs"] + [v for c in s["calls"] for v in placeholders_in(c["path"]) + placeholders_in(c["body"]) if not v.startswith("DATO_")]:
            used_in.setdefault(v, [])
            if index not in used_in[v] and produced_by.get(v) != index:
                used_in[v].append(index)
    return info, produced_by, used_in


def step_label(ex, index):
    s = ex["steps"][index]
    return f"[{index + 1:02d}]({s['file']})"


# ------------------------------------------------------------------ render de un paso

def render_call(number, c, record, reverse):
    out = [f"## {number}. {c['title']}", ""]
    if c["external"]:
        service = "Geography Service" if ":8000" in c["path"] else "Party Identity Service"
        out += [f"> **Otro servicio:** esta llamada va a **{service}**, no al catálogo.", ""]
    if c["cond"] and c.get("cond_text"):
        out += [f"> {c['cond_text']}", ""]
    elif c["cond"]:
        var = next(iter(c["save"]))
        out += [
            "> **Solo si la consulta anterior devolvió `\"items\": []`.** Si el grupo ya existía, **omita esta llamada** "
            f"y use como `<{var}>` el `id` que devolvió la consulta.",
            "",
        ]
    out += ["```http", f"{c['method']} {c['path']}", "```", ""]
    if c.get("upload"):
        name = c["upload"]["file_name"]
        out += [
            "Cuerpo `multipart/form-data` con **un solo campo**, `file`, que contiene el archivo de la imagen. Con cURL:",
            "",
            "```bash",
            f'curl -X {c["method"]} "http://localhost:8003{c["path"]}" \\',
            '  -H "Authorization: Bearer $TOKEN" \\',
            f'  -F "file=@{name}"',
            "```",
            "",
        ]
    if c["body"] is not None:
        out += ["```json", dumps(c["body"]), "```", ""]
    permission = (record or {}).get("permission") or c.get("perm")
    if permission:
        out += permission_lines(permission)
    if c["why"]:
        out += ["**Por qué se hace así**", ""]
        out += [f"- {w}" for w in c["why"]]
        out.append("")
    if c["external"] and c.get("sample") is not None:
        extra = f", {c['sample_note']}" if c.get("sample_note") else ""
        out += [f"**Respuesta esperada — `{STATUS_TEXT[c['sample_status']]}`** (abreviada{extra})", "",
                "```json", dumps(c["sample"]), "```", ""]
    elif record and "response" in record:
        status = record["status"]
        response = record["response"]
        shown = pick(response, [tokens(p) for p in c["show"]]) if c["show"] else strip_audit(response)
        shown = mask(shown, reverse)
        label = "Respuesta esperada (error)" if status >= 400 else "Respuesta esperada"
        out += [f"**{label} — `{STATUS_TEXT.get(status, status)}`** (abreviada)", "", "```json", dumps(shown), "```", ""]
    saves = {k: v for k, v in c["save"].items() if not is_internal(k)}
    if saves:
        items = [f"`{where}` → `<{var}>`" for var, where in saves.items()]
        out += ["**Guardar:** " + " · ".join(items), ""]
    if c["note"]:
        out += [c["note"], ""]
    return out


def render_step(ex, index, records, reverse, info):
    s = ex["steps"][index]
    total = len(ex["steps"])
    prev_link = f"[← Paso anterior]({ex['steps'][index - 1]['file']})" if index > 0 else ""
    next_link = f"[Paso siguiente →]({ex['steps'][index + 1]['file']})" if index + 1 < total else ""
    nav = " · ".join(x for x in [prev_link, "[Orden del ejercicio](ORDEN.md)", next_link] if x)
    out = [f"# Paso {index + 1:02d} de {total:02d} — {s['title']}", "", f"{ex['title']} · {nav}", ""]
    out += [f"**Objetivo:** {s['goal']}", ""]
    meta = info[index]
    if meta["needs"]:
        origin = ", ".join(step_label(ex, i) for i in meta["from_steps"])
        out += [f"**Necesita (de pasos anteriores):** {code_list(meta['needs'])}" + (f" — pasos {origin}" if origin else ""), ""]
    if meta["saves"]:
        out += [f"**Deja guardado para los siguientes pasos:** {code_list(meta['saves'])}", ""]
    if s["intro"]:
        out += [s["intro"], ""]
    out += ["---", ""]
    for number, c in enumerate(s["calls"], start=1):
        record = records.get((index, number - 1))
        out += render_call(number, c, record, reverse)
    if s["after"]:
        out += ["---", "", f"> {s['after']}", ""]
    out += ["---", "", nav, ""]
    return "\n".join(out)


# ------------------------------------------------------------------ ORDEN.md y datos del Excel

ORDER_RULES = [
    ("Datos base", "Unidades, empaques, tipos de grupo y fabricante ya existen; todo lo demás usa sus `id`."),
    ("Catálogos antes del producto", "Unidad nueva, marca, categorías y atributos se crean antes, porque el producto y "
     "sus valores los referencian. Una referencia inexistente da `422 REFERENCE_NOT_FOUND`."),
    ("Atributos → categoría", "El atributo se asocia a la categoría antes de registrar valores: un valor solo se "
     "acepta si alguna categoría del producto usa ese atributo (`422 ATTRIBUTE_NOT_APPLICABLE`)."),
    ("Producto → categoría → valores", "Por la misma razón, el producto se clasifica antes de registrar sus valores."),
    ("Presentaciones → códigos de barras", "El código de barras se liga a una presentación, que debe existir antes."),
    ("Grupos", "Son independientes del resto: pueden asignarse en cualquier momento después de crear el producto."),
    ("Verificación al final", "Con todo cargado, el producto debe quedar `is_complete: true`."),
]


def render_order(ex, info, produced_by, used_in):
    out = [f"# {ex['title']}", "", "[← Todos los ejercicios](../README.md)", ""]
    out += [f"**Qué enseña:** {ex['focus']}", ""]
    out += [f"**Filas del Excel:** ID {ex['excel_ids']} — detalle y decisiones en [00-datos-del-excel.md](00-datos-del-excel.md).", ""]
    out += ["Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).", ""]
    out += ["**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL "
            "y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).", ""]
    out += ["## Orden de ejecución", ""]
    out += ["Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.", ""]
    out += ["| Paso | Archivo | Qué hace | Llamadas | Depende de |", "| --- | --- | --- | --- | --- |"]
    out.append("| 00 | [00-datos-del-excel.md](00-datos-del-excel.md) | Leer: qué dice el Excel y cómo se interpreta | — | — |")
    for index, s in enumerate(ex["steps"]):
        deps = ", ".join(f"{i + 1:02d}" for i in info[index]["from_steps"]) or "—"
        out.append(f"| {index + 1:02d} | [{s['file']}]({s['file']}) | {s['goal']} | {len(s['calls'])} | {deps} |")
    out += ["", "## Por qué este orden", ""]
    out += [f"{n}. **{title}.** {text}" for n, (title, text) in enumerate(ORDER_RULES, start=1)]
    if any("inactivar" in s["file"] for s in ex["steps"]):
        out.append(f"{len(ORDER_RULES) + 1}. **Inactivar al final.** Sobre un producto inactivo no se pueden agregar "
                   "elementos (`422 PRODUCT_INACTIVE`); por eso se carga completo y se inactiva de último.")
    out += ["", "## Lista de `id` que debe ir guardando", ""]
    out += ["| Variable | Se obtiene en | Se usa en |", "| --- | --- | --- |"]
    for var, index in produced_by.items():
        uses = ", ".join(f"{i + 1:02d}" for i in used_in.get(var, [])) or "—"
        out.append(f"| `<{var}>` | {index + 1:02d} | {uses} |")
    out += ["", "Las variables con `—` no se usan más en este ejercicio, pero conviene guardarlas: son las que se "
            "necesitan para corregir o inactivar ese registro después.", ""]
    out += ["## Resultado esperado", ""]
    last = ex["steps"][-1]
    out += [f"Al terminar el paso {len(ex['steps']):02d} ([{last['file']}]({last['file']})) el producto queda como se describe allí.", ""]
    out += ["[Empezar → paso 01](" + ex["steps"][0]["file"] + ")", ""]
    return "\n".join(out)


def render_excel(ex):
    out = [f"# Datos del Excel — {ex['title']}", "", "[← Orden del ejercicio](ORDEN.md)", ""]
    out += ["Fuente: `docs/CAMPOS PRODUCTOS.xlsx`, hoja `Hoja1`.", ""]
    out += ["## Lo que dice el Excel", "", "| Columna | Valor |", "| --- | --- |"]
    out += [f"| {k} | {v} |" for k, v in ex["excel"]]
    out += ["", "## Cómo se interpreta en el catálogo", "", "| Tema | Decisión |", "| --- | --- |"]
    out += [f"| {k} | {v} |" for k, v in ex["interpretation"]]
    out += ["", "Referencia general de columnas: [../mapeo-campos-excel.md](../mapeo-campos-excel.md).", "",
            "[Empezar → paso 01](" + ex["steps"][0]["file"] + ")", ""]
    return "\n".join(out)


# ------------------------------------------------------------------ principal

def render_exercise(ex, ctx, record_list):
    """Documentos de un ejercicio: {ruta relativa a docs/ejemplo/: contenido}."""
    reverse = {}
    for var, value in ctx.items():
        if isinstance(value, str) and UUID_RE.match(value) and not is_internal(var):
            reverse.setdefault(value, var)
    records = index_records(record_list)
    info, produced_by, used_in = analyze(ex)
    folder = ex["folder"]
    documents = {
        f"{folder}/ORDEN.md": render_order(ex, info, produced_by, used_in),
        f"{folder}/00-datos-del-excel.md": render_excel(ex),
    }
    for index, s in enumerate(ex["steps"]):
        documents[f"{folder}/{s['file']}"] = render_step(ex, index, records, reverse, info)
    documents[f"{folder}/USUARIOS.md"] = render_users(ex, records)
    return documents


def render_general_document(record_lists):
    """`usuarios-y-permisos.md` a partir de los registros de todos los ejercicios (en orden)."""
    return render_general(EXERCISES, [index_records(records) for records in record_lists])


def index_records(record_list):
    return {(r["step"], r["call"]): r for r in record_list}
