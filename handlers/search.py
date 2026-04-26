# handlers/search.py
import db
import auth
import logging

logger = logging.getLogger("search")

rate_limiter = None  # diisi dari main

async def handle_search(user_id: str, args: list) -> str:
    # Auth opsional: semua user bisa search, tapi rate limit tetap
    if rate_limiter:
        if not await rate_limiter.allow(user_id, max_requests=5):
            return "Terlalu banyak permintaan. Coba lagi nanti."

    if not args:
        return "Format: /search <kata kunci>"

    query = " ".join(args).strip()
    if not query:
        return "Kata kunci tidak boleh kosong."

    # Cari di FTS5
    db_conn = await db.get_connection()
    try:
        async with db_conn.execute(
            "SELECT filepath, snippet(file_index, 1, '*', '*', '.....', 40) as snippet "
            "FROM file_index WHERE content MATCH ?",
            (query,)
        ) as cursor:
            rows = await cursor.fetchall()
    except Exception as e:
        logger.exception("Error saat pencarian")
        return "Terjadi kesalahan saat mencari."

    if not rows:
        return f"Tidak ditemukan hasil untuk '{query}'."

    lines = []
    for row in rows:
        lines.append(f"📄 {row['filepath']}\n   {row['snippet']}")
    return "\n\n".join(lines[:5])  # batasi 5 hasil
