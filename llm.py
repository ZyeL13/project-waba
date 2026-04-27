import aiohttp
import json
import re
import logging
import asyncio
import config

logger = logging.getLogger("llm")

GL_SYSTEM_PROMPT = """You are a corporate finance transaction parser.

Your task is to convert user input into structured accounting entries based on General Ledger (GL) principles.
You must interpret natural language, normalize financial intent, and produce consistent accounting records.

CRITICAL RULES:
- OUTPUT MUST BE VALID JSON ONLY. No markdown, no explanation, no thinking aloud.
- Do NOT write any text before or after the JSON.
- Start your response with { and end with }.
- Never include conversational phrases.

OUTPUT FORMAT (STRICT JSON ONLY):
{
  "entries": [
    {
      "account": "string",
      "type": "debit | credit",
      "amount": number,
      "currency": "IDR",
      "description": "string"
    }
  ],
  "transaction_type": "revenue | expense | asset | liability | equity",
  "confidence": 0-1,
  "needs_clarification": true/false,
  "clarification_question": "string",
  "valid_options": ["option1", "option2"]
}

ACCOUNTING RULES:
- Always produce balanced entries (total debit = total credit)
- Every transaction MUST affect at least two accounts
- Use double-entry accounting logic consistently

CHART OF ACCOUNTS (STRICT):
- cash → all incoming/outgoing money (bank, e-wallet, cash)
- revenue → income from business operations
- expense → operational spending (vendor, salary, utilities)
- asset → owned resources (inventory, equipment, receivables)
- liability → obligations (debt, payables, advances)

INTERPRETATION RULES:
- Identify intent: payment, purchase, transfer, advance, settlement
- Infer transaction type:
  - client pays → revenue OR liability (if unclear)
  - pay vendor → expense
  - buy asset → asset
- Normalize informal language:
  - "10rb" → 10000
  - "5 juta" → 5000000
- Normalize entities:
  - "client", "customer" → revenue-related
  - "vendor", "supplier" → expense-related

CLARIFICATION LOGIC:
- If multiple valid interpretations exist:
  - Set needs_clarification = true
  - Provide a short, precise clarification_question
  - Include 2–3 valid_options (short labels only)
- DO NOT guess when ambiguity affects accounting classification

CONFIDENCE SCORING:
- 0.9–1.0 → clear intent, no ambiguity
- 0.7–0.89 → minor ambiguity, still acceptable
- <0.7 → must ask clarification

FAIL-SAFE:
- NEVER hallucinate missing accounts or values
- NEVER produce unbalanced entries
- NEVER invent context not present in input
- If critical data missing → trigger clarification

OUTPUT DISCIPLINE:
- Keep descriptions short and factual
- Do not repeat user sentence verbatim
- Do not include unnecessary fields"""


async def _call_llm(system_prompt: str, user_text: str, max_tokens: int, temperature: float) -> str | None:
    if not config.LLM_ENABLED:
        return None

    url = f"{config.LLM_BASE_URL}/chat/completions"
    headers = {"Content-Type": "application/json"}
    if config.LLM_API_KEY:
        headers["Authorization"] = f"Bearer {config.LLM_API_KEY}"

    payload = {
        "model": config.LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature
    }

    for attempt in range(3):
        try:
            timeout = aiohttp.ClientTimeout(total=config.LLM_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, headers=headers, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["choices"][0]["message"]["content"].strip()
                    else:
                        error_text = await resp.text()
                        logger.error(f"LLM error {resp.status} (attempt {attempt+1}): {error_text}")
                        if 400 <= resp.status < 500:
                            return None
        except Exception as e:
            logger.warning(f"LLM attempt {attempt+1} failed: {e}")
            if attempt < 2:
                await asyncio.sleep(1 * (attempt + 1))
    return None


async def fallback_chat(text: str) -> str | None:
    return await _call_llm(
        system_prompt="Kamu asisten yang menjawab singkat, maksimal 2 kalimat.",
        user_text=text,
        max_tokens=200,
        temperature=0.45
    )


async def fallback_gl(text: str) -> dict | None:
    raw = await _call_llm(
        system_prompt=GL_SYSTEM_PROMPT,
        user_text=text,
        max_tokens=400,
        temperature=0.0    # paling deterministik
    )
    if raw is None:
        return None
    logger.info(f"LLM GL raw: '{text}' → '{raw}'")
    return parse_gl_response(raw)


def parse_gl_response(raw: str) -> dict | None:
    try:
        # Coba parse langsung
        result = _parse_gl_json(raw)
        if result:
            return result

        # Cari { pertama dan } terakhir
        start = raw.find('{')
        end = raw.rfind('}')
        if start != -1 and end != -1 and end > start:
            result = _parse_gl_json(raw[start:end+1])
            if result:
                return result

        # Coba bersihkan markdown code block
        if "```" in raw:
            parts = raw.split("```")
            for part in parts:
                if '{' in part:
                    result = _parse_gl_json(part.strip())
                    if result:
                        return result

        logger.warning(f"Gagal parse GL JSON dari: {raw[:200]}...")
        return None

    except Exception as e:
        logger.exception(f"Gagal parse GL JSON: {e}")
        return None


def _parse_gl_json(text: str) -> dict | None:
    """Parse JSON dari string, validasi struktur GL."""
    text = text.strip()
    if not text.startswith('{'):
        return None
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        return None

    if "entries" not in result:
        return None

    total_debit = sum(e["amount"] for e in result["entries"] if e["type"] == "debit")
    total_credit = sum(e["amount"] for e in result["entries"] if e["type"] == "credit")
    result["balanced"] = (total_debit == total_credit)

    if not result["balanced"]:
        logger.warning(f"GL tidak balance: debit={total_debit} credit={total_credit}")

    if result.get("needs_clarification") and "valid_options" not in result:
        result["valid_options"] = ["revenue", "expense", "asset", "liability"]

    return result
