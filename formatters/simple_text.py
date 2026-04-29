from .base import BaseFormatter

class SimpleTextFormatter(BaseFormatter):
    def format_journal_entries(self, entries: list[dict]) -> str:
        lines = ["✅ Transaksi tercatat:"]
        total_debit = total_credit = 0
        for e in entries:
            if e.get("type") == "debit":
                lines.append(f"  + Debit  {e['account']:10} Rp{e['amount']:>12,.0f}  ({e.get('description','')})")
                total_debit += e["amount"]
            else:
                lines.append(f"  - Kredit {e['account']:10} Rp{e['amount']:>12,.0f}  ({e.get('description','')})")
                total_credit += e["amount"]
        lines.append(f"  {'─'*40}")
        lines.append(f"  Balance: ✅  D={total_debit:,.0f}  K={total_credit:,.0f}")
        return "\n".join(lines)
