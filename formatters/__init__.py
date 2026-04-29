from .simple_text import SimpleTextFormatter
from .ledger_template import LedgerFormatter

_registry = {
    "simple_text": SimpleTextFormatter,
    "ledger_template": LedgerFormatter,
}

def get_formatter(name: str):
    cls = _registry.get(name, SimpleTextFormatter)
    return cls()
