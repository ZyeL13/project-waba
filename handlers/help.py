# handlers/help.py
async def handle_help(user_id: str, args: list) -> str:
    return """🤖 Bot Asisten

📋 *Commands:*
  /catat [teks]    – Catat transaksi double-entry (General Ledger)
  /saldo           - Lihat saldo per akun
  /neraca          - Laporan posisi keuangan
  /add [item]      – Tambah item (operator only)
  /search [kata]   – Cari di file terindeks
  /help            – Tampilkan bantuan ini

💬 Chat bebas akan dijawab otomatis.
📂 File di *files/* otomatis terindeks.
🔒 Rate limit: 5 request/detik."""
