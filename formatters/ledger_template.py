from .base import BaseFormatter

class LedgerFormatter(BaseFormatter):
    def format_journal_entries(self, entries: list[dict]) -> dict:
        """
        Return struktur data template General Ledger:
        - ACCOUNT NAME
        - ACCT NO.
        - MONTH ENDING
        - DATE | DESCRIPTION | POST REF | TRANSACTIONS (DEBIT/CREDIT) | BALANCES (TOTAL)
        """
        rows = []
        running_debit = 0
        running_credit = 0

        for e in entries:
            debit = e.get("debit", 0)
            credit = e.get("credit", 0)
            running_debit += debit
            running_credit += credit

            rows.append({
                "date":         e.get("date", ""),
                "description":  e.get("description", ""),
                "post_ref":     e.get("account_id", ""),
                "debit":        debit,
                "credit":       credit,
                "running_debit":  running_debit,
                "running_credit": running_credit,
            })

        return {
            "account_name":   "General Ledger",
            "acct_no":        "GL-001",
            "month_ending":   rows[-1]["date"] if rows else "",
            "starting_balance": 0,
            "total_adjusted":   running_debit - running_credit,
            "rows": rows,
        }
