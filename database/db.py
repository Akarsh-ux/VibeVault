"""
Vibe Vault — Database Layer (PostgreSQL / psycopg2)

Connection source priority:
  1. DATABASE_URL environment variable (Render production, any PaaS)
  2. Individual DB_HOST / DB_PORT / DB_USER / DB_PASSWORD / DB_NAME env vars
     assembled into a connection URL (local development convenience)

All queries use %s placeholders, which are native to psycopg2.
INSERT statements executed with commit=True automatically use RETURNING id
so callers receive the new row's primary key — transparently replacing
PyMySQL's cursor.lastrowid behaviour.
"""

import os
import re
import psycopg2
import psycopg2.extras
from config import Config

# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def _build_dsn() -> str:
    """
    Return the PostgreSQL DSN / connection URL to use.

    Priority:
      1. DATABASE_URL env var (set by Render and most PaaS platforms)
      2. Construct from individual DB_* env vars (local dev fallback)
    """
    url = os.environ.get('DATABASE_URL', '')
    if url:
        # Render (and some older Heroku-style platforms) may supply
        # "postgres://" which psycopg2 requires as "postgresql://"
        if url.startswith('postgres://'):
            url = url.replace('postgres://', 'postgresql://', 1)
        return url

    # Individual env-var fallback (local development)
    host     = os.environ.get('DB_HOST', 'localhost')
    port     = os.environ.get('DB_PORT', '5432')
    user     = os.environ.get('DB_USER', 'postgres')
    password = os.environ.get('DB_PASSWORD', '')
    dbname   = os.environ.get('DB_NAME', 'vibe_vault')

    # URL-encode the password in case it contains special characters
    from urllib.parse import quote_plus
    encoded_password = quote_plus(password)
    return f"postgresql://{user}:{encoded_password}@{host}:{port}/{dbname}"


def get_pg_connection():
    """
    Open and return a new psycopg2 connection using the resolved DSN.
    Raises RuntimeError if the connection cannot be established.
    """
    dsn = _build_dsn()
    try:
        conn = psycopg2.connect(dsn, connect_timeout=5)
        conn.autocommit = False
        return conn
    except psycopg2.OperationalError as exc:
        raise RuntimeError(
            f"[VibeVault DB] Cannot connect to PostgreSQL.\n"
            f"Check DATABASE_URL or DB_* environment variables.\n"
            f"Original error: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Public query API
# ---------------------------------------------------------------------------

def query_db(query: str, args=(), one: bool = False, commit: bool = False):
    """
    Execute a PostgreSQL query and return results as plain dicts.

    Parameters
    ----------
    query  : SQL string with %s placeholders (psycopg2 style)
    args   : tuple or list of query parameters
    one    : if True, return a single dict (or None) instead of a list
    commit : if True, commit the transaction and return the new row's id
             (for INSERT/UPDATE/DELETE).  INSERT statements automatically
             receive a `RETURNING id` clause appended so the primary key
             is returned to the caller.

    Returns
    -------
    - commit=True  → int (last inserted id or affected rowcount)
    - one=True     → dict | None
    - otherwise    → list[dict]
    """
    conn = get_pg_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if commit:
                # For INSERT statements, append RETURNING id so we get the
                # new primary key back (replaces PyMySQL cursor.lastrowid).
                exec_query = query.rstrip().rstrip(';')
                normalized = exec_query.upper().lstrip()
                if normalized.startswith('INSERT'):
                    exec_query = f"{exec_query} RETURNING id"
                    cur.execute(exec_query, args)
                    conn.commit()
                    row = cur.fetchone()
                    return row['id'] if row else None
                else:
                    cur.execute(exec_query, args)
                    conn.commit()
                    return cur.rowcount
            else:
                cur.execute(query, args)
                rows = cur.fetchall()
                # RealDictRow → plain dict for JSON serialisability
                result = [dict(r) for r in rows]
                if one:
                    return result[0] if result else None
                return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

def init_db():
    """
    Create all required PostgreSQL tables (idempotent — safe to call on
    every startup because the schema uses IF NOT EXISTS).
    """
    print("[VibeVault DB] Initializing PostgreSQL database...")

    schema_path = os.path.join(Config.BASE_DIR, 'database', 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as fh:
        sql_script = fh.read()

    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            # Split on semicolons, skip blank/comment-only chunks
            statements = [s.strip() for s in sql_script.split(';') if s.strip()]
            for stmt in statements:
                # Skip pure comment lines
                if re.match(r'^--', stmt):
                    continue
                try:
                    cur.execute(stmt)
                except Exception as err:
                    # Log but continue — usually harmless "already exists" on
                    # indexes that psycopg2 surfaces as an error even with
                    # IF NOT EXISTS in some edge cases.
                    print(f"[DB Init Notice]: {err}")
                    conn.rollback()
                    # Re-open cursor after rollback
                    cur = conn.cursor()
        conn.commit()
        print("[VibeVault DB] PostgreSQL database initialized successfully!")
    except Exception as exc:
        conn.rollback()
        raise RuntimeError(f"[VibeVault DB] Schema initialization failed: {exc}") from exc
    finally:
        conn.close()
