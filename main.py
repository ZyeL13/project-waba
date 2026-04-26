import asyncio
import logging
import os
import time

from aiohttp import web

import config
import db
import auth
import rate_limiter
import queue_worker
import parser
import handlers.help as help_handler
import handlers.my_commands as cmd_handler
import handlers.search as search_handler
import handlers.keywords as keywords
import file_watcher
import indexer
import llm
import whatsapp_adapter
from sheets import SheetsClient

# ===== Logging =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("main")

# ===== Inisialisasi Komponen =====
limiter = rate_limiter.SlidingWindowLimiter()
cmd_handler.rate_limiter = limiter
search_handler.rate_limiter = limiter

sheets_client = SheetsClient(config.SHEETS_CREDENTIALS_FILE, config.SPREADSHEET_ID)
queue_worker.call_batch_append = sheets_client.batch_append

COMMAND_MAP = {
    'add': cmd_handler.handle_add,
    'search': search_handler.handle_search,
    'help': help_handler.handle_help,
}

start_time = time.time()

# ===== Lifecycle =====
async def on_startup(app):
    await db.init_db()
    app['worker_task'] = asyncio.create_task(queue_worker.sheets_worker())
    app['cleanup_task'] = asyncio.create_task(periodic_cleanup())

    watcher = file_watcher.FileWatcher(
        directory=config.FILES_DIR,
        on_change=indexer.index_file,
        on_delete=indexer.remove_index,
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

# ===== Webhook Internal Handler =====
async def process_message(user_id: str, text: str) -> str:
    """Return text balasan untuk user"""
    if not await limiter.allow(user_id):
        return "Terlalu banyak permintaan. Coba lagi nanti."

    cmd, args = parser.parse_command(text)
    if cmd is not None:
        handler = COMMAND_MAP.get(cmd)
        if handler is None:
            return f"Command /{cmd} belum tersedia."
        try:
            return await handler(user_id, args)
        except Exception as e:
            logger.exception(f"Error /{cmd}: {e}")
            return "Terjadi kesalahan internal."

    # Bukan command
    kw_reply = await keywords.check_keywords(text)
    if kw_reply:
        return kw_reply

    if config.LLM_ENABLED:
        fb = await llm.fallback_chat(text)
        if fb:
            return fb

    return "Perintah tidak dikenal. Coba /help."

# ===== Route: Generic Webhook =====
async def webhook(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"text": "Invalid JSON"}, status=400)

    uid = str(data.get('from', {}).get('id', ''))
    text = data.get('text', '').strip()
    if not uid or not text:
        return web.json_response({"text": "Bad request"}, status=400)

    reply = await process_message(uid, text)
    return web.json_response({"text": reply})

# ===== Route: WhatsApp Webhook =====
async def whatsapp_webhook(request):
    # Verifikasi webhook (GET)
    if request.method == 'GET':
        mode = request.query.get('hub.mode')
        token = request.query.get('hub.verify_token')
        challenge = request.query.get('hub.challenge')
        if mode == 'subscribe' and token == whatsapp_adapter.WHATSAPP_VERIFY_TOKEN:
            return web.Response(text=challenge, status=200)
        return web.Response(text="Verification failed", status=403)

    # Proses pesan masuk (POST)
    try:
        payload = await request.json()
    except Exception:
        return web.Response(text="Invalid JSON", status=400)

    messages = whatsapp_adapter.normalize(payload)
    for msg in messages:
        uid = msg['from']['id']
        text = msg['text']
        if not uid or not text:
            continue
        reply = await process_message(uid, text)
        # Kirim balasan via WhatsApp API
        await whatsapp_adapter.send_reply(uid, reply)

    return web.Response(text="ok", status=200)

# ===== Route: Stats =====
async def stats(request):
    return web.json_response({
        "status": "ok",
        "uptime_seconds": int(time.time() - start_time),
        "queue_size": queue_worker.queue.qsize(),
        "memory": "ok"
    })

# ===== App Init =====
app = web.Application()
app.router.add_post('/webhook', webhook)
app.router.add_get('/webhook', lambda r: web.json_response({"status": "ok"}))
app.router.add_route('*', '/whatsapp', whatsapp_webhook)
app.router.add_get('/health', lambda r: web.json_response({"status": "ok"}))
app.router.add_get('/stats', stats)

app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Menjalankan di port {port}")
    web.run_app(app, host='0.0.0.0', port=port)
