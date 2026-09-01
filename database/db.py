"""
Vibe Vault — Database Layer (MySQL / PyMySQL)

Connection source priority:
  1. DATABASE_URL / MYSQL_URL / JAWSDB_URL / CLEARDB_DATABASE_URL
     (Render, Railway, Heroku, AWS RDS, Docker, and other PaaS)
  2. Individual DB_HOST / DB_PORT / DB_USER / DB_PASSWORD / DB_NAME env vars
     (Local development convenience)

All queries use %s placeholders, which are native to PyMySQL and standard DB-API 2.0.
INSERT statements executed with commit=True return cursor.lastrowid (the new row's primary key).
UPDATE and DELETE statements return cursor.rowcount.
"""

import os
import re
from urllib.parse import urlparse, unquote
import pymysql
import pymysql.cursors
from config import Config


# ---------------------------------------------------------------------------
# Connection parameter resolution
# ---------------------------------------------------------------------------

def _get_db_params():
    """
    Parse database connection parameters from environment.
    Supports standard MySQL URLs and individual environment variables.
    """
    # Check URL env vars commonly used across PaaS providers
    url = (
        os.environ.get('DATABASE_URL')
        or os.environ.get('MYSQL_URL')
        or os.environ.get('JAWSDB_URL')
        or os.environ.get('CLEARDB_DATABASE_URL')
        or ''
    )

    if url and (url.startswith('mysql://') or url.startswith('mysql+pymysql://')):
        # Strip pymysql prefix if present
        if url.startswith('mysql+pymysql://'):
            url = url.replace('mysql+pymysql://', 'mysql://', 1)

        parsed = urlparse(url)
        return {
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 3306,
            'user': unquote(parsed.username) if parsed.username else 'root',
            'password': unquote(parsed.password) if parsed.password else '',
            'database': parsed.path.lstrip('/') if parsed.path else 'vibe_vault'
        }

    # Fallback to individual environment variables
    return {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'port': int(os.environ.get('DB_PORT', 3306)),
        'user': os.environ.get('DB_USER', 'root'),
        'password': os.environ.get('DB_PASSWORD', ''),
        'database': os.environ.get('DB_NAME', 'vibe_vault')
    }


def get_db_connection(include_db: bool = True):
    """
    Open and return a new PyMySQL connection.
    
    Parameters
    ----------
    include_db : bool
        If True, connects directly to the target database.
        If False, connects to the server without selecting a DB (used for CREATE DATABASE).
    """
    params = _get_db_params()
    connect_kwargs = {
        'host': params['host'],
        'port': params['port'],
        'user': params['user'],
        'password': params['password'],
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor,
        'autocommit': False,
        'connect_timeout': 10
    }

    if include_db and params['database']:
        connect_kwargs['database'] = params['database']

    try:
        conn = pymysql.connect(**connect_kwargs)
        return conn
    except pymysql.MySQLError as exc:
        raise RuntimeError(
            f"[VibeVault DB] Cannot connect to MySQL server at {params['host']}:{params['port']}.\n"
            f"Check DATABASE_URL or DB_* environment variables in your .env file.\n"
            f"Original error: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Public query API
# ---------------------------------------------------------------------------

def query_db(query: str, args=(), one: bool = False, commit: bool = False):
    """
    Execute a MySQL query and return results as plain dicts.

    Parameters
    ----------
    query  : SQL string with %s placeholders
    args   : tuple or list of query parameters
    one    : if True, return a single dict (or None) instead of a list
    commit : if True, commit the transaction and return:
             - for INSERT: the new row's auto_increment id (cursor.lastrowid)
             - for UPDATE / DELETE: the affected row count (cursor.rowcount)

    Returns
    -------
    - commit=True  → int (last inserted id or affected rowcount)
    - one=True     → dict | None
    - otherwise    → list[dict]
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, args)
            if commit:
                conn.commit()
                normalized = query.strip().upper()
                if normalized.startswith('INSERT'):
                    return cur.lastrowid
                return cur.rowcount
            else:
                rows = cur.fetchall()
                if one:
                    return rows[0] if rows else None
                return list(rows) if rows else []
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
    Create database (if not exists) and all required MySQL tables idempotently.
    Safe to call on every startup because schema uses IF NOT EXISTS.
    """
    print("[VibeVault DB] Initializing MySQL database...")
    params = _get_db_params()
    dbname = params['database']

    # Step 1: Ensure database exists
    try:
        server_conn = get_db_connection(include_db=False)
        try:
            with server_conn.cursor() as cur:
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{dbname}` "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
                )
            server_conn.commit()
        finally:
            server_conn.close()
    except Exception as err:
        print(f"[VibeVault DB Notice] Database creation check: {err}")

    # Step 2: Execute schema.sql tables & indexes
    schema_path = os.path.join(Config.BASE_DIR, 'database', 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as fh:
        sql_script = fh.read()

    conn = get_db_connection(include_db=True)
    try:
        with conn.cursor() as cur:
            # Split on semicolons, skip blank and comment-only chunks
            statements = [s.strip() for s in sql_script.split(';') if s.strip()]
            for stmt in statements:
                # Remove leading comments
                clean_stmt = re.sub(r'^--.*$', '', stmt, flags=re.MULTILINE).strip()
                if not clean_stmt:
                    continue
                try:
                    cur.execute(clean_stmt)
                except Exception as err:
                    print(f"[DB Init Notice]: {err}")
        conn.commit()
        print("[VibeVault DB] MySQL database initialized successfully!")
    except Exception as exc:
        conn.rollback()
        raise RuntimeError(f"[VibeVault DB] Schema initialization failed: {exc}") from exc
    finally:
        conn.close()
