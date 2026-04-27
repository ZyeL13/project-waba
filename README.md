# ⚡ 0xZyel Engine

**Lightweight General Ledger Bot — Double-Entry Accounting in Chat**

A production-ready Telegram/WhatsApp automation system with built-in **General Ledger (GL) double-entry accounting**. Parse natural language transactions, get real-time financial reports, all from your chat app.

---

## 📸 Overview

| Feature | Command |
|---------|---------|
| Record transaction | `/catat client transfer 2 juta` |
| Check balance | `/saldo` |
| Financial statement | `/neraca` |
| Search files | `/search <keyword>` |
| Add item (operator) | `/add <item>` |
| Help | `/help` |

**Smart clarification**: If a transaction is ambiguous (e.g., "client transfer" → revenue or liability?), the bot asks once. Reply with one word and it completes the entry.

**Auto-reply keywords**: No LLM needed for common greetings ("halo", "pagi", "makasih").

---

## 🧠 General Ledger Engine

```

User: /catat client transfer 2 juta
Bot:  ⚠️ Revenue or liability? (revenue/liability)
User: revenue
Bot:  ✅ Transaksi tercatat:
+ Debit  cash       Rp   2,000,000  (Client transfer for revenue)
- Kredit revenue    Rp   2,000,000  (Revenue from client transfer)
────────────────────────────────────────
Balance: ✅  D=2,000,000  K=2,000,000
Confidence: 100% | Tipe: revenue

```

**Double-entry accounting** with strict validation:
- Total Debit = Total Credit (always balanced)
- Chart of accounts: `cash`, `revenue`, `expense`, `asset`, `liability`
- Informal number normalization: `10rb` → `10000`, `5 juta` → `5000000`
- Stateful clarification: pending transactions remembered per user

---

## 📊 Financial Reports

### `/saldo` — Balance per Account
```

📊 Saldo per Akun:
CASH         Rp   2,000,000  (Debit)
REVENUE      Rp   2,000,000  (Kredit)
────────────────────────────────────
Total Debit : Rp   2,000,000
Total Kredit: Rp   2,000,000
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
Total K+E    Rp   2,000,000

Status: ✅ Balance

```

---

## 🏗 Architecture

```

┌─────────────────────────────────┐
│  Telegram / WhatsApp            │
│  (polling or webhook)           │
└────────────┬────────────────────┘
│
┌────────────▼────────────────────┐
│  aiohttp HTTP Server            │
│  ┌──────────────────────────┐  │
│  │ Rate Limiter (sliding)   │  │
│  │ Command Parser           │  │
│  │ GL Engine (LLM + JSON)   │  │
│  │ Auto-reply Keywords      │  │
│  └──────────────────────────┘  │
└────────────┬────────────────────┘
│
┌────────────▼────────────────────┐
│  SQLite (WAL mode)             │
│  ├─ journal (GL entries)       │
│  ├─ accounts (chart)           │
│  ├─ file_index (FTS5 search)   │
│  └─ items, command_log         │
└────────────┬────────────────────┘
│
┌────────────▼────────────────────┐
│  Google Sheets (batch write)   │
│  File Watcher (auto-index)     │
│  LLM Fallback (DeepSeek V3.2)  │
└─────────────────────────────────┘

```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.13+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- [ClawRouter](https://openclaw.ai) or any OpenAI-compatible API (optional, for GL & chat)
- Google Sheets Service Account (optional, for `/add` persistence)

### 1. Clone & Setup
```bash
git clone https://github.com/ZyeL13/project-waba.git
cd project-waba
pip install -r requirements.txt
```

2. Configure .env

```env
# Telegram
TELEGRAM_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# LLM (via ClawRouter or OpenAI-compatible API)
LLM_ENABLED=true
LLM_BASE_URL=http://127.0.0.1:8402/v1
LLM_MODEL=free/deepseek-v3.2
LLM_TIMEOUT=20.0

# Google Sheets (optional)
SPREADSHEET_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUq7oHQt2CvMhD_lZA
```

3. Run

```bash
python main.py
```

The bot will start polling Telegram immediately. Send /help to your bot to verify.

---

📦 Dependencies

Minimal & lightweight — no heavy frameworks.

Package Purpose
aiohttp HTTP server + async API calls
aiosqlite Async SQLite with WAL mode
google-auth Google Sheets API (optional)
requests Auth token refresh

---

🛡 Reliability

· Rate limiting: 5 req/sec per user (sliding window)
· Retry logic: 3x with exponential backoff for LLM & Sheets API
· Graceful shutdown: Ctrl+C once, all background tasks cleaned
· Multi-tenant ready: Per-client .env, isolated DB & files via Docker
· Zero silent failures: Every error logged to stdout + bot.log

---

🐳 Docker (Production)

```bash
docker build -t zyel-engine .
docker run --rm --env-file .env.client-a \
  -v $(pwd)/data/client-a:/app/data \
  -v $(pwd)/files/client-a:/app/files \
  -p 8080:8080 \
  zyel-engine
```

Multi-client with docker-compose:

```bash
docker-compose up -d
```

---

📁 Project Structure

```
project-waba/
├── main.py               # Server entry point
├── config.py             # Environment config
├── db.py                 # SQLite + journal tables
├── llm.py                # GL parser (strict JSON LLM)
├── parser.py             # Deterministic /command parser
├── telegram_adapter.py   # Telegram polling
├── whatsapp_adapter.py   # WhatsApp Cloud API (ready)
├── rate_limiter.py       # Sliding window per-user
├── queue_worker.py       # Batch Google Sheets writes
├── file_watcher.py       # File change → auto-index
├── indexer.py            # FTS5 full-text indexer
├── handlers/
│   ├── gl.py             # /catat (GL double-entry)
│   ├── balance.py        # /saldo + /neraca
│   ├── my_commands.py    # /add
│   ├── search.py         # /search
│   ├── help.py           # /help
│   └── keywords.py       # Auto-reply
└── files/                # Watched directory
```

---

🔮 Roadmap

· /buku — Recent journal entries
· /export — Export to CSV/PDF
· Multi-currency support
· WhatsApp Cloud API live test
· Web dashboard (minimal)

---
```

Built with ☕ in Termux • MIT License

```

---
