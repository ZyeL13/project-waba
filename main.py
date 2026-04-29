import asyncio
import logging
import os
import signal
import time

from aiohttp import web
import parser_shorthand
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
import handlers.gl as gl_handler
import handlers.balance as balance_handler
import file_watcher
import indexer
import llm
import whatsapp_adapter
import telegram_adapter
from sheets import SheetsClient
import signal, sys
import handlers.export_handler as export_handler

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
    'catat': gl_handler.handle_catat,
    'saldo': balance_handler.handle_balance,
    'neraca': balance_handler.handle_neraca,
    'export': export_handler.handle_export,
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

    if config.TELEGRAM_TOKEN:
        app['telegram_task'] = asyncio.create_task(
            telegram_adapter.start_polling(
                token=config.TELEGRAM_TOKEN,
                on_message=process_message,
                interval=config.TELEGRAM_POLL_INTERVAL
            )
        )
        logger.info("Telegram polling dimulai")

    logger.info("Bot siap")

async def on_cleanup(app):
    tasks = ['worker_task', 'cleanup_task', 'watcher_task', 'telegram_task']
    for key in tasks:
        t = app.get(key)
        if t:
            t.cancel()
    await asyncio.gather(*[app[k] for k in tasks if app.get(k)], return_exceptions=True)
    logger.info("Bot dimatikan bersih")

async def periodic_cleanup():
    while True:
        await asyncio.sleep(300)
        await limiter.cleanup_stale()

# ===== Process Message =====
async def process_message(user_id: str, text: str) -> str:
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

    # Cek pending GL (user menjawab klarifikasi)
    pending_reply = await gl_handler.resolve_clarification(user_id, text)
    if pending_reply is not None:
        return pending_reply

    # ── NEW: Deteksi shorthand transaction (tanpa /catat) ──────────────────
    shorthand = parser_shorthand.parse_shorthand(text)
    if isinstance(shorthand, dict) and "entries" in shorthand:
        # Arahkan langsung ke GL engine
        return await gl_handler._process_gl(user_id, text)
    elif isinstance(shorthand, dict) and "error" in shorthand:
        return f"❌ {shorthand['error']}"
    # ──────────────────────────────────────────────────────────────────────

    kw_reply = await keywords.check_keywords(text)
    if kw_reply:
        return kw_reply

    if config.LLM_ENABLED:
        fb = await llm.fallback_chat(text)
        if fb:
            return fb

    return "Perintah tidak dikenal. Coba /help."

# ===== Routes =====
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

async def whatsapp_webhook(request):
    if request.method == 'GET':
        mode = request.query.get('hub.mode')
        token = request.query.get('hub.verify_token')
        challenge = request.query.get('hub.challenge')
        if mode == 'subscribe' and token == whatsapp_adapter.WHATSAPP_VERIFY_TOKEN:
            return web.Response(text=challenge, status=200)
        return web.Response(text="Verification failed", status=403)
    try:
        payload = await request.json()
    except Exception:
        return web.Response(text="Invalid JSON", status=400)
    messages = whatsapp_adapter.normalize(payload)
    for msg in messages:
        reply = await process_message(msg['from']['id'], msg['text'])
        await whatsapp_adapter.send_reply(msg['from']['id'], reply)
    return web.Response(text="ok", status=200)

async def stats(request):
    return web.json_response({
        "status": "ok",
        "uptime_seconds": int(time.time() - start_time),
        "queue_size": queue_worker.queue.qsize(),
        "memory": "ok"
    })

# ===== App =====
app = web.Application()
app.router.add_post('/webhook', webhook)
app.router.add_get('/webhook', lambda r: web.json_response({"status": "ok"}))
app.router.add_route('*', '/whatsapp', whatsapp_webhook)
app.router.add_get('/health', lambda r: web.json_response({"status": "ok"}))
app.router.add_get('/stats', stats)
app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)

# ===== Entry Point =====
if __name__ == '__main__':
    import atexit

    port = int(os.environ.get("PORT", 8080))
    PID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".bot.pid")

    # ── Auto-kill proses lama via pidfile ─────────────────────────────────
    try:
        with open(PID_FILE) as f:
            old_pid = int(f.read().strip())
        try:
            os.kill(old_pid, signal.SIGTERM)
            logger.info(f"Menghentikan proses lama (PID {old_pid})...")
            time.sleep(0.5)
            try:
                os.kill(old_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        except ProcessLookupError:
            pass
    except (FileNotFoundError, ValueError):
        pass

    # ── Tulis PID baru ────────────────────────────────────────────────────
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    def _cleanup_pidfile():
        try:
            os.remove(PID_FILE)
        except FileNotFoundError:
            pass

    atexit.register(_cleanup_pidfile)

    # ── Start server ──────────────────────────────────────────────────────
    logger.info(f"Menjalankan di port {port}")
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    web.run_app(app, host='0.0.0.0', port=port, shutdown_timeout=3.0)
