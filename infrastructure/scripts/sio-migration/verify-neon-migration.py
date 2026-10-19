#!/usr/bin/env python3
"""Verificación de solo lectura de PostgreSQL en Docker frente a Neon."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit, urlunsplit, quote

SERVICES = ('geography', 'party-identity', 'product-catalog', 'operational-context',
            'payment-reference', 'commercial-relationship', 'purchase', 'sales',
            'inventory', 'audit', 'workflow')
IMAGE = 'postgres:18-bookworm'
# Cada respuesta es una fila JSON, por lo que no depende del separador de psql.
META_SQL = r"""
SELECT json_build_object('kind','column','schema',table_schema,'table',table_name,
 'name',column_name,'type',data_type,'udt',udt_schema||'.'||udt_name,
 'nullable',is_nullable,'default',column_default,'ordinal',ordinal_position,
 'identity',identity_generation,'generated',is_generated)::text
FROM information_schema.columns
WHERE table_schema NOT IN ('pg_catalog','information_schema')
ORDER BY table_schema,table_name,ordinal_position;
SELECT json_build_object('kind','constraint','schema',n.nspname,'table',c.relname,
 'name',con.conname,'type',con.contype,'definition',pg_get_constraintdef(con.oid,true))::text
FROM pg_constraint con JOIN pg_class c ON c.oid=con.conrelid
JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%'
ORDER BY n.nspname,c.relname,con.conname;
SELECT json_build_object('kind','index','schema',n.nspname,'table',t.relname,
 'name',i.relname,'definition',pg_get_indexdef(i.oid))::text
FROM pg_index x JOIN pg_class t ON t.oid=x.indrelid
JOIN pg_class i ON i.oid=x.indexrelid JOIN pg_namespace n ON n.oid=t.relnamespace
WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%'
ORDER BY n.nspname,t.relname,i.relname;
SELECT json_build_object('kind','sequence','schema',n.nspname,'name',c.relname,
 'type',s.seqtypid::regtype::text,'start',s.seqstart,'increment',s.seqincrement,
 'min',s.seqmin,'max',s.seqmax,'cache',s.seqcache,'cycle',s.seqcycle)::text
FROM pg_sequence s JOIN pg_class c ON c.oid=s.seqrelid JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname NOT IN ('pg_catalog','information_schema') ORDER BY n.nspname,c.relname;
SELECT json_build_object('kind','table','schema',n.nspname,'name',c.relname,'relkind',c.relkind)::text
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname NOT IN ('pg_catalog','information_schema')
AND n.nspname NOT LIKE 'pg_toast%' AND c.relkind IN ('r','p')
ORDER BY n.nspname,c.relname;
"""

def load_url(env_file):
    if not env_file.is_file():
        raise RuntimeError(f'No se encontró {env_file}')
    for line in env_file.read_text().splitlines():
        match = re.match(r'^\s*(?:export\s+)?NEON_BASE_URL\s*=\s*(.*?)\s*$', line)
        if match:
            val = match.group(1).strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            return val
    raise RuntimeError('Falta NEON_BASE_URL en el archivo .env')

def command(argv, *, sql=None):
    p = subprocess.run(argv, input=sql, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=900)
    if p.returncode:
        # Evitar imprimir mensajes que puedan contener contraseñas/URLs.
        raise RuntimeError('Error al consultar PostgreSQL (revisar Docker, permisos y conexión). '
                           + p.stderr.replace(os.environ.get('SIO_NEON_SECRET', 'not-a-secret'), '[REDACTED]')[:350])
    return p.stdout.splitlines()

def query_local(service, sql):
    container = f'sio-{service}-db'
    return command(['docker','exec','-i',container,'sh','-ec',
         'exec psql -X -qAt -v ON_ERROR_STOP=1 -U "${POSTGRES_USER:-postgres}" '
         '-d "${POSTGRES_DB:-${POSTGRES_USER:-postgres}}" -f -'], sql=sql)

def query_neon(url, sql):
    return command(['docker','run','--rm','--network','host','-i','-e','PGTARGET='+url,
                    IMAGE,'sh','-ec','exec psql "$PGTARGET" -X -qAt -v ON_ERROR_STOP=1 -f -'], sql=sql)

def metadata(rows):
    return [json.loads(row) for row in rows if row.strip()]

def table_count_sql(items):
    def ident(s): return '"' + s.replace('"','""') + '"'
    return '\n'.join("SELECT json_build_object('kind','count','schema'," +
         "'" + t['schema'].replace("'","''") + "','name','" +
         t['name'].replace("'","''") + "','rows',count(*))::text FROM " +
         ident(t['schema'])+'.'+ident(t['name'])+';' for t in items if t['kind']=='table')

def normalize_pg_expression(expr):
    """Normaliza solo la representación ARRAY[varchar] cambiada entre PG 17/18.

    No modifica reglas ni orden de elementos. No se ejecuta SQL.
    """
    if expr is None:
        return None
    # PG18: ('ACTIVE'::character varying)::text  -> 'ACTIVE'::text
    expr = re.sub(r"\(('(?:[^']|''])*')::character varying\)::text", r"\1::text", expr)
    expr = expr.replace("::character varying::text", "::text")
    # PG17: 'ACTIVE'::character varying -> 'ACTIVE'::text
    expr = re.sub(r"('(?:[^']|''])*')::character varying(?!::text)", r"\1::text", expr)
    # PG17: (ARRAY[...] )::text[] and ARRAY[...]::text[] -> ARRAY[...]
    expr = re.sub(r"\(ARRAY\[([^\]]*)\]\)::text\[\]", r"ARRAY[\1]", expr)
    expr = re.sub(r"ARRAY\[([^\]]*)\]::text\[\]", r"ARRAY[\1]", expr)
    # PG17: ARRAY[...typed literals]::text[] and PG18: ARRAY[...text literals]
    # Both now use the same array expression. Parenthesized ARRAY can be
    # present within ANY (...), but these parentheses are not semantically distinct.
    expr = re.sub(r"\(ARRAY\[([^\]]*)\]\)", r"ARRAY[\1]", expr)
    return expr


def normalized_item(item):
    if item is None:
        return None
    item = dict(item)
    if item['kind'] == 'column':
        # Ordinal position is physically stored column order. pg_dump/pg_restore
        # can change it when source tables have previously dropped columns.
        item.pop('ordinal', None)
    elif item['kind'] == 'constraint':
        # PG18 exposes NOT NULL as a named pg_constraint record; PG17 does not.
        if item.get('type') == 'n':
            return None
        item['definition'] = normalize_pg_expression(item['definition'])
        if item.get('type') == 'f' and item.get('schema') == 'public':
            item['definition'] = item['definition'].replace('REFERENCES public.', 'REFERENCES ')
    elif item['kind'] == 'index':
        item['definition'] = normalize_pg_expression(item['definition'])
    return item


def compare(local, remote):
    def key(item):
        return (item['kind'], item.get('schema',''), item.get('table',''), item.get('name',''))
    left = {key(x): normalized_item(x) for x in local if not (x['kind'] == 'constraint' and x.get('type') == 'n')}
    right = {key(x): normalized_item(x) for x in remote if not (x['kind'] == 'constraint' and x.get('type') == 'n')}
    mismatches = []
    for k in sorted(set(left)|set(right)):
        a, b = left.get(k), right.get(k)
        if a != b:
            mismatches.append({'object':'.'.join(str(x) for x in k if x),
                              'local':a,'neon':b})
    return mismatches

def main():
    parser = argparse.ArgumentParser(description='Validar bases SIO (solo lectura)')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--all', action='store_true')
    group.add_argument('--service', choices=SERVICES)
    parser.add_argument('--env-file', type=Path, default=Path(__file__).with_name('neon-migration.env'))
    parser.add_argument('--report-dir', type=Path, default=Path('backups/neon-migration/verification'))
    args = parser.parse_args()
    url = load_url(args.env_file)
    parts = urlsplit(url)
    if parts.scheme not in ('postgres','postgresql') or not parts.hostname or not parts.username:
        raise RuntimeError('NEON_BASE_URL debe ser una URL PostgreSQL válida')
    services = SERVICES if args.all else (args.service,)
    results = []
    for service in services:
        database = 'sio_' + service.replace('-','_') + '_dev'
        dest = urlunsplit((parts.scheme,parts.netloc,'/'+quote(database),parts.query,parts.fragment))
        os.environ['SIO_NEON_SECRET'] = dest
        print(f'[{service}] Comparando Docker con Neon ({database})...', flush=True)
        try:
            local = metadata(query_local(service, META_SQL))
            remote = metadata(query_neon(dest, META_SQL))
            tables = [x for x in local if x['kind']=='table']
            local += metadata(query_local(service, table_count_sql(tables)))
            remote += metadata(query_neon(dest, table_count_sql([x for x in remote if x['kind']=='table'])))
            # Alembic se compara mediante el conteo y también leyendo sus revisiones.
            for side, runner in ((local,lambda sql: query_local(service, sql)),
                                 (remote,lambda sql: query_neon(dest, sql))):
                alembics = [t for t in side if t['kind']=='table' and t['name']=='alembic_version']
                for table in alembics:
                    schema = '"'+table['schema'].replace('"','""')+'"'
                    sql = ("SELECT json_build_object('kind','alembic','schema',"+
                           "'"+table['schema'].replace("'","''")+"','name','alembic_version',"+
                           "'revisions',coalesce(json_agg(version_num ORDER BY version_num),'[]'::json))::text " +
                           f'FROM {schema}.alembic_version;')
                    side.extend(metadata(runner(sql)))
            mismatches = compare(local,remote)
            result = {'service':service,'database':database,'status':'OK' if not mismatches else 'DIFFERENCES',
                      'tables_local':len(tables),'tables_neon':sum(x['kind']=='table' for x in remote),
                      'differences':mismatches}
            print(f'[{service}] {result["status"]}: {len(mismatches)} diferencias; {len(tables)} tablas locales.')
        except Exception as exc:
            result = {'service':service,'database':database,'status':'ERROR','error':str(exc)}
            print(f'[{service}] ERROR: {exc}', file=sys.stderr)
        results.append(result)
    args.report_dir.mkdir(parents=True,exist_ok=True)
    stamp=dt.datetime.now().strftime('%Y%m%d-%H%M%S')
    report=args.report_dir / f'verify-neon-{stamp}.json'
    report.write_text(json.dumps({'created_at':dt.datetime.now(dt.timezone.utc).isoformat(),
                                   'results':results},ensure_ascii=False,indent=2)+'\n')
    print(f'Informe: {report}')
    print('Nota: se comparan conteos y metadatos; no el contenido fila por fila.')
    return 0 if all(x['status']=='OK' for x in results) else 1

if __name__=='__main__':
    try: sys.exit(main())
    except (RuntimeError,ValueError) as exc:
        print('ERROR: '+str(exc),file=sys.stderr)
        sys.exit(1)
