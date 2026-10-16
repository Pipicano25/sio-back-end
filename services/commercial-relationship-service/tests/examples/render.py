"""Genera los documentos de docs/ejemplo/ a partir de los ejercicios y de las respuestas reales.

`render_exercise` y `render_general_document` devuelven {ruta relativa: contenido}. La prueba
`test_examples.py` compara ese resultado con los archivos versionados y, con
`COMMERCIAL_RELATIONSHIP_EXAMPLES_WRITE=1`, los reescribe. `README.md` se escribe a mano.
"""

import json
import re
from collections import OrderedDict

from tests.examples.exercises import EXERCISES
from tests.examples.render_users import permission_lines, render_general, render_users

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
PLACEHOLDER = re.compile(r"<([A-Z0-9_]+)>")
AUDIT = {"created_at", "updated_at", "created_by", "updated_by", "trace_id", "type", "instance", "title",
         "valid_from"}
TIMESTAMP_KEYS = {"valid_to", "assigned_at", "deactivated_at"}
STATUS_TEXT = {200: "200 OK", 201: "201 Created", 409: "409 Conflict", 422: "422 Unprocessable Content"}


def data_file(ex):
    """Archivo de datos del ejercicio: `00-datos-del-excel.md` (fuente real) o `00-datos-ficticios.md`."""
    return ex.get("data_file", "00-datos-ficticios.md")


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
        return {
            k: ("<fecha y hora del cambio>" if k in TIMESTAMP_KEYS and v else mask(v, reverse))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [mask(v, reverse) for v in obj]
    if isinstance(obj, str) and UUID_RE.match(obj):
        return f"<{reverse[obj]}>" if obj in reverse else "<id generado>"
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


# ------------------------------------------------------------------ análisis

def analyze(ex):
    """Qué variables deja y necesita cada paso."""
    produced_by = {}
    info = []
    for index, s in enumerate(ex["steps"]):
        saves, needs = [], []
        for c in s["calls"]:
            for var in placeholders_in(c["path"]) + placeholders_in(c["body"]) + placeholders_in(c.get("params")):
                if var not in saves and var not in needs:
                    needs.append(var)
            saves += list(c["save"])
        saves = uniq(saves)
        external_needs = [v for v in needs if v not in saves]
        from_steps = sorted(set(produced_by[v] for v in external_needs if v in produced_by))
        for v in saves:
            produced_by.setdefault(v, index)
        info.append(dict(saves=saves, needs=external_needs, from_steps=from_steps))
    used_in = OrderedDict()
    for index, s in enumerate(ex["steps"]):
        for c in s["calls"]:
            for v in placeholders_in(c["path"]) + placeholders_in(c["body"]):
                used_in.setdefault(v, [])
                if index not in used_in[v] and produced_by.get(v) != index:
                    used_in[v].append(index)
    return info, produced_by, used_in


def step_label(ex, index):
    s = ex["steps"][index]
    return f"[{index + 1:02d}]({s['file']})"


# ------------------------------------------------------------------ render de un paso

def render_process(number, c, record, reverse):
    out = [f"## {number}. {c['title']}", ""]
    out += ["> **Proceso automático:** no es una llamada que haga el usuario. En un entorno real lo hacen Purchase (al "
            "registrar la recepción física) y el `commercial-relationship-price-worker`; en la validación automática lo "
            "ejecuta la prueba.", ""]
    if c["why"]:
        out += ["**Qué ocurre**", ""]
        out += [f"- {w}" for w in c["why"]]
        out.append("")
    if record and "response" in record:
        shown = pick(record["response"], [tokens(p) for p in c["show"]]) if c["show"] else record["response"]
        out += ["**Resultado**", "", "```json", dumps(mask(shown, reverse)), "```", ""]
    if c["save"]:
        items = [f"`{where}` → `<{var}>`" for var, where in c["save"].items()]
        out += ["**Guardar:** " + " · ".join(items), ""]
    if c["note"]:
        out += [c["note"], ""]
    return out


def render_call(number, c, record, reverse):
    if c.get("process"):
        return render_process(number, c, record, reverse)
    out = [f"## {number}. {c['title']}", ""]
    if c["external"]:
        out += [f"> **Otro servicio:** esta llamada va a **{c['external']}**, no a Commercial Relationship. "
                "No se ejecuta en la validación automática: su resultado se simula.", ""]
    out += ["```http", f"{c['method']} {c['path']}", "```", ""]
    if c["body"] is not None:
        out += ["```json", dumps(c["body"]), "```", ""]
    permission = (record or {}).get("permission") or c.get("perm")
    if permission:
        also = (record or {}).get("also", c.get("also", []))
        out += permission_lines([permission, *also], c)
    if c["why"]:
        out += ["**Por qué se hace así**", ""]
        out += [f"- {w}" for w in c["why"]]
        out.append("")
    if c["external"] and c.get("sample") is not None:
        out += [f"**Respuesta esperada — `{STATUS_TEXT[c['sample_status']]}`** (abreviada)", "",
                "```json", dumps(c["sample"]), "```", ""]
    elif record and "response" in record:
        status = record["status"]
        response = record["response"]
        shown = pick(response, [tokens(p) for p in c["show"]]) if c["show"] else strip_audit(response)
        shown = mask(shown, reverse)
        label = "Respuesta esperada (error)" if status >= 400 else "Respuesta esperada"
        out += [f"**{label} — `{STATUS_TEXT.get(status, status)}`** (abreviada)", "", "```json", dumps(shown), "```", ""]
    if c["save"]:
        items = [f"`{where}` → `<{var}>`" for var, where in c["save"].items()]
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


# ------------------------------------------------------------------ ORDEN.md y datos

def render_order(ex, info, produced_by, used_in):
    out = [f"# {ex['title']}", "", "[← Todos los ejercicios](../README.md)", ""]
    out += [f"**Qué enseña:** {ex['focus']}", ""]
    kind = "**reales** del sistema anterior (`docs/CAMPOS PRODUCTOS.xlsx`)" if ex.get("real_data") else "**ficticios**"
    out += [f"**Datos:** {kind} — detalle y decisiones en [{data_file(ex)}]({data_file(ex)}).", ""]
    out += ["Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).", ""]
    out += ["**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL "
            "y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).", ""]
    out += ["## Orden de ejecución", ""]
    out += ["Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.", ""]
    out += ["| Paso | Archivo | Qué hace | Llamadas | Depende de |", "| --- | --- | --- | --- | --- |"]
    what = "las filas del Excel" if ex.get("real_data") else "los datos ficticios"
    out.append(f"| 00 | [{data_file(ex)}]({data_file(ex)}) | Leer: {what} y cómo se interpretan | — | — |")
    for index, s in enumerate(ex["steps"]):
        deps = ", ".join(f"{i + 1:02d}" for i in info[index]["from_steps"]) or "—"
        out.append(f"| {index + 1:02d} | [{s['file']}]({s['file']}) | {s['goal']} | {len(s['calls'])} | {deps} |")
    out += ["", "## Por qué este orden", ""]
    out += [f"{n}. **{title}.** {text}" for n, (title, text) in enumerate(ex["order_rules"], start=1)]
    out += ["", "## Lista de `id` que debe ir guardando", ""]
    out += ["| Variable | Se obtiene en | Se usa en |", "| --- | --- | --- |"]
    for var, index in produced_by.items():
        uses = ", ".join(f"{i + 1:02d}" for i in used_in.get(var, [])) or "—"
        out.append(f"| `<{var}>` | {index + 1:02d} | {uses} |")
    out += ["", "[Empezar → paso 01](" + ex["steps"][0]["file"] + ")", ""]
    return "\n".join(out)


def render_data(ex):
    out = [f"# Datos del ejercicio — {ex['title']}", "", "[← Orden del ejercicio](ORDEN.md)", ""]
    if ex.get("real_data"):
        out += ["> **Datos reales del sistema anterior.** Los productos son filas de `docs/CAMPOS PRODUCTOS.xlsx` "
                "(se cita la fila de cada uno). Mapeo de columnas: [../mapeo-campos-excel.md](../mapeo-campos-excel.md). "
                "La empresa y los datos marcados como **ficticios** son inventados.", ""]
    else:
        out += ["> **Datos ficticios.** No existe una fuente del sistema anterior para clientes y proveedores. Las "
                "personas, organizaciones y empresas de este ejercicio son **inventadas** y no corresponden a "
                "entidades reales. Commercial Relationship no guarda NIT, razón social ni documentos: esos datos "
                "legales viven en Party Identity y en un entorno real se toman de una fuente oficial (RUT, RUES).", ""]
    out += ["## Datos usados", "", "| Dato | Valor |", "| --- | --- |"]
    out += [f"| {k} | {v} |" for k, v in ex["data"]]
    out += ["", "## Cómo se interpretan", "", "| Tema | Decisión |", "| --- | --- |"]
    out += [f"| {k} | {v} |" for k, v in ex["interpretation"]]
    out += ["", "[Empezar → paso 01](" + ex["steps"][0]["file"] + ")", ""]
    return "\n".join(out)


# ------------------------------------------------------------------ principal

def render_exercise(ex, ctx, record_list):
    """Documentos de un ejercicio: {ruta relativa a docs/ejemplo/: contenido}."""
    reverse = {}
    for var, value in ctx.items():
        if isinstance(value, str) and UUID_RE.match(value):
            reverse.setdefault(value, var)
    records = index_records(record_list)
    info, produced_by, used_in = analyze(ex)
    folder = ex["folder"]
    documents = {
        f"{folder}/ORDEN.md": render_order(ex, info, produced_by, used_in),
        f"{folder}/{data_file(ex)}": render_data(ex),
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
