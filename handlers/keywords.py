import re

KEYWORDS = {
    r'\b(halo|hai|hey|hi|assalam)\b': "Halo! Ada yang bisa saya bantu?",
    r'\b(pagi|siang|sore|malam)\b': "Selamat beraktivitas! Ada yang bisa dibantu?",
    r'\b(terima kasih|makasih|thanks)\b': "Sama-sama! Senang bisa membantu.",
    r'\b(bot|kamu siapa)\b': "Saya bot asisten, siap membantu 24/7.",
    r'\b(help|bantuan)\b': "Ketik /help untuk lihat command.",
}

async def check_keywords(text: str) -> str | None:
    text_lower = text.lower()
    for pattern, reply in KEYWORDS.items():
        if re.search(pattern, text_lower):
            return reply
    return None
