class BaseFormatter:
    def format_journal_entries(self, entries: list[dict]) -> dict:
        """Return data structure siap export / render."""
        raise NotImplementedError

    def format_balance_sheet(self, rows: list[dict]) -> dict:
        """Return structured balance sheet."""
        raise NotImplementedError
