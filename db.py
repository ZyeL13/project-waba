# db.py
import aiosqlite
import asyncio
from config import DB_PATH

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

    # Tabel user (lama)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            role TEXT NOT NULL DEFAULT 'guest'
        )
    """)

    # Tabel log (lama)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS command_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            command TEXT NOT NULL,
            args TEXT,
            timestamp REAL
        )
    """)

    # Tabel items (lama)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            item TEXT NOT NULL,
            ts REAL
        )
    """)

    # File index FTS5 (lama)
    await db.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS file_index USING fts5(
            filepath,
            content,
            tokenize='unicode61'
        )
    """)

    # ===== GL: Chart of Accounts =====
    await db.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL
        )
    """)

    # Seed akun standar (abaikan jika sudah ada)
    seed_accounts = [
        ("cash",      "Cash",       "asset"),
        ("revenue",   "Revenue",    "revenue"),
        ("expense",   "Expense",    "expense"),
        ("asset",     "Asset",      "asset"),
        ("liability", "Liability",  "liability"),
    ]
    await db.executemany(
        "INSERT OR IGNORE INTO accounts (id, name, type) VALUES (?, ?, ?)",
        seed_accounts
    )

    # ===== GL: Journal Entries =====
    await db.execute("""
        CREATE TABLE IF NOT EXISTS journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            account_id TEXT NOT NULL,
            debit REAL DEFAULT 0,
            credit REAL DEFAULT 0,
            confidence REAL,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        )
    """)

    await db.commit()

async def execute_write(sql: str, params=()):
    db = await get_connection()
    async with _lock:
        await db.execute(sql, params)
        await db.commit()

async def execute_write_many(sql: str, params_list: list):
    """Insert banyak row sekaligus (satu transaksi)"""
    db = await get_connection()
    async with _lock:
        await db.executemany(sql, params_list)
        await db.commit()

async def fetch_all(sql: str, params=()):
    db = await get_connection()
    async with db.execute(sql, params) as cursor:
        return await cursor.fetchall()
