# handlers/gl.py (update fungsi)
import logging
from datetime import datetime
import llm
import db
from parser_regex import classify_transaction, get_clarify_message, NEEDS_LLM
import parser_shorthand

logger = logging.getLogger("gl")

VALID_ACCOUNTS = {"cash", "revenue", "expense", "asset", "liability"}
pending = {}

# Mapping clarify key → (question_text, valid_options)
CLARIFY_OPTIONS = {
    "revenue_or_liability": ("Transfer ini masuk (pendapatan) atau titipan/dp (kewajiban)?", ["masuk", "titipan"]),
}

async def handle_catat(user_id: str, args: list) -> str:
    if not args:
        return "Format: /catat <transaksi>\nContoh: /catat client transfer 2 juta"

    if user_id in pending:
        prev = pending[user_id]
        return f"⚠️ Selesaikan dulu transaksi sebelumnya: {prev['question']}"

    text = " ".join(args)
    return await _process_gl(user_id, text)


async def resolve_clarification(user_id: str, answer: str) -> str | None:
    """Dipanggil saat user membalas tanpa command, dan ada pending transaksi."""
    if user_id not in pending:
        return None

    session = pending.pop(user_id)
    # Combine original text + user clarification
    new_text = f"{session['original_text']} (clarification: {answer})"
    return await _process_gl(user_id, new_text)

async def _process_gl(user_id: str, text: str) -> str:
    """Proses transaksi: shorthand → regex natural → clarify → LLM."""

    # ── Step 1: shorthand grammar (strict, 0ms) ────────────────────────────
    shorthand = parser_shorthand.parse_shorthand(text)
    if isinstance(shorthand, dict):
        if "entries" in shorthand:
            entries = shorthand["entries"]
            await _save_journal_llm(user_id, entries, 1.0)
            return _format_response(entries, shorthand)
        elif "error" in shorthand:
            return f"❌ {shorthand['error']}"

    # ── Step 2: regex natural (classify_transaction) ──────────────────────
    regex_result = classify_transaction(text)

    if isinstance(regex_result, dict):
        if regex_result.get("type") is not None:
            return await _save_and_format(user_id, regex_result)

        if regex_result.get("type") is None:
            clarify_key = regex_result.get("clarify", "")
            question, options = CLARIFY_OPTIONS.get(
                clarify_key,
                ("⚠️ Tolong perjelas jenis transaksinya.", [])
            )
            pending[user_id] = {
                "original_text": text,
                "parsed_result": regex_result,
                "question": question,
                "valid_options": options,
            }
            opt_str = "/".join(options)
            return f"⚠️ {question}\nBalas singkat: {opt_str}" if opt_str else f"⚠️ {question}"

    # ── Step 3: NEEDS_LLM → LLM fallback ──────────────────────────────────
    return await _process_llm(user_id, text)

async def _process_llm(user_id: str, text: str) -> str:
    """LLM fallback (asli, tidak diubah)."""
    result = await llm.fallback_gl(text)
    if result is None:
        return "❌ Gagal memproses transaksi. Coba lagi dengan kata-kata yang lebih jelas."

    if result.get("needs_clarification"):
        question = result.get("clarification_question", "Mohon jelaskan lebih detail.")
        valid_options = result.get("valid_options", [])
        opt_str = "/".join(valid_options)
        pending[user_id] = {
            "original_text": text,
            "parsed_result": result,
            "question": question,
            "valid_options": valid_options,
        }
        return f"⚠️ {question}\nBalas singkat: {opt_str}" if opt_str else f"⚠️ {question}"

    entries = result.get("entries", [])
    if not entries:
        return "❌ Tidak ada entry yang dihasilkan."

    await _save_journal_llm(user_id, entries, result.get("confidence", 0))
    return _format_response(entries, result)


async def _save_and_format(user_id: str, regex_result: dict) -> str:
    """Simpan hasil regex ke journal dan format respons."""
    tx_type = regex_result["type"]
    amount = regex_result["amount"]
    desc = regex_result.get("description", "")

    # Tentukan akun yang terlibat (debit/credit sesuai aturan akuntansi)
    if tx_type == "expense":
        entries = [
            {"account": "expense", "type": "debit", "amount": amount, "currency": "IDR", "description": desc},
            {"account": "cash", "type": "credit", "amount": amount, "currency": "IDR", "description": f"Cash out: {desc}"},
        ]
    elif tx_type == "revenue":
        entries = [
            {"account": "cash", "type": "debit", "amount": amount, "currency": "IDR", "description": desc},
            {"account": "revenue", "type": "credit", "amount": amount, "currency": "IDR", "description": f"Revenue: {desc}"},
        ]
    elif tx_type == "liability":
        entries = [
            {"account": "cash", "type": "debit", "amount": amount, "currency": "IDR", "description": desc},
            {"account": "liability", "type": "credit", "amount": amount, "currency": "IDR", "description": desc},
        ]
    elif tx_type == "asset":
        entries = [
            {"account": "asset", "type": "debit", "amount": amount, "currency": "IDR", "description": desc},
            {"account": "cash", "type": "credit", "amount": amount, "currency": "IDR", "description": f"Purchase: {desc}"},
        ]
    else:
        return "❌ Tipe transaksi tidak dikenali."

    result = {
        "entries": entries,
        "transaction_type": tx_type,
        "confidence": 1.0,
        "balanced": True,
    }
    await _save_journal_llm(user_id, entries, 1.0)
    return _format_response(entries, result)


async def _save_journal_llm(user_id, entries, confidence):
    """Simpan journal entries (sama seperti sebelumnya)."""
    today = datetime.now().strftime("%Y-%m-%d")
    records = []
    for entry in entries:
        account = entry["account"].lower()
        if account not in VALID_ACCOUNTS:
            account = "expense"
        debit_val = entry["amount"] if entry["type"] == "debit" else 0
        credit_val = entry["amount"] if entry["type"] == "credit" else 0
        records.append((user_id, today, entry.get("description", ""), account, debit_val, credit_val, confidence))
    await db.execute_write_many(
        "INSERT INTO journal (user_id, date, description, account_id, debit, credit, confidence) VALUES (?, ?, ?, ?, ?, ?, ?)",
        records
    )
    logger.info(f"Journal saved: {len(records)} entries for user {user_id}")


def _format_response(entries, result) -> str:
    """Format respons (sama seperti sebelumnya)."""
    lines = ["✅ Transaksi tercatat:"]
    total_debit = total_credit = 0
    for entry in entries:
        acc = entry["account"]
        amt = entry["amount"]
        desc = entry.get("description", "")
        if entry["type"] == "debit":
            lines.append(f"  + Debit  {acc:10} Rp{amt:>12,}  ({desc})")
            total_debit += amt
        else:
            lines.append(f"  - Kredit {acc:10} Rp{amt:>12,}  ({desc})")
            total_credit += amt
    lines.append(f"  {'─' * 40}")
    bal = "✅" if result.get("balanced") else "⚠️"
    lines.append(f"  Balance: {bal}  D={total_debit:,}  K={total_credit:,}")
    lines.append(f"  Confidence: {result.get('confidence', 0):.0%} | Tipe: {result.get('transaction_type', '?')}")
    return "\n".join(lines)
