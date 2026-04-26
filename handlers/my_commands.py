# handlers/my_commands.py
import time
import auth
import db
import queue_worker

# Jika diperlukan rate limiter instance bisa di‑inject
rate_limiter = None   # akan diisi dari main

async def handle_add(user_id: str, args: list) -> str:
    # 1. Auth
    if not await auth.check_role(user_id, "operator"):
        return "Akses ditolak. Hanya operator."

    # 2. Rate limit (jika tersedia)
    if rate_limiter:
        if not await rate_limiter.allow(user_id, max_requests=5):
            return "Terlalu banyak permintaan, coba lagi nanti."

    # 3. Validasi
    if len(args) != 1:
        return "Format: /add <nama_item>"

    item = args[0].strip()
    if not item:
        return "Nama item tidak boleh kosong."

    timestamp = time.time()

    # 4. Tulis ke DB lokal
    await db.execute_write(
        "INSERT INTO items (user_id, item, ts) VALUES (?, ?, ?)",
        (user_id, item, timestamp)
    )

    # 5. Antri tulis ke Google Sheets
    queue_worker.schedule_write({
        "timestamp": timestamp,
        "user_id": user_id,
        "command": "add",
        "data": item
    })

    return f"Item '{item}' berhasil ditambahkan."
