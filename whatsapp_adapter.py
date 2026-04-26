import aiohttp
import logging
import os

logger = logging.getLogger("whatsapp")

# Konfigurasi dari env
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.environ.get("WHATSAPP_PHONE_ID", "")
WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "verify_123")

def normalize(payload: dict) -> list[dict]:
    """
    Ubah payload WhatsApp (single/multi message) -> list format internal.
    Return list of {'from': {'id': ...}, 'text': ...}
    """
    messages = []
    try:
        entries = payload.get("entry", [])
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                msgs = value.get("messages", [])
                for msg in msgs:
                    messages.append({
                        "from": {
                            "id": str(msg.get("from", "")),
                            "name": msg.get("from", "")
                        },
                        "text": msg.get("text", {}).get("body", "")
                    })
    except Exception as e:
        logger.exception(f"Gagal normalisasi WhatsApp: {e}")
    return messages

async def send_reply(phone_number: str, text: str) -> bool:
    """Kirim balasan via WhatsApp Cloud API"""
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        logger.warning("WHATSAPP_TOKEN/PHONE_ID belum diset, balasan tidak terkirim")
        return False

    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    body = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {"body": text}
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body, headers=headers) as resp:
                if resp.status in (200, 201):
                    logger.info(f"Balasan WhatsApp terkirim ke {phone_number}")
                    return True
                else:
                    resp_text = await resp.text()
                    logger.error(f"Gagal kirim WhatsApp: {resp.status} {resp_text}")
                    return False
    except Exception as e:
        logger.exception(f"Error kirim WhatsApp: {e}")
        return False
