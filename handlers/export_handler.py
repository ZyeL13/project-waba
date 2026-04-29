import os
import tempfile
import asyncio
import logging
from datetime import datetime
import db
import telegram_adapter
import config
from formatters import get_formatter
from exporters import export_ledger_xlsx

logger = logging.getLogger("export")

async def handle_export(user_id: str, args: list) -> str:
    # Ambil data jurnal user
    rows = await db.fetch_all(
        """SELECT date, description, account_id, debit, credit
           FROM journal
           WHERE user_id = ?
           ORDER BY date, id""",
        (user_id,)
    )
    if not rows:
        return "📊 Belum ada transaksi untuk diexport."

    # Format ke structured data
    formatted_rows = [dict(r) for r in rows]
    formatter = get_formatter("ledger_template")
    data = formatter.format_journal_entries(formatted_rows)

    # Export ke file temp
    filename = f"ledger_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = os.path.join(tempfile.gettempdir(), filename)
    export_ledger_xlsx(data, filepath)

    # Kirim via Telegram
    if config.TELEGRAM_TOKEN:
        try:
            await telegram_adapter.send_document(config.TELEGRAM_TOKEN, user_id, filepath, filename)
            os.remove(filepath)
            return "📎 File ledger telah dikirim."
        except Exception as e:
            logger.exception("Gagal kirim file")
            return f"❌ Gagal mengirim file: {e}"
    else:
        return f"📁 File tersimpan di: {filepath}"
