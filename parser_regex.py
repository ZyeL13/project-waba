# parser_regex.py
# Regex-first transaction classifier — LLM hanya fallback
import re

# ── Keyword patterns per transaction type ──────────────────────────────────
_PATTERNS = {
    "expense": re.compile(
        r"\b(bayar|beli|biaya|ongkos|sewa|gaji|listrik|air|internet|makan|bensin|"
        r"transport|ojek|grab|gopay|ovo|cicilan|angsuran|iuran|pajak|service|"
        r"cetak|print|kirim|ongkir|packing|bahan|modal|operasional)\b",
        re.IGNORECASE,
    ),
    "revenue": re.compile(
        r"\b(terima|diterima|masuk|terbayar|lunas|dp\s*masuk|uang\s*masuk|"
        r"pembayaran\s*masuk|client\s*transfer|transfer\s*masuk|bayaran|"
        r"pemasukan|penjualan|jual|laku|order\s*masuk|fee|honor|komisi)\b",
        re.IGNORECASE,
    ),
    "liability": re.compile(
        r"\b(hutang|ngutang|pinjam|pinjaman|dp\s*keluar|advance\s*keluar|"
        r"titipan|deposit\s*keluar)\b",
        re.IGNORECASE,
    ),
    "asset": re.compile(
        r"\b(beli\s*aset|investasi|peralatan|kendaraan|mesin|gedung|"
        r"beli\s*hp|beli\s*laptop|beli\s*motor|beli\s*mobil)\b",
        re.IGNORECASE,
    ),
}

# ── Nominal parser ─────────────────────────────────────────────────────────
_NOMINAL = re.compile(
    r"([\d,.]+)\s*(rb|ribu|k|jt|juta|m|miliar)?",
    re.IGNORECASE,
)

def parse_amount(text: str) -> int | None:
    """Extract nominal dari teks informal. '2 juta' → 2000000, '690rb' → 690000."""
    m = _NOMINAL.search(text)
    if not m:
        return None
    raw = m.group(1).replace(",", "").replace(".", "")
    try:
        value = float(raw)
    except ValueError:
        return None
    suffix = (m.group(2) or "").lower()
    multiplier = {
        "rb": 1_000, "ribu": 1_000, "k": 1_000,
        "jt": 1_000_000, "juta": 1_000_000,
        "m": 1_000_000_000, "miliar": 1_000_000_000,
    }.get(suffix, 1)
    return int(value * multiplier)


# ── Main classifier ────────────────────────────────────────────────────────
NEEDS_LLM = "NEEDS_LLM"          # sentinel: regex tidak cukup

def classify_transaction(text: str) -> dict | str:
    """
    Coba classify transaksi via regex.

    Return dict jika berhasil:
        {
            "type": "expense" | "revenue" | "liability" | "asset",
            "amount": int,
            "description": str,
            "confidence": "high" | "medium",
        }

    Return NEEDS_LLM jika tidak yakin (ambiguous / nominal tidak ditemukan).
    """
    amount = parse_amount(text)
    if amount is None:
        return NEEDS_LLM  # tidak ada nominal → serahkan ke LLM

    matches = {
        t: bool(p.search(text))
        for t, p in _PATTERNS.items()
    }
    matched_types = [t for t, hit in matches.items() if hit]

    if len(matched_types) == 1:
        tx_type = matched_types[0]
        return {
            "type": tx_type,
            "amount": amount,
            "description": text.strip(),
            "confidence": "high",
        }

    if len(matched_types) == 0:
        # Heuristic terakhir: ada kata "transfer" tanpa konteks → minta klarifikasi
        # tapi tetap via bot, bukan LLM
        if re.search(r"\btransfer\b", text, re.IGNORECASE):
            return {
                "type": None,           # perlu klarifikasi
                "amount": amount,
                "description": text.strip(),
                "confidence": "medium",
                "clarify": "revenue_or_liability",  # bot tanya, bukan LLM
            }
        return NEEDS_LLM

    # Lebih dari 1 match → ambiguous
    return NEEDS_LLM


# ── Helper: generate clarification message (tanpa LLM) ────────────────────
CLARIFY_MESSAGES = {
    "revenue_or_liability": (
        "⚠️ Transfer ini *masuk* (pendapatan) atau *titipan/dp* (kewajiban)?\n"
        "Balas: `masuk` atau `titipan`"
    ),
    "expense_or_asset": (
        "⚠️ Pembelian ini untuk *operasional* (biaya) atau *aset tetap*?\n"
        "Balas: `biaya` atau `aset`"
    ),
}

def get_clarify_message(key: str) -> str:
    return CLARIFY_MESSAGES.get(key, "⚠️ Tolong perjelas jenis transaksinya.")

