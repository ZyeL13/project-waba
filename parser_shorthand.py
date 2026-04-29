# parser_shorthand.py
# Deterministic shorthand grammar parser — 0ms, no LLM
import re

# ── Config ──────────────────────────────────────────────────────────────────
TYPE_MAP = {
    "i": "income",
    "e": "expense",
    "t": "transfer",
    "b": "buy",
    "s": "sell",
}

# Category alias → official chart of accounts mapping
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
    # Cash / Bank (for transfers)
    "cash": "cash", "bank": "cash", "bca": "cash", "bri": "cash", "mandiri": "cash",
}

TRANSFER_PATTERN = re.compile(
    r"^t\s+(\w+)\s+(\w+)\s+([\d.]+)$",
    re.IGNORECASE,
)
SHORTHAND_PATTERN = re.compile(
    r"^(\w+)\s+(\w+)\s+([\d.]+)\s*(\w*)$",
    re.IGNORECASE,
)


def parse_shorthand(text: str) -> dict | None:
    """
    Try to parse shorthand notation.
    
    Input: "i sal 300" or "e food 20" or "b btc 0.001 eth"
    Output: standardized internal dict, or None if not shorthand
    """
    t_match = TRANSFER_PATTERN.match(text.strip().lower())
    if t_match:
        src, dst, amount_str = t_match.groups()
        try:
            amount = float(amount_str)
            if amount <= 0:
                return {"error": "Amount must be positive"}
        except ValueError:
            return None
        src_account = CATEGORY_MAP.get(src, src)
        dst_account = CATEGORY_MAP.get(dst, dst)
        entries = [
            {"account": dst_account, "type": "debit", "amount": amount, "currency": "IDR", "description": f"Transfer from {src} to {dst}"},
            {"account": src_account, "type": "credit", "amount": amount, "currency": "IDR", "description": f"Transfer out to {dst}"},
        ]
        return {
            "entries": entries,
            "transaction_type": "transfer",
            "confidence": 1.0,
            "balanced": True,
            "source": "shorthand_transfer",
        }

    match = SHORTHAND_PATTERN.match(text.strip().lower())
    if not match:
        return None

    type_token, cat_token, amount_str, asset_token = match.groups()
    
    # Validate type token
    tx_type = TYPE_MAP.get(type_token)
    if tx_type is None:
        return {"error": f"Unknown type: {type_token}. Use i|e|t|b|s"}

    # Validate numeric amount
    try:
        amount = float(amount_str)
        if amount <= 0:
            return {"error": "Amount must be positive"}
    except ValueError:
        return None  # serahkan ke LLM

    # Resolve category to account
    account = CATEGORY_MAP.get(cat_token, cat_token)  # fallback: raw token as account

    # Build standardized entries
    return _build_entries(tx_type, account, amount, cat_token, asset_token)


def _build_entries(tx_type: str, account: str, amount: float, cat_label: str, asset_token: str | None) -> dict:
    """Convert shorthand into standard GL entries dict."""
    
    if tx_type == "income":
        entries = [
            {"account": "cash", "type": "debit", "amount": amount, "currency": "IDR", "description": f"Income: {cat_label}"},
            {"account": account, "type": "credit", "amount": amount, "currency": "IDR", "description": f"Revenue from {cat_label}"},
        ]
        transaction_type = "revenue"
    
    elif tx_type == "expense":
        entries = [
            {"account": account, "type": "debit", "amount": amount, "currency": "IDR", "description": f"Expense: {cat_label}"},
            {"account": "cash", "type": "credit", "amount": amount, "currency": "IDR", "description": f"Cash out: {cat_label}"},
        ]
        transaction_type = "expense"
    
    elif tx_type == "buy":
        asset_account = CATEGORY_MAP.get(asset_token, "asset") if asset_token else "asset"
        entries = [
            {"account": asset_account, "type": "debit", "amount": amount, "currency": "IDR", "description": f"Buy: {cat_label}"},
            {"account": "cash", "type": "credit", "amount": amount, "currency": "IDR", "description": f"Purchase: {cat_label}"},
        ]
        transaction_type = "asset"
    
    elif tx_type == "sell":
        entries = [
            {"account": "cash", "type": "debit", "amount": amount, "currency": "IDR", "description": f"Sell: {cat_label}"},
            {"account": "revenue", "type": "credit", "amount": amount, "currency": "IDR", "description": f"Sale of {cat_label}"},
        ]
        transaction_type = "revenue"
    
    elif tx_type == "transfer":
        # Transfer between accounts (e.g., "t cash btc 100")
        # Debit destination, credit source
        entries = [
            {"account": "cash", "type": "debit", "amount": amount, "currency": "IDR", "description": f"Transfer in: {cat_label}"},
            {"account": "cash", "type": "credit", "amount": amount, "currency": "IDR", "description": f"Transfer out: {cat_label}"},
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
