# llm.py
import aiohttp
import logging
import config

logger = logging.getLogger("llm")

async def fallback_chat(text: str) -> str | None:
    """Panggil LLM hanya jika diaktifkan, kembalikan None jika gagal/timeout."""
    if not config.LLM_ENABLED:
        return None

    url = f"{config.LLM_BASE_URL}/chat/completions"
    headers = {
        "Content-Type": "application/json"
    }
    if config.LLM_API_KEY:
        headers["Authorization"] = f"Bearer {config.LLM_API_KEY}"

    payload = {
        "model": config.LLM_MODEL,
        "messages": [
            {"role": "system", "content": "Kamu asisten yang menjawab singkat, maksimal 2 kalimat."},
            {"role": "user", "content": text}
        ],
        "max_tokens": 200,
        "temperature": 0.45
    }

    try:
        timeout = aiohttp.ClientTimeout(total=config.LLM_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    answer = data["choices"][0]["message"]["content"].strip()
                    logger.info(f"LLM fallback: '{text}' → '{answer}'")
                    return answer
                else:
                    error_text = await resp.text()
                    logger.error(f"LLM error {resp.status}: {error_text}")
                    return None
    except Exception as e:
        logger.exception(f"LLM request failed: {e}")
        return None
