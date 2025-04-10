import os
import asyncio
import asyncpg
import aiosqlite
from dotenv import load_dotenv

load_dotenv()

POSTGRES_URI = os.getenv("POSTGRES_URI")
if not POSTGRES_URI:
    raise EnvironmentError("POSTGRES_URI not set in environment.")

background_tasks = set()
pool = None
sqlite_db = None

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

async def init_sqlite():
    """Initialize the aiosqlite connection once at startup."""
    global sqlite_db
    sqlite_db = await aiosqlite.connect('urls.db')
    await sqlite_db.execute("PRAGMA journal_mode=WAL;")
    await sqlite_db.execute("""
    CREATE TABLE IF NOT EXISTS url (
        code TEXT PRIMARY KEY,
        link TEXT NOT NULL
    )
    """)
    await sqlite_db.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value INTEGER NOT NULL
    )
    """)
    await sqlite_db.commit()
    print("SQLite DB initialized.")

async def ensure_pool():
    """Ensure that the pool is initialized."""
    global pool
    if pool is None:
        await init_pool()

async def ensure_sqlite():
    """Ensure that the SQLite DB is initialized."""
    global sqlite_db
    if sqlite_db is None:
        await init_sqlite()

def _create_task(coro):
    """Create a background task and track it."""
    global background_tasks
    task = asyncio.create_task(coro)
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    return task

# --- Async wrapper for Postgres queries ---

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
    await ensure_sqlite()
    await sqlite_db.execute(
        "INSERT INTO url (code, link) VALUES (?, ?) ON CONFLICT(code) DO NOTHING",
        (code, link)
    )
    await sqlite_db.commit()
    _create_task(_insert_url_pg(code, link))

async def delete_url(code: str):
    await ensure_sqlite()
    await sqlite_db.execute(
        "DELETE FROM url WHERE code = ?",
        (code,)
    )
    await sqlite_db.commit()
    _create_task(_delete_url_pg(code))

async def set_setting(key: str, value: int):
    await ensure_sqlite()
    await sqlite_db.execute("""
    INSERT INTO settings (key, value) VALUES (?, ?)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, value))
    await sqlite_db.commit()
    _create_task(_set_setting_pg(key, value))

async def get_link(code: str) -> str | None:
    await ensure_sqlite()
    async with sqlite_db.execute(
        "SELECT link FROM url WHERE code = ?",
        (code,)
    ) as cursor:
        row = await cursor.fetchone()
        return row[0] if row else None

async def get_url_codes() -> list[str] | None:
    await ensure_sqlite()
    async with sqlite_db.execute(
        "SELECT code FROM url ORDER BY code"
    ) as cursor:
        rows = await cursor.fetchall()
        return [row[0] for row in rows] if rows else None

async def get_url_mappings() -> dict[str, str]:
    """Return a dictionary of code -> link mappings."""
    await ensure_sqlite()
    mappings = {}
    async with sqlite_db.execute(
        "SELECT code, link FROM url"
    ) as cursor:
        async for row in cursor:
            mappings[row[0]] = row[1]
    return mappings

async def get_setting(key: str) -> int:
    await ensure_sqlite()
    async with sqlite_db.execute(
        "SELECT value FROM settings WHERE key = ?",
        (key,)
    ) as cursor:
        row = await cursor.fetchone()
        return row[0] if row else 0

async def full_sync():
    """Sync data from Supabase/Postgres to local SQLite."""
    await ensure_sqlite()
    await ensure_pool()
    async with pool.acquire() as conn_pg:
        print("Starting full sync from Supabase to SQLite...")

        # Sync url table
        urls = await conn_pg.fetch("SELECT code, link FROM url")
        await sqlite_db.execute("DELETE FROM url")
        await sqlite_db.executemany(
            "INSERT INTO url (code, link) VALUES (?, ?)",
            [(r['code'], r['link']) for r in urls]
        )

        # Sync settings table
        settings = await conn_pg.fetch("SELECT key, value FROM settings")
        await sqlite_db.execute("DELETE FROM settings")
        await sqlite_db.executemany(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            [(r['key'], r['value']) for r in settings]
        )

        await sqlite_db.commit()
    print("Full sync completed.")
