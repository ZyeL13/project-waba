# db.py (versi terbaru)
import aiosqlite
import asyncio

DB_PATH = "bot.db"
_lock = asyncio.Lock()
_conn: aiosqlite.Connection | None = None

async def get_connection() -> aiosqlite.Connection:
    global _conn
    if _conn is None:
        async with _lock:
            if _conn is None:
                _conn = await aiosqlite.connect(DB_PATH)
                _conn.row_factory = aiosqlite.Row
                await _conn.execute("PRAGMA journal_mode=WAL")
                await _conn.commit()
    return _conn

async def init_db():
    db = await get_connection()
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            role TEXT NOT NULL DEFAULT 'guest'
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS command_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            command TEXT NOT NULL,
            args TEXT,
            timestamp REAL
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            item TEXT NOT NULL,
            ts REAL
        )
    """)
    await db.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS file_index USING fts5(
            filepath,
            content,
            tokenize='unicode61'
        )
    """)
    await db.commit()

async def execute_write(sql: str, params=()):
    db = await get_connection()
    async with _lock:
        await db.execute(sql, params)
        await db.commit()
