async def handle_help(user_id: str, args: list) -> str:
    return """🤖 Bot Asisten

📋 *Commands tersedia:*
  /add <item>      – Tambah item (operator only)
  /search <kata>   – Cari di file terindeks
  /help            – Tampilkan bantuan ini

💬 Kamu juga bisa ngobrol bebas, bot akan merespon otomatis.

📂 File di folder *files/* otomatis terindeks dan bisa dicari.

🔒 Rate limit: 5 request/detik per user."""
