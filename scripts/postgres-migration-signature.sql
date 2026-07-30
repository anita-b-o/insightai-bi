\set ON_ERROR_STOP on
\pset tuples_only on
\pset format unaligned
\pset fieldsep '|'

SELECT 'ALEMBIC', version_num
FROM public.alembic_version
ORDER BY version_num;

SELECT 'EXTENSION', extname, extversion
FROM pg_extension
WHERE extname <> 'plpgsql'
ORDER BY extname;

SELECT
    'COLUMN',
    n.nspname || '.' || c.relname,
    a.attnum,
    a.attname,
    pg_catalog.format_type(a.atttypid, a.atttypmod),
    a.attnotnull,
    COALESCE(pg_get_expr(d.adbin, d.adrelid), ''),
    a.attidentity,
    a.attgenerated
FROM pg_attribute a
JOIN pg_class c ON c.oid = a.attrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
WHERE n.nspname = 'public'
  AND c.relkind IN ('r', 'p')
  AND a.attnum > 0
  AND NOT a.attisdropped
ORDER BY n.nspname, c.relname, a.attnum;

SELECT
    'CONSTRAINT',
    n.nspname || '.' || c.relname,
    con.conname,
    con.contype,
    pg_get_constraintdef(con.oid, true)
FROM pg_constraint con
JOIN pg_class c ON c.oid = con.conrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
ORDER BY n.nspname, c.relname, con.conname;

SELECT
    'INDEX',
    n.nspname || '.' || tbl.relname,
    idx.relname,
    i.indisprimary,
    i.indisunique,
    pg_get_indexdef(idx.oid)
FROM pg_index i
JOIN pg_class idx ON idx.oid = i.indexrelid
JOIN pg_class tbl ON tbl.oid = i.indrelid
JOIN pg_namespace n ON n.oid = tbl.relnamespace
WHERE n.nspname = 'public'
ORDER BY n.nspname, tbl.relname, idx.relname;

SELECT
    'SEQUENCE',
    schemaname || '.' || sequencename,
    data_type,
    start_value,
    min_value,
    max_value,
    increment_by,
    cycle,
    cache_size
FROM pg_sequences
WHERE schemaname = 'public'
ORDER BY schemaname, sequencename;

SELECT format(
    'SELECT %L, %L, last_value, is_called FROM %I.%I;',
    'SEQUENCE_STATE',
    schemaname || '.' || sequencename,
    schemaname,
    sequencename
)
FROM pg_sequences
WHERE schemaname = 'public'
ORDER BY schemaname, sequencename
\gexec

SELECT format(
    'SELECT %L, %L, count(*)::bigint FROM %I.%I;',
    'ROWS',
    n.nspname || '.' || c.relname,
    n.nspname,
    c.relname
)
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relkind = 'r'
ORDER BY n.nspname, c.relname
\gexec

SELECT format(
    'SELECT %L, %L, count(*)::bigint, md5(COALESCE(string_agg(row_to_json(t)::text, E''\n'' ORDER BY row_to_json(t)::text COLLATE "C"), '''')) FROM %I.%I AS t;',
    'CONTENT_MD5',
    n.nspname || '.' || c.relname,
    n.nspname,
    c.relname
)
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relkind = 'r'
ORDER BY n.nspname, c.relname
\gexec
