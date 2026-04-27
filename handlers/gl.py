# handlers/gl.py
import logging
from datetime import datetime
import llm
import db

logger = logging.getLogger("gl")

VALID_ACCOUNTS = {"cash", "revenue", "expense", "asset", "liability"}

# Session pending: user_id -> { "original_text", "parsed_result", "question", "valid_options" }
pending = {}

async def handle_catat(user_id: str, args: list) -> str:
    if not args:
        return "Format: /catat <transaksi>\nContoh: /catat client bayar 5 juta via transfer"

    # Cegah tumpukan pending
    if user_id in pending:
        prev = pending[user_id]
        opts = "/".join(prev.get("valid_options", []))
        return f"⚠️ Selesaikan dulu transaksi sebelumnya: {prev['question']} ({opts})"

    text = " ".join(args)
    return await _process_gl(user_id, text)


async def resolve_clarification(user_id: str, answer: str) -> str:
    """Dipanggil ketika user membalas tanpa command, dan ada pending transaksi."""
    if user_id not in pending:
        return None  # tidak ada pending, biarkan flow normal

    session = pending.pop(user_id)
    # Gabungkan teks asli + jawaban user lalu minta LLM ulang
    new_text = f"{session['original_text']} (clarification: {answer})"
    return await _process_gl(user_id, new_text)


async def _process_gl(user_id: str, text: str) -> str:
    """Proses LLM GL, simpan ke DB jika sukses, atau simpan pending jika butuh klarifikasi."""
    result = await llm.fallback_gl(text)
    if result is None:
        return "❌ Gagal memproses transaksi. Coba lagi dengan kata-kata yang lebih jelas."

    # Kalau perlu klarifikasi, simpan pending
    if result.get("needs_clarification"):
        question = result.get("clarification_question", "Mohon jelaskan lebih detail.")
        valid_options = result.get("valid_options", [])
        opt_str = "/".join(valid_options) if valid_options else ""
        hint = f" ({opt_str})" if opt_str else ""
        pending[user_id] = {
            "original_text": text,
            "parsed_result": result,
            "question": question,
            "valid_options": valid_options,
        }
        return f"⚠️ {question}\nBalas singkat: {opt_str}" if opt_str else f"⚠️ {question}"

    # Sukses, simpan ke database
    entries = result.get("entries", [])
    if not entries:
        return "❌ Tidak ada entry yang dihasilkan."

    await _save_journal(user_id, entries, result.get("confidence", 0))
    return _format_response(entries, result)


async def _save_journal(user_id, entries, confidence):
    today = datetime.now().strftime("%Y-%m-%d")
    records = []
    for entry in entries:
        account = entry["account"].lower()
        if account not in VALID_ACCOUNTS:
            account = "expense"  # fallback
        debit_val = entry["amount"] if entry["type"] == "debit" else 0
        credit_val = entry["amount"] if entry["type"] == "credit" else 0
        records.append((
            user_id,
            today,
            entry.get("description", ""),
            account,
            debit_val,
            credit_val,
            confidence
        ))
    await db.execute_write_many(
        "INSERT INTO journal (user_id, date, description, account_id, debit, credit, confidence) VALUES (?, ?, ?, ?, ?, ?, ?)",
        records
    )
    logger.info(f"Journal saved: {len(records)} entries for user {user_id}")


def _format_response(entries, result) -> str:
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
    balance_icon = "✅" if result.get("balanced") else "⚠️"
    lines.append(f"  Balance: {balance_icon}  D={total_debit:,}  K={total_credit:,}")
    lines.append(f"  Confidence: {result.get('confidence', 0):.0%} | Tipe: {result.get('transaction_type', '?')}")
    return "\n".join(lines)
