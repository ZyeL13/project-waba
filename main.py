# main.py
import asyncio
import logging
import os

from aiohttp import web

import config
import db
import auth
import rate_limiter
import queue_worker
import parser
import handlers.my_commands as cmd_handler
import handlers.search as search_handler
import file_watcher
import indexer
from sheets import SheetsClient
import llm
# ===== Logging =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("main")

# ===== Inisialisasi Komponen =====
limiter = rate_limiter.SlidingWindowLimiter()

# Inject rate limiter ke handler
cmd_handler.rate_limiter = limiter
search_handler.rate_limiter = limiter

# Inisialisasi Google Sheets client (bukan dummy!)
sheets_client = SheetsClient(config.SHEETS_CREDENTIALS_FILE, config.SPREADSHEET_ID)
queue_worker.call_batch_append = sheets_client.batch_append

# Mapping command
COMMAND_MAP = {
    'add': cmd_handler.handle_add,
    'search': search_handler.handle_search,
    # 'help': ... bisa ditambahkan nanti
}

# ===== Lifecycle =====
async def on_startup(app):
    await db.init_db()
    # Jalankan worker queue untuk Sheets
    app['worker_task'] = asyncio.create_task(queue_worker.sheets_worker())
    # Bersihkan rate limiter secara berkala
    app['cleanup_task'] = asyncio.create_task(periodic_cleanup())

    # File watcher untuk Flow 2
    watcher = file_watcher.FileWatcher(
        directory="./files",
        callback=indexer.index_file,
        interval=10.0
    )
    app['watcher_task'] = asyncio.create_task(watcher.start())

    logger.info("Bot siap")

async def on_cleanup(app):
    tasks = [app['worker_task'], app['cleanup_task'], app['watcher_task']]
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("Bot dimatikan bersih")

async def periodic_cleanup():
    while True:
        await asyncio.sleep(300)
        await limiter.cleanup_stale()

# ===== Webhook Route =====
async def webhook(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"text": "Invalid JSON"}, status=400)

    user_id = str(data.get('from', {}).get('id', ''))
    text = data.get('text', '').strip()

    if not user_id or not text:
        return web.json_response({"text": "Bad request"}, status=400)

    # Rate limit
    if not await limiter.allow(user_id):
        return web.json_response({"text": "Terlalu banyak permintaan. Coba lagi nanti."})

    # Parse command
    cmd, args = parser.parse_command(text)
    if cmd is None:
        # Coba LLM fallback (jika diaktifkan)
        if config.LLM_ENABLED:
            fallback_result = await llm.fallback_chat(text)
            if fallback_result:
                return web.json_response({"text": fallback_result})
        # Jika tidak ada LLM atau LLM gagal
        return web.json_response({"text": "Perintah tidak dikenal. Coba /help."})

    handler = COMMAND_MAP.get(cmd)
    if handler is None:
        return web.json_response({"text": f"Command /{cmd} belum tersedia."})

    try:
        result = await handler(user_id, args)
    except Exception as e:
        logger.exception(f"Error handling /{cmd} for user {user_id}: {e}")
        return web.json_response({"text": "Terjadi kesalahan internal."})

    return web.json_response({"text": result})

# ===== App Init =====
app = web.Application()
app.router.add_post('/webhook', webhook)
app.router.add_get('/health', lambda r: web.json_response({"status": "ok"}))

app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Menjalankan di port {port}")
    web.run_app(app, host='0.0.0.0', port=port)
