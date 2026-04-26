# auth.py
import aiosqlite
import asyncio

DB_PATH = "bot.db"  # nanti bisa diubah lewat config

# Lock global untuk inisialisasi DB
_db_lock = asyncio.Lock()
_db_conn: aiosqlite.Connection | None = None

async def get_db() -> aiosqlite.Connection:
    global _db_conn
    if _db_conn is None:
        async with _db_lock:
            if _db_conn is None:  # double-check
                _db_conn = await aiosqlite.connect(DB_PATH)
                _db_conn.row_factory = aiosqlite.Row
                await _db_conn.execute("PRAGMA journal_mode=WAL")
                await _db_conn.execute(
                    """CREATE TABLE IF NOT EXISTS users (
                        user_id TEXT PRIMARY KEY,
                        role TEXT NOT NULL DEFAULT 'guest'
                    )"""
                )
                await _db_conn.commit()
    return _db_conn

async def init_db():
    """Panggil saat startup untuk memastikan DB siap"""
    await get_db()

async def check_role(user_id: str, required_role: str) -> bool:
    db = await get_db()
    async with db.execute("SELECT role FROM users WHERE user_id = ?", (user_id,)) as cursor:
        row = await cursor.fetchone()
    return row is not None and row["role"] == required_role

async def add_user(user_id: str, role: str = "guest"):
    db = await get_db()
    await db.execute("INSERT OR REPLACE INTO users (user_id, role) VALUES (?, ?)", (user_id, role))
    await db.commit()
