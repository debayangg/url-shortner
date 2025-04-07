import os
import asyncio
import asyncpg
import sqlite3
from dotenv import load_dotenv

load_dotenv()

POSTGRES_URI = os.getenv("POSTGRES_URI")
if not POSTGRES_URI:
    raise EnvironmentError("POSTGRES_URI not set in environment.")
background_tasks = set()

pool = None

async def init_pool():
    """Initialize the asyncpg pool once at startup."""
    global pool
    pool = await asyncpg.create_pool(
        dsn=POSTGRES_URI,
        min_size=1,
        max_size=10,
        statement_cache_size=0
    )
    print("Asyncpg pool initialized.")

async def ensure_pool():
    """Ensure that the pool is initialized."""
    global pool
    if pool is None:
        await init_pool()

def _create_task(coro):
    """Create a background task and track it."""
    global background_tasks
    task = asyncio.create_task(coro)
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    return task

# --- Local SQLite Setup ---
conn = sqlite3.connect('urls.db', check_same_thread=False)
conn.execute("PRAGMA journal_mode=WAL;")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS url (
    code TEXT PRIMARY KEY,
    link TEXT NOT NULL
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value INTEGER NOT NULL
)
""")
conn.commit()

# --- Async wrapper for supabase/postgres queries ---

async def _insert_url_pg(code: str, link: str):
    await ensure_pool()
    async with pool.acquire() as conn_pg:
        async with conn_pg.transaction():
            await conn_pg.execute(
                "INSERT INTO url (code, link) VALUES ($1, $2) ON CONFLICT (code) DO NOTHING",
                code, link
            )

async def _delete_url_pg(code: str):
    await ensure_pool()
    async with pool.acquire() as conn_pg:
        async with conn_pg.transaction():
            await conn_pg.execute(
                "DELETE FROM url WHERE code = $1", code
            )

async def _set_setting_pg(key: str, value: int):
    await ensure_pool()
    async with pool.acquire() as conn_pg:
        async with conn_pg.transaction():
            await conn_pg.execute("""
                INSERT INTO settings (key, value)
                VALUES ($1, $2)
                ON CONFLICT (key)
                DO UPDATE SET value = EXCLUDED.value
            """, key, value)

# --- Public API ---

async def insert_url(code: str, link: str):
    # First update local db fast
    cursor.execute("INSERT INTO url (code, link) VALUES (?, ?) ON CONFLICT(code) DO NOTHING", (code, link))
    conn.commit()
    # Then separately run postgres update
    _create_task(_insert_url_pg(code, link))

async def delete_url(code: str):
    cursor.execute("DELETE FROM url WHERE code = ?", (code,))
    conn.commit()
    _create_task(_delete_url_pg(code))

async def set_setting(key: str, value: int):
    cursor.execute("""
    INSERT INTO settings (key, value) VALUES (?, ?)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, value))
    conn.commit()
    _create_task(_set_setting_pg(key, value))

def get_link(code: str) -> str:
    cursor.execute("SELECT link FROM url WHERE code = ?", (code,))
    row = cursor.fetchone()
    return row[0] if row else None

def get_url_codes() -> list[str]:
    cursor.execute("SELECT code FROM url ORDER BY code")
    rows = cursor.fetchall()
    return [row[0] for row in rows] if rows else None

def get_setting(key: str) -> int:
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    return row[0] if row else 0

async def full_sync():
    """Sync data from Supabase/Postgres to local SQLite."""
    await ensure_pool()
    async with pool.acquire() as conn_pg:
        print("Starting full sync from Supabase to SQLite...")

        # Sync url table
        urls = await conn_pg.fetch("SELECT code, link FROM url")
        cursor.execute("DELETE FROM url")
        conn.commit()
        cursor.executemany(
            "INSERT INTO url (code, link) VALUES (?, ?)",
            [(r['code'], r['link']) for r in urls]
        )
        conn.commit()

        # Sync settings table
        settings = await conn_pg.fetch("SELECT key, value FROM settings")
        cursor.execute("DELETE FROM settings")
        conn.commit()
        cursor.executemany(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            [(r['key'], r['value']) for r in settings]
        )
        conn.commit()

    print("Full sync completed.")
