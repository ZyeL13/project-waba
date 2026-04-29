# telegram_adapter.py
import aiohttp
import asyncio
import logging
from typing import Callable

logger = logging.getLogger("telegram")

TELEGRAM_API = "https://api.telegram.org"

async def start_polling(token: str, on_message: Callable, interval: float = 2.0):
    if not token:
        logger.warning("TELEGRAM_TOKEN kosong, polling tidak dimulai")
        return

    url = f"{TELEGRAM_API}/bot{token}/getUpdates"
    offset = 0
    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        while True:
            try:
                params = {"offset": offset, "timeout": 10}
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for update in data.get("result", []):
                            offset = update["update_id"] + 1
                            msg = update.get("message", {})
                            text = msg.get("text", "")
                            chat_id = str(msg.get("chat", {}).get("id", ""))
                            if chat_id and text:
                                logger.info(f"Telegram message from {chat_id}: {text}")
                                reply = await on_message(chat_id, text)
                                if reply:
                                    await send_message(token, chat_id, reply)
                    else:
                        logger.error(f"Telegram polling error {resp.status}")
            except Exception as e:
                logger.exception(f"Telegram polling error: {e}")

            await asyncio.sleep(interval)

async def send_message(token: str, chat_id: str, text: str) -> bool:
    """Kirim pesan balasan via Telegram."""
    if not token:
        return False
    url = f"{TELEGRAM_API}/bot{token}/sendMessage"
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json={
                "chat_id": chat_id,
                "text": text[:4000]
            }) as resp:
                if resp.status == 200:
                    return True
                logger.error(f"Telegram send error {resp.status}: {await resp.text()}")
                return False
    except Exception as e:
        logger.exception(f"Telegram send failed: {e}")
        return False

async def send_document(token: str, chat_id: str, filepath: str, filename: str) -> bool:
    """Kirim file dokumen via Telegram."""
    if not token:
        return False
    url = f"{TELEGRAM_API}/bot{token}/sendDocument"
    data = {"chat_id": chat_id}
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            with open(filepath, "rb") as f:
                form = aiohttp.FormData()
                form.add_field("chat_id", chat_id)
                form.add_field("document", f, filename=filename, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                async with session.post(url, data=form) as resp:
                    if resp.status == 200:
                        logger.info(f"Document sent to {chat_id}: {filename}")
                        return True
                    logger.error(f"Send document error {resp.status}: {await resp.text()}")
                    return False
    except Exception as e:
        logger.exception(f"Send document failed: {e}")
        return False
