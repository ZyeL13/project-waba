# parser_shorthand.py
# Deterministic shorthand grammar parser — 0ms, no LLM
import re

# ── Type mapping ───────────────────────────────────────────────────────────
TYPE_MAP = {
    "i": "income",
    "e": "expense",
    "t": "transfer",
    "b": "buy",
    "s": "sell",
}

# ── Category alias → chart of accounts ─────────────────────────────────────
CATEGORY_MAP = {
    # Income
    "sal": "revenue", "sales": "revenue", "jual": "revenue", "fee": "revenue",
    "komisi": "revenue", "honor": "revenue",
    # Expense
    "food": "expense", "makan": "expense", "listrik": "expense", "air": "expense",
    "internet": "expense", "sewa": "expense", "gaji": "expense", "salary": "expense",
    "bensin": "expense", "transport": "expense", "pajak": "expense",
    "vendor": "expense", "supplier": "expense",
    # Asset
    "btc": "asset", "eth": "asset", "hp": "asset", "laptop": "asset",
    "motor": "asset", "mobil": "asset", "peralatan": "asset", "inventory": "asset",
    # Cash / Bank
    "cash": "cash", "bank": "cash", "bca": "cash", "bri": "cash", "mandiri": "cash",
}

# ── Human-readable labels ──────────────────────────────────────────────────
LABEL_MAP = {
    # Income
    "sal": "Sales Revenue", "sales": "Sales Revenue", "jual": "Sales Revenue",
    "fee": "Service Fee", "komisi": "Commission", "honor": "Honorarium",
    # Expense
    "food": "Food Expense", "makan": "Food Expense",
    "listrik": "Electricity", "air": "Water", "internet": "Internet",
    "sewa": "Rent", "gaji": "Salary", "salary": "Salary",
    "bensin": "Fuel", "transport": "Transportation", "pajak": "Tax",
    "vendor": "Vendor Payment", "supplier": "Supplier Payment",
    # Asset
    "btc": "Bitcoin", "eth": "Ethereum",
    "hp": "Mobile Phone", "laptop": "Laptop",
    "motor": "Motorcycle", "mobil": "Car",
    "peralatan": "Equipment", "inventory": "Inventory",
    # Cash
    "cash": "Cash", "bank": "Bank",
    "bca": "BCA", "bri": "BRI", "mandiri": "Mandiri",
}

# ── Patterns ───────────────────────────────────────────────────────────────
# Transfer: t <source> <dest> <amount>
TRANSFER_PATTERN = re.compile(
    r"^t\s+(\w+)\s+(\w+)\s+([\d.]+)$",
    re.IGNORECASE,
)

# Generic shorthand: <type> <category...> <amount>
SHORTHAND_MULTI_PATTERN = re.compile(
    r"^(\w+)\s+(.+?)\s+([\d.]+)$",
    re.IGNORECASE,
)


# ── Public API ──────────────────────────────────────────────────────────────

def parse_shorthand(text: str) -> dict | None:
    """
    Parse shorthand notation.
    
    Supported formats:
      i sal 300            → Income: Sales Revenue
      i sales hijab 300    → Income: Sales Revenue — hijab
      e food nasi padang 20 → Expense: Food Expense — nasi padang
      b btc 0.001          → Buy: Bitcoin
      t bank cash 500      → Transfer: Bank → Cash
    """
    text = text.strip().lower()
    
    # ── Transfer pattern (exact 4 tokens) ────────────────────────────────
    t_match = TRANSFER_PATTERN.match(text)
    if t_match:
        src, dst, amount_str = t_match.groups()
        try:
            amount = float(amount_str)
            if amount <= 0:
                return {"error": "Amount must be positive"}
        except ValueError:
            return None

        src_label = LABEL_MAP.get(src, src.title())
        dst_label = LABEL_MAP.get(dst, dst.title())
        src_acct = CATEGORY_MAP.get(src, src)
        dst_acct = CATEGORY_MAP.get(dst, dst)

        entries = [
            {"account": dst_acct, "type": "debit",  "amount": amount, "currency": "IDR",
             "description": f"Transfer from {src_label}"},
            {"account": src_acct, "type": "credit", "amount": amount, "currency": "IDR",
             "description": f"Transfer to {dst_label}"},
        ]
        return {
            "entries": entries,
            "transaction_type": "transfer",
            "confidence": 1.0,
            "balanced": True,
            "source": "shorthand_transfer",
        }

    # ── Generic multi-word pattern ──────────────────────────────────────
    match = SHORTHAND_MULTI_PATTERN.match(text)
    if match:
        type_token, cat_raw, amount_str = match.groups()

        if type_token not in TYPE_MAP:
            return {"error": f"Unknown type: {type_token}. Use i|e|t|b|s"}

        try:
            amount = float(amount_str)
            if amount <= 0:
                return {"error": "Amount must be positive"}
        except ValueError:
            return None

        tx_type = TYPE_MAP[type_token]

        # Parse category: "sales hijab premium" → key="sales", extra="hijab premium"
        cat_parts = cat_raw.split()
        cat_key = cat_parts[0]
        extra = " ".join(cat_parts[1:]) if len(cat_parts) > 1 else ""

        # Resolve account
        account = CATEGORY_MAP.get(cat_key, cat_key)

        # Build human-readable description
        base_label = LABEL_MAP.get(cat_key, cat_key.title())
        full_label = f"{base_label} — {extra}" if extra else base_label

        return _build_entries(tx_type, account, amount, full_label, cat_key)

    return None


# ── Entry builders ──────────────────────────────────────────────────────────

def _build_entries(tx_type: str, account: str, amount: float, label: str, cat_key: str) -> dict:
    """Build standardized GL entries from parsed shorthand."""

    if tx_type == "income":
        entries = [
            {"account": "cash",   "type": "debit",  "amount": amount, "currency": "IDR", "description": label},
            {"account": account,  "type": "credit", "amount": amount, "currency": "IDR", "description": label},
        ]
        transaction_type = "revenue"

    elif tx_type == "expense":
        entries = [
            {"account": account, "type": "debit",  "amount": amount, "currency": "IDR", "description": label},
            {"account": "cash",  "type": "credit", "amount": amount, "currency": "IDR", "description": label},
        ]
        transaction_type = "expense"

    elif tx_type == "buy":
        entries = [
            {"account": "asset", "type": "debit",  "amount": amount, "currency": "IDR", "description": f"Buy {label}"},
            {"account": "cash",  "type": "credit", "amount": amount, "currency": "IDR", "description": f"Purchase {label}"},
        ]
        transaction_type = "asset"

    elif tx_type == "sell":
        entries = [
            {"account": "cash",     "type": "debit",  "amount": amount, "currency": "IDR", "description": f"Sell {label}"},
            {"account": "revenue",  "type": "credit", "amount": amount, "currency": "IDR", "description": f"Sale of {label}"},
        ]
        transaction_type = "revenue"

    elif tx_type == "transfer":
        entries = [
            {"account": "cash", "type": "debit",  "amount": amount, "currency": "IDR", "description": f"Transfer in {label}"},
            {"account": "cash", "type": "credit", "amount": amount, "currency": "IDR", "description": f"Transfer out {label}"},
        ]
        transaction_type = "transfer"

    else:
        return None

    return {
        "entries": entries,
        "transaction_type": transaction_type,
        "confidence": 1.0,
        "balanced": True,
        "source": "shorthand",
    }
