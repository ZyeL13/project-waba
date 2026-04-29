# ⚡ 0xZyel Engine

**Lightweight General Ledger Bot — Double-Entry Accounting in Chat**

A production-ready Telegram/WhatsApp automation system with built-in **General Ledger (GL) double-entry accounting**. Parse transactions via shorthand, natural language, or full double-entry — export to Excel instantly.

---

## 📸 Overview

| Mode | Input | Latency |
|------|-------|---------|
| **Shorthand** | `i sal 300` | 0ms (regex) |
| **Natural** | `/catat client transfer 2 juta` | regex → clarify → LLM |
| **Full GL** | `/catat bayar listrik 500rb` | regex 0ms |
| **Reports** | `/saldo`, `/neraca` | instant |
| **Export** | `/export` | Excel file |

**Smart clarification**: If ambiguous, bot asks once. Reply with one word.

---

## 🧠 General Ledger Engine

```

User: i sal 300
Bot:  ✅ Transaksi tercatat:
+ Debit  cash       Rp         300  (Income: sal)
- Kredit revenue    Rp         300  (Revenue from sal)
────────────────────────────────────────
Balance: ✅  D=300  K=300
Confidence: 100% | Tipe: revenue

```

**Double-entry accounting** with strict validation:
- Total Debit = Total Credit (always balanced)
- Chart of accounts: `cash`, `revenue`, `expense`, `asset`, `liability`
- Shorthand grammar parser (0ms, no LLM)
- Natural language classifier (regex-first, LLM fallback)
- Stateful clarification: pending transactions remembered per user

---

## ⌨️ Shorthand Grammar

| Shorthand | Meaning |
|-----------|---------|
| `i sal 300` | Income: sales Rp300 |
| `e food 20` | Expense: food Rp20 |
| `b btc 0.001` | Buy: bitcoin 0.001 |
| `t bank cash 500` | Transfer bank → cash Rp500 |

No `/catat` needed — just type it directly.

---

## 📊 Financial Reports

### `/saldo` — Balance per Account
```

📊 Saldo per Akun:
CASH         Rp   2,000,000  (Debit)
REVENUE      Rp   2,000,000  (Kredit)
────────────────────────────────────
Status: ✅ Balance

```

### `/neraca` — Statement of Financial Position
```

📈 Laporan Posisi Keuangan

ASET
Rp   2,000,000

KEWAJIBAN & EKUITAS
Liabilitas   Rp           0
Ekuitas      Rp   2,000,000
──────────────────────────────
Status: ✅ Balance

```

### `/export` — Download Excel Template
```

/export
Bot: 📎 File ledger_1089039279_20260429.xlsx telah dikirim.

```

You get a properly formatted **General Ledger Template** (`.xlsx`) directly in Telegram.

---

## 🏗 Architecture

```

User Input
│
├─ Shorthand (regex, 0ms)
├─ Natural lang (regex classifier → LLM fallback)
│
├─ GL Engine (double-entry validation)
│
├─ SQLite (journal, accounts, FTS5)
│
├─ Formatters (text, ledger_template, ...)
├─ Exporters (XLSX, ...)
│
└─ Telegram / WhatsApp Output

```

**Template system**: add new client → branch repo → change `OUTPUT_FORMAT` → done.

---

## 🚀 Quick Start

```bash
git clone https://github.com/ZyeL13/project-waba.git
cd project-waba
pip install -r requirements.txt
cp .env.example .env   # edit TELEGRAM_TOKEN, LLM, etc.
python main.py
```

---

📦 Project Structure

```
project-waba/
├── main.py               # Server entry point
├── config.py             # Environment config + OUTPUT_FORMAT
├── parser_shorthand.py   # Shorthand grammar (i sal 300)
├── parser_regex.py       # Natural language regex classifier
├── llm.py                # GL parser (LLM fallback)
├── telegram_adapter.py   # Telegram polling + file upload
├── whatsapp_adapter.py   # WhatsApp Cloud API (ready)
├── formatters/           # Output formatters (text, ledger)
├── exporters/            # File exporters (XLSX)
├── handlers/             # Commands (/catat, /saldo, /neraca, /export)
└── files/                # Watched directory for /search
```

---

🛡 Reliability

· Rate limiting: 5 req/sec per user
· Retry logic: 3x with backoff
· Graceful shutdown: Ctrl+C once, port freed
· Multi-tenant ready: per-client .env, isolated DB via Docker
· Zero silent failures: all errors logged

---

```
Built with ☕ in Termux • MIT License
```
